# user/views.py
from django.contrib.auth.hashers import check_password
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import generics, permissions, status, parsers
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from .serializers import SignUpSerializer, LoginSerializer, LogoutSerializer, CartItemCreateSerializer, CartItemSerializer, CartItemUpdateSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from django.conf import settings
from .utils import upload_profile_image_to_s3
from .models import CartItem
from product.models import Product

class SignUpAPI(generics.CreateAPIView):
    serializer_class = SignUpSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    @swagger_auto_schema(
        operation_summary="회원가입",
        consumes=["multipart/form-data"],
    )
    def post(self, request, *args, **kwargs):
        image_file = request.FILES.get("profile_image")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save() 

        if image_file:
            image_bytes = image_file.read()
            profile_image_url = upload_profile_image_to_s3(str(user.id), image_bytes)

            user.profile_image = profile_image_url
            user.save() 

        return Response({
            "message": "회원가입이 완료되었습니다.",
            "user_id": user.id,
            "profile_image_url": user.profile_image
        }, status=201)

class LoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
    operation_summary="로그인",
    request_body=LoginSerializer,      
    responses={200: "로그인 성공", 401: "비밀번호 오류", 404: "ID 없음"},
)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=username, password=password)
        
        if user is None:
            return Response({"error": "아이디 또는 비밀번호가 올바르지 않습니다."}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        data = {
            "status": 200,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "message": "로그인 성공",
        }

        resp = Response(data, status=status.HTTP_200_OK)
        resp.set_cookie("access",  data["access_token"],
                        httponly=True, samesite="Lax",
                        secure=not settings.DEBUG, path="/", max_age=60*60)
        resp.set_cookie("refresh", data["refresh_token"],
                        httponly=True, samesite="Lax",
                        secure=not settings.DEBUG, path="/", max_age=60*60*24*7)
        return resp
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]  # access 쿠키 필수

    @swagger_auto_schema(
        operation_summary="로그아웃",
        request_body=LogoutSerializer,
        responses={204: "로그아웃 완료", 400: "잘못된 토큰"},
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        resp = Response(status=status.HTTP_204_NO_CONTENT)
        # 쿠키 삭제(클라이언트에서 지우도록 max_age=0)
        resp.delete_cookie("access",  path="/", domain="127.0.0.1")  # domain 값은 로그인과 동일
        resp.delete_cookie("refresh", path="/", domain="127.0.0.1")
        return resp
    
class CookieTokenRefreshView(TokenRefreshView):
    """
    쿠키에서 refresh 토큰을 읽어 access 토큰 재발급
    (요청 body에 refresh 필드를 줘도 동작)
    """
    serializer_class = TokenRefreshSerializer        # 그대로 사용

    @swagger_auto_schema(
        operation_summary="Access 토큰 재발급",
        operation_description="만료된 access 대신 refresh 토큰으로 새 access 토큰을 발급합니다.",
        # body 없이도 호출할 수 있으므로 request_body=None
        responses={200: "재발급 성공", 401: "refresh 토큰 오류"}
    )
    def post(self, request, *args, **kwargs):
        # ① refresh 토큰 추출: 쿠키 > body 순
        refresh_token = (
            request.COOKIES.get("refresh") or
            request.data.get("refresh")
        )
        if not refresh_token:
            return Response({"error": "refresh 토큰이 없습니다."},
                            status=status.HTTP_401_UNAUTHORIZED)

        # ② Simple JWT 기본 serializer 재사용
        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({"error": "유효하지 않은 refresh 토큰"},
                            status=status.HTTP_401_UNAUTHORIZED)

        access_token = serializer.validated_data["access"]

        # ③ 새 access 토큰을 쿠키+본문에 포함
        resp = Response(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,  
            },
            status=status.HTTP_200_OK
        )
        resp.set_cookie(
            key="access",
            value=access_token,
            httponly=True,
            samesite="Lax",
            secure=not settings.DEBUG,
            path="/",
            max_age=60 * 15,    
        )
        return resp
    
class CartItemCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="장바구니에 상품 추가",
        request_body=CartItemCreateSerializer,
        responses={201: CartItemSerializer, 400: "잘못된 요청"}
    )
    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({"error": "존재하지 않는 상품입니다."}, status=404)

        cart_item, created = CartItem.objects.get_or_create(user=user, product=product)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()

        response_serializer = CartItemSerializer(cart_item)
        return Response(response_serializer.data, status=201)
    
class CartItemListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(operation_summary="장바구니 리스트") 
    def get(self, request):
        cart_items = CartItem.objects.filter(user=request.user)
        serializer = CartItemSerializer(cart_items, many=True)

        total_price = sum(item.product.price * item.quantity for item in cart_items)

        return Response({
            "cart_product": serializer.data,
            "total_price": total_price
        })
        
class CartItemUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="장바구니 상품 수량 수정",
        request_body=CartItemUpdateSerializer,
        responses={200: CartItemSerializer, 404: "상품을 찾을 수 없음"}
    )
    def put(self, request, cart_product_id):
        try:
            cart_item = CartItem.objects.get(id=cart_product_id, user=request.user)
        except CartItem.DoesNotExist:
            return Response({"error": "장바구니에서 해당 상품을 찾을 수 없습니다."}, status=404)

        serializer = CartItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        quantity = serializer.validated_data['quantity']
        
        if quantity <= 0:
            cart_item.delete()
            return Response({"message": "상품이 장바구니에서 삭제되었습니다."}, status=200)
        else:
            cart_item.quantity = quantity
            cart_item.save()
            response_serializer = CartItemSerializer(cart_item)
            return Response(response_serializer.data, status=200)
        
    @swagger_auto_schema(
        operation_summary="장바구니 상품 삭제",
        responses={200: "삭제 완료", 404: "상품을 찾을 수 없음"}
    )
    def delete(self, request, cart_product_id):
        try:
            cart_item = CartItem.objects.get(id=cart_product_id, user=request.user)
            cart_item.delete()
            return Response({"message": "상품이 장바구니에서 삭제되었습니다."}, status=200)
        except CartItem.DoesNotExist:
            return Response({"error": "장바구니에서 해당 상품을 찾을 수 없습니다."}, status=404)
        
        
class UpdateProfileImageAPI(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="프로필 이미지 변경",
        operation_description="새로운 프로필 이미지를 업로드하여 변경합니다.",
        consumes=["multipart/form-data"],
        manual_parameters=[
            openapi.Parameter(
                name="profile_image",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="새 프로필 이미지 파일",
            )
        ],
        responses={
            200: openapi.Response(
                description="성공적으로 변경됨",
                examples={
                    "application/json": {
                        "message": "프로필 이미지가 성공적으로 변경되었습니다.",
                        "profile_image_url": "https://cdn.example.com/profiles/1/abcd.jpg"
                    }
                }
            ),
            400: "이미지가 포함되지 않았을 때",
        }
    )
    def patch(self, request):
        image_file = request.FILES.get("profile_image")
        if not image_file:
            return Response({"error": "이미지 파일을 제공해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        image_bytes = image_file.read()
        ext = image_file.name.split('.')[-1].lower()

        user = request.user
        profile_image_url = upload_profile_image_to_s3(str(user.id), image_bytes, ext)

        user.profile_image = profile_image_url
        user.is_fitting = False
        user.save()

        return Response({
            "message": "프로필 이미지가 성공적으로 변경되었습니다.",
            "profile_image_url": user.profile_image
        }, status=status.HTTP_200_OK)