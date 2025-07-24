from rest_framework import serializers
from .models import Product

class ProductCreateSerializer(serializers.ModelSerializer):
    image_file = serializers.ImageField(write_only=True, required=True)

    class Meta:
        model = Product
        fields = ['category', 'name', 'content', 'price', 'count', 'image_file']

    def create(self, validated_data):
        image_file = validated_data.pop('image_file')
        image_bytes = image_file.read()

        from .utils import upload_product_image
        # product 생성 전 임시 product_id 할당: 새 product의 PK가 실제로 필요한 경우엔 저장 후 처리
        product = Product.objects.create(**validated_data, image='')  # 먼저 인스턴스 생성
        s3_url = upload_product_image(product.id, image_bytes)

        product.image = s3_url
        product.save(update_fields=["image"])
        return product
