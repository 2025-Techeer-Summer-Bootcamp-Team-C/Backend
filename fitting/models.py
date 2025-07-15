from django.db import models
from django.conf import settings

class UserImage(models.Model):
    user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='user_id',
        db_index=True,
        null=False,
    )
    user_image_url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_image'
    
    def __str__(self):
        return f"UserImage {self.id}"

class FittingResult(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fitting_results',
        verbose_name="사용자 아이디"
    )
    product = models.ForeignKey(
        'product.Product',
        on_delete=models.CASCADE,
        related_name='fitting_results',
        verbose_name="상품 아이디"
    )
    image = models.CharField(max_length=255, null=True, blank=True, verbose_name="피팅사진 주소")
    video = models.CharField(max_length=255, null=True, blank=True, verbose_name="피팅영상")
    create_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="수정일시")
    is_deleted = models.BooleanField(null=True, blank=True, verbose_name="삭제여부")

    class Meta:
        db_table = 'fitting_result'

    def __str__(self):
        return f"FittingResult {self.id} - User {self.user_id} - Product {self.product_id}"

