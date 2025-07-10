# user/views.py
from rest_framework.views import APIView
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .serializers import SignUpSerializer, LoginSerializer
from drf_yasg.utils import swagger_auto_schema

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

class LoginAPI(APIView):
    permission_classes = [permissions.AllowAny]  # 비로그인도 호출 가능

    @swagger_auto_schema(request_body=LoginSerializer, responses={201: LoginSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_201_CREATED)
    
    
