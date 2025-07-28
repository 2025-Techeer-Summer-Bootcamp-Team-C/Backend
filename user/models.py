from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from product.models import Product

class User(AbstractUser):
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="사용자 이름",
        help_text="한글 포함 가능",
    )
    credit = models.IntegerField(
        default=300000,
        verbose_name="크레딧(원)",
        help_text="사용자 초기 크레딧은 300,000원입니다."
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="수정일")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="삭제일")
    is_fitting = models.BooleanField(default=False, verbose_name="합성 여부")
    
    def __str__(self):
        return f"{self.username} ({self.email})"

    class Meta:
        db_table = 'user'  
        
    profile_image = models.CharField(max_length=255, null=True, blank=True,verbose_name="사용자 사진 이미지 주소")
    
class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name} x {self.quantity}"

class UserImage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="사용자 아이디",
        related_name="user_images"
    )
    image = models.CharField(max_length=255, verbose_name="사용자 이미지 주소")
    is_fitting = models.BooleanField(default=False,verbose_name="가상피팅 유무")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="수정일")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="삭제일")

    class Meta:
        db_table = 'user_image'
        verbose_name = "사용자 사진"
        verbose_name_plural = "사용자 사진 목록"

    def __str__(self):
        return f"{self.user.username} - {self.image}"