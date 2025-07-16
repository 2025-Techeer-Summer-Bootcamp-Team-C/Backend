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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="수정일")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="삭제일")

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
    is_fitting = models.BooleanField(default=False, verbose_name="합성 여부")

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name} x {self.quantity}"