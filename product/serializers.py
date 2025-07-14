from rest_framework import serializers
from .models import Product

class ProductCreateSerializer(serializers.ModelSerializer):
    image_file = serializers.ImageField(write_only=True, required=True)

    class Meta:
        model = Product
        fields = ['category', 'name', 'content', 'price', 'count', 'image_file']

    def create(self, validated_data):
        image_file = validated_data.pop('image_file')
        from .utils import upload_image_to_s3  # S3 업로드 함수

        # S3 업로드 후 URL 획득
        s3_url = upload_image_to_s3(image_file, folder='model_images/')

        # 상품 등록
        product = Product.objects.create(image=s3_url, **validated_data)
        return product
