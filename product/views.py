from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from user.models import UserImage
from fitting.models import FittingResult

from .models import Product, ProductImage
from .utils import upload_product_image
from fitting.models import FittingResult

class ProductCreateListView(APIView):
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_id="createProduct",
        operation_summary="상품 등록 (관리자 전용)",
        operation_description="상품 정보와 로컬 이미지를 업로드하여 상품을 등록합니다.",
        manual_parameters=[
            openapi.Parameter('category', openapi.IN_FORM, description="카테고리 ID", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('name', openapi.IN_FORM, description="상품명", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('content', openapi.IN_FORM, description="상세 설명", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('price', openapi.IN_FORM, description="가격", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('count', openapi.IN_FORM, description="재고 수량", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('image_file', openapi.IN_FORM, description="상품 이미지 파일", type=openapi.TYPE_FILE, required=True),
        ],
        responses={201: "상품 생성 성공", 400: "잘못된 요청"},
    )
    def post(self, request):
        image_file = request.FILES.get('image_file')
        if not image_file:
            return Response({"error": "이미지 파일이 필요합니다."}, status=400)
        product = Product.objects.create(
            category_id=request.POST.get('category'),
            name=request.POST.get('name'),
            content=request.POST.get('content'),
            price=request.POST.get('price'),
            count=request.POST.get('count'),
            image=''
        )
        image_bytes = image_file.read()
        s3_url = upload_product_image(product.id, image_bytes)
        product.image = s3_url
        product.save()
        return Response({
            "message": "상품이 성공적으로 등록되었습니다.",
            "product_id": product.id,
            "s3_image_url": s3_url
        }, status=201)

        permission_classes = [AllowAny]
    permission_classes = [IsAuthenticated]

    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_id="listProducts",
        operation_summary="상품 정보 리스트",
        responses={200: "상품 리스트", 401: "로그인 필요"},
    )
    def get(self, request):
        result = []
        products = Product.objects.filter(Q(is_deleted=False) | Q(is_deleted__isnull=True))
        # show_fitting 파라미터/분기 완전 삭제!
        for product in products:
            result.append({
                "product_id": product.id,
                "name": product.name,
                "price": product.price,
                "image": product.image,  # 항상 상품 기본 이미지만 반환!
                "content": product.content
            })
        return Response({'products': result}, status=200)
    
# 상품 상세 정보(GET) & 이미지 다중 업로드(POST) - 하나의 클래스
class ProductDetailImageView(APIView):
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        operation_id="retrieveProduct",
        operation_summary="상품 상세 정보",
        responses={200: "상품 상세 정보"},
    )
    def get(self, request, product_id):
        try:
            product = Product.objects.select_related('category').get(pk=product_id)
        except Product.DoesNotExist:
            return Response({'error': '상품이 존재하지 않습니다.'}, status=404)
        product_images = list(
            ProductImage.objects.filter(product=product, is_deleted=0)
            .values_list('image', flat=True)
        )
        response_data = {
            "product_id": product.id,
            "name": product.name,
            "content": product.content,
            "price": product.price,
            "count": product.count,
            "model_image": product.image,
            "product_images": product_images,
        }
        return Response(response_data, status=200)

    @swagger_auto_schema(
        operation_summary="상품 이미지 다중 업로드",
        manual_parameters=[
            openapi.Parameter(
                name='images',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description='업로드할 이미지 파일들 (여러 장 가능)',
                required=True,
            ),
        ],
        responses={201: "업로드 성공", 400: "잘못된 요청", 404: "상품 없음"},
        )
    def post(self, request, product_id):
        product = Product.objects.filter(id=product_id).first()
        if not product:
            return Response({"error": "상품이 존재하지 않습니다."}, status=404)
        images = request.FILES.getlist('images')
        if not images:
            return Response({"error": "업로드할 이미지가 없습니다."}, status=400)
        uploaded_urls = []
        for image_file in images:
            image_bytes = image_file.read()
            s3_url = upload_product_image(product.id, image_bytes)
            ProductImage.objects.create(
                product=product,
                image=s3_url,
                is_deleted=False
            )
            uploaded_urls.append(s3_url)
        return Response({
            "product_id": product.id,
            "uploaded_images": uploaded_urls
        }, status=201)
        
class ProductFittingImageView(APIView):
    """
    특정 상품(product_id)과 특정 user_image(id) 파라미터(쿼리) 기반 fitting_result image 반환
    """
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="상품별 가상 피팅 이미지 조회",
        operation_description="상품 ID와 user_image 파라미터(pk)를 받아 해당 조합의 피팅 결과 이미지를 반환합니다.",
        manual_parameters=[
            openapi.Parameter(
                'user_image', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True,
                description="user_image 테이블의 id"
            )
        ],
        responses={
            200: openapi.Response(
                description="가상 피팅 결과 이미지 반환",
                examples={
                    "application/json": {
                        "product_id": 1,
                        "user_image_id": 5,
                        "fitting_image": "https://.../fit.jpg"
                    }
                }
            ),
            404: "결과 없음",
        }
    )
    def get(self, request, product_id):
        user_image_id = request.GET.get("user_image")
        if not user_image_id:
            return Response({"error": "user_image 파라미터가 필요합니다."}, status=400)

        # user_image 존재 확인
        try:
            user_image = UserImage.objects.get(id=user_image_id)
        except UserImage.DoesNotExist:
            return Response({"error": "user_image를 찾을 수 없습니다."}, status=404)

        # fitting_result에서 해당 조합의 결과 조회
        fitting_result = FittingResult.objects.filter(
            user_image=user_image, product_id=product_id
        ).order_by('-created_at').first()

        if not fitting_result or not fitting_result.image:
            return Response({"error": "피팅 이미지 결과가 없습니다."}, status=404)

        return Response({
            "product_id": product_id,
            "user_image_id": user_image.id,
            "fitting_image": fitting_result.image
        }, status=200)