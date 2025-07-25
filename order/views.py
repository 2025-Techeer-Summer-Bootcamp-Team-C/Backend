# order/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import transaction
from .models import Order, OrderItem
from product.models import Product
from user.models import CartItem  # ✅ user/models.py의 CartItem 사용
from .serializers import SingleOrderCreateSerializer, SingleOrderResponseSerializer, CartOrderCreateSerializer, CartOrderResponseSerializer, OrderedProductSerializer
from drf_yasg.utils import swagger_auto_schema

class SingleOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=SingleOrderCreateSerializer,
        responses={
            201: SingleOrderResponseSerializer,
            404: '상품을 찾을 수 없음',
            500: '서버 내부 오류'
        }
    )
    def post(self, request):
        # 1) 요청 유효성 검사
        serializer = SingleOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']

        # 2) 상품 조회
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"message": "상품을 찾을 수 없습니다."}, status=404)

        # 3) 주문 생성
        order = Order.objects.create(user=request.user)
        OrderItem.objects.create(order=order, product=product, quantity=quantity)

        # 4) 응답 직렬화
        resp_data = {
            "order_id":       order.id,
            "user_id":        request.user.id,
            "product_id":     product.id,
            "product_name":   product.name,
            "quantity":       quantity,
            "price_per_item": product.price,
            "total_price":    product.price * quantity,
            "status":         order.status,
            "created_at":     order.created_at,
        }
        resp_serializer = SingleOrderResponseSerializer(resp_data)
        return Response(resp_serializer.data, status=201)


class CartOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=CartOrderCreateSerializer,
        responses={
            201: CartOrderResponseSerializer,
            400: '선택된 장바구니 상품이 없습니다.',
            404: '해당 장바구니 상품이 존재하지 않습니다.',
            500: '서버 내부 오류'
        }
    )
    @transaction.atomic
    def post(self, request):
        user = request.user
        serializer = CartOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart_product_ids = serializer.validated_data['cart_product_ids']

        if not cart_product_ids:
            return Response({"message": "선택된 장바구니 상품이 없습니다."}, status=400)

        cart_items = CartItem.objects.filter(user=user, product_id__in=cart_product_ids)
        if not cart_items.exists():
            return Response({"message": "해당 장바구니 상품이 존재하지 않습니다."}, status=404)

        order = Order.objects.create(user=user)
        ordered_products = []
        total_price = 0

        for item in cart_items:
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
            product_total = item.quantity * item.product.price
            ordered_products.append({
                "product_id": item.product.id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "price_per_item": item.product.price,
                "total_price": product_total
            })
            total_price += product_total

        cart_items.delete()

        resp = {
            "order_id": order.id,
            "user_id": user.id,
            "total_price": total_price,
            "status": order.status,
            "created_at": order.created_at,
            "ordered_products": ordered_products,
            "message": "선택한 장바구니 상품으로 주문이 생성되었습니다."
        }
        return Response(resp, status=201)