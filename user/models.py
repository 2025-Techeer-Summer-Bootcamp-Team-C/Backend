from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class User(AbstractUser):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )

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
        db_table = 'user'  
        
        
class WishlistProduct(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_products",
    )
    product_name = models.CharField(max_length=255)
    url = models.URLField(null=True, blank=True)
    price = models.PositiveIntegerField()
    image_url = models.URLField(null=True, blank=True)
    brand = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "url")  # 같은 상품 중복 방지
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.product_name}"
