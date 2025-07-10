from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )

    # ERD 필드 매핑
    user_gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        null=True,
        blank=True,
        verbose_name="성별"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="수정일")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="삭제일")

    def __str__(self):
        return f"{self.username} ({self.email})"

    class Meta:
        db_table = 'user'  # 테이블명을 user 로 고정
