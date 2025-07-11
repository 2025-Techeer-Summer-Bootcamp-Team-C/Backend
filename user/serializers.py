from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User


class SignUpSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "user_gender", "password", "password2")

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")
        if User.objects.filter(username=data["username"]).exists():
            raise serializers.ValidationError("이미 사용 중인 ID 입니다.")
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