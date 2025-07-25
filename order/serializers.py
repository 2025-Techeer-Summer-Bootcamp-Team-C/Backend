# order/serializers.py
from rest_framework import serializers

class SingleOrderCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(
        help_text="주문할 상품의 ID"
    )
    quantity = serializers.IntegerField(
        default=1,
        help_text="수량 (기본값: 1)"
    )

class SingleOrderResponseSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    quantity = serializers.IntegerField()
    price_per_item = serializers.IntegerField()
    total_price = serializers.IntegerField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()

class CartOrderCreateSerializer(serializers.Serializer):
    cart_product_ids = serializers.ListField(
    child=serializers.IntegerField(),
    help_text="주문할 장바구니 상품의 ID 리스트"
)

class OrderedProductSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(help_text="상품 ID")
    product_name = serializers.CharField(help_text="상품명")
    quantity = serializers.IntegerField(help_text="수량")
    price_per_item = serializers.IntegerField(help_text="상품 단가")
    total_price = serializers.IntegerField(help_text="상품별 총 가격")

class CartOrderResponseSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(help_text="생성된 주문 ID")
    user_id = serializers.IntegerField(help_text="주문자(유저) ID")
    total_price = serializers.IntegerField(help_text="전체 주문 금액")
    status = serializers.CharField(help_text="주문 상태")
    created_at = serializers.DateTimeField(help_text="주문 생성 시각")
    ordered_products = OrderedProductSerializer(
        many=True,
        help_text="주문된 상품 상세 목록"
    )
    message = serializers.CharField(help_text="응답 메시지")