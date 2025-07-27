from product.models import Category, Product
from rest_framework import serializers
from product.models import Category

class ProductInCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'image')

class CategoryWithProductsSerializer(serializers.ModelSerializer):
    products = ProductInCategorySerializer(source='product_set', many=True)
    class Meta:
        model = Category
        fields = ('id', 'name', 'products')

class CategoryCreateSerializer(serializers.ModelSerializer):
    # 클라이언트로부터 category_name 필드로 입력을 받되, 내부적으로는 Category.name 필드에 매핑
    category_name = serializers.CharField(source='name')

    class Meta:
        model = Category
        fields = ['category_name']