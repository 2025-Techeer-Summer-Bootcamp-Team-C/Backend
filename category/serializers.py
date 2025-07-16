from product.models import Category, Product
from rest_framework import serializers

class ProductInCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'image')

class CategoryWithProductsSerializer(serializers.ModelSerializer):
    products = ProductInCategorySerializer(source='product_set', many=True)
    class Meta:
        model = Category
        fields = ('id', 'name', 'products')
