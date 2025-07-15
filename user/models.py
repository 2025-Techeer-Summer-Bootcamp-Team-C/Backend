from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class User(AbstractUser):
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="사용자 이름",
        help_text="한글 포함 가능",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="수정일")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="삭제일")

    def __str__(self):
        return f"{self.username} ({self.email})"

    class Meta:
        db_table = 'user'  
        
    profile_image = models.CharField(max_length=255, null=True, blank=True,verbose_name="사용자 사진 이미지 주소")