from rest_framework import serializers

class GeminiStyleURLSerializer(serializers.Serializer):
    image_url = serializers.URLField(help_text="분석할 이미지의 URL")

class GeminiStyleResultSerializer(serializers.Serializer):
    result = serializers.CharField(help_text="스타일 키워드 결과 (예: #미니멀 #스트리트 #빈티지 #캐주얼 #모던)")

class ShoppingSearchRequestSerializer(serializers.Serializer):
    category = serializers.CharField(help_text="상품 카테고리 (예: 상의)")
    detail = serializers.CharField(help_text="상품 상세 (예: 반팔)")
    message = serializers.CharField(help_text="추가 메시지 또는 분석 내용")

class ShoppingProductSerializer(serializers.Serializer):
    product_id = serializers.CharField(help_text="상품 ID")
    product_name = serializers.CharField(help_text="상품명")
    price = serializers.IntegerField(help_text="가격")
    url = serializers.URLField(help_text="상품 링크")
    image_url = serializers.URLField(help_text="상품 이미지 URL")

class ShoppingSearchResponseSerializer(serializers.Serializer):
    status = serializers.IntegerField(help_text="상태 코드")
    results = ShoppingProductSerializer(many=True)