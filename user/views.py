# user/views.py
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.conf import settings
from .serializers import SignUpSerializer, LoginSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class SignUpAPI(generics.CreateAPIView):
    """
    회원가입 엔드포인트
    ---
    username, email, user_gender, password, password2 를 받아 회원 생성
    """
    serializer_class = SignUpSerializer
    permission_classes = [permissions.AllowAny]  # 비로그인도 접근 허용

    def create(self, request, *args, **kwargs):
        # 사용자 생성 후 응답을 받음
        response = super().create(request, *args, **kwargs)
        
        # "message" 추가해서 새로운 Response 객체 생성
        response.data["message"] = "회원가입이 완료되었습니다."
        
        # 수정된 응답 반환
        return Response(response.data, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
    operation_summary="로그인 또는 회원가입",
    request_body=LoginSerializer,      # 요청·응답 동일하게 쓰거나 생략도 가능
    responses={200: "로그인 성공"},
)
    def post(self, request):
        # 1) 요청 검증
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        # 2) 사용자 조회 or 생성
        try:
            user = User.objects.get(username=username)
            if not check_password(password, user.password):
                return Response(
                    {"error": "비밀번호가 틀렸습니다."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            message = "로그인 성공 (기존 사용자)"
        except User.DoesNotExist:
            user = User.objects.create(
                username=username,
                password=make_password(password),
            )
            message = "로그인 성공 (신규 사용자)"

        # 3) JWT 발급
        refresh = RefreshToken.for_user(user)
        data = {
            "status": 201,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "message": message,
        }

        # 5) 쿠키 + 본문 응답
        resp = Response(data, status=status.HTTP_201_CREATED)
        resp.set_cookie(
            key="access",
            value=data["access_token"],
            httponly=True,
            samesite="Lax",
            secure=not settings.DEBUG,   # 운영환경이면 True 로!
            max_age=60 * 15,             # 15분
            path="/",
        )
        resp.set_cookie(
            key="refresh",
            value=data["refresh_token"],
            httponly=True,
            samesite="Lax",
            secure=not settings.DEBUG,
            max_age=60 * 60 * 24 * 7,    # 7일
            path="/",
        )
        return resp