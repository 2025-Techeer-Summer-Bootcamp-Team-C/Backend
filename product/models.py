from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=20, verbose_name="카테고리 명")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="수정일시")
    is_deleted = models.BooleanField(null=True, blank=True, verbose_name="삭제여부")

    class Meta:
        db_table = 'category'

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="카테고리 아이디")
    name = models.CharField(max_length=30, verbose_name="상품명")
    content = models.TextField(verbose_name="상세 설명")
    price = models.IntegerField(verbose_name="가격")
    count = models.IntegerField(verbose_name="재고")
    image = models.CharField(max_length=255, verbose_name="모델 이미지 주소")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="수정일시")
    is_deleted = models.BooleanField(null=True, blank=True, verbose_name="삭제여부")

    class Meta:
        db_table = 'product'

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_images', verbose_name="상품 아이디")
    image = models.CharField(max_length=255, verbose_name="상품 이미지 주소")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name="수정일시")
    is_deleted = models.BooleanField(null=True, blank=True, verbose_name="삭제여부")

    class Meta:
        db_table = 'product_image'

    def __str__(self):
        return f"{self.product.name} 이미지"

