# user/views.py
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.conf import settings
from .serializers import SignUpSerializer, LoginSerializer, LogoutSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User


class SignUpAPI(generics.CreateAPIView):
    serializer_class = SignUpSerializer
    permission_classes = [permissions.AllowAny]  
    
    @swagger_auto_schema(operation_summary="회원가입")
    def post(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data["message"] = "회원가입이 완료되었습니다."
        return Response(response.data, status=status.HTTP_201_CREATED)

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

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "존재하지 않는 ID 입니다."},
                            status=status.HTTP_404_NOT_FOUND)

        if not check_password(password, user.password):
            return Response({"error": "비밀번호가 틀렸습니다."},
                            status=status.HTTP_401_UNAUTHORIZED)

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
                        secure=not settings.DEBUG, path="/", max_age=60*15)
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