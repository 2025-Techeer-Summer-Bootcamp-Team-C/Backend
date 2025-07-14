from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User

class SignUpSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)
    profile_image = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "password2", "profile_image") 
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def validate(self, data):
        if data["password"] != self.initial_data.get("password2"):
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")
        return data

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


    
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(  
            username=data["username"],
            password=data["password"],
        )
        if user is None:
            raise serializers.ValidationError("아이디 또는 비밀번호가 올바르지 않습니다.")

        data["user"] = user
        return data
    
class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

    def validate(self, attrs):
        from rest_framework_simplejwt.tokens import RefreshToken, TokenError
        try:
            self.token = RefreshToken(attrs["refresh_token"])
        except TokenError:
            raise serializers.ValidationError("잘못되었거나 만료된 토큰입니다.")
        return attrs

    def save(self, **kwargs):
        # 블랙리스트 테이블에 저장 → 더 이상 재사용 불가
        self.token.blacklist()
        