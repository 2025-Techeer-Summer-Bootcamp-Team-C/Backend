# order/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db import transaction
from .models import Order, OrderItem
from product.models import Product
from user.models import CartItem, User  # ✅ user/models.py의 CartItem 사용
from .serializers import SingleOrderCreateSerializer, SingleOrderResponseSerializer, CartOrderCreateSerializer, CartOrderResponseSerializer, OrderedProductSerializer
from drf_yasg.utils import swagger_auto_schema

class SingleOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=SingleOrderCreateSerializer,
        operation_summary="단일 상품 주문",
        responses={
            201: SingleOrderResponseSerializer,
            402: '잔액이 부족합니다.',
            404: '상품을 찾을 수 없음',
            500: '서버 내부 오류'
        }
    )
    def post(self, request):
        # 1) 요청 유효성 검사
        serializer = SingleOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data['product_id']
        quantity   = serializer.validated_data['quantity']

        # 2) 상품 조회
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"message": "상품을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        user = request.user
        total_price = product.price * quantity

        # 3) 주문 전 초기 크레딧 저장
        initial_credit = user.credit

        # 4) 잔액 체크
        if initial_credit < total_price:
            return Response(
                {"message": "잔액이 부족합니다."},
                status=status.HTTP_402_PAYMENT_REQUIRED
            )

        # 5) 주문 생성
        order = Order.objects.create(user=user)
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity
        )

        # 6) 크레딧 차감 및 저장
        user.credit = initial_credit - total_price
        user.save(update_fields=['credit'])

        # 7) 응답 직렬화 (초기 크레딧, 차감 금액, 남은 크레딧 포함)
        resp_data = {
            "order_id":         order.id,
            "user_id":          user.id,
            "product_id":       product.id,
            "product_name":     product.name,
            "quantity":         quantity,
            "price_per_item":   product.price,
            "total_price":      total_price,
            "initial_credit":   initial_credit,      # 🆕 주문 전 초기 크레딧
            "deducted_credit":  total_price,         # 🆕 차감된 크레딧
            "remaining_credit": user.credit,         # 🆕 차감 후 잔여 크레딧
            "status":           order.status,
            "created_at":       order.created_at,
            "message":          "주문이 성공적으로 생성되었습니다."
        }
        resp_serializer = SingleOrderResponseSerializer(resp_data)
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


class CartOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=CartOrderCreateSerializer,
        operation_summary="장바구니 상품 주문",
        responses={
            201: CartOrderResponseSerializer,
            400: '선택된 장바구니 상품이 없습니다.',
            402: '잔액이 부족합니다.',
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

        # 1) 선택된 상품 유무 체크
        if not cart_product_ids:
            return Response({"message": "선택된 장바구니 상품이 없습니다."}, status=400)

        # 2) 실제 장바구니 아이템 조회
        cart_items = CartItem.objects.filter(user=user, product_id__in=cart_product_ids)
        if not cart_items.exists():
            return Response({"message": "해당 장바구니 상품이 존재하지 않습니다."}, status=404)

        # 3) 총 주문 금액 계산
        total_price = sum(item.quantity * item.product.price for item in cart_items)

        # 4) 크레딧 부족 체크
        initial_credit = user.credit
        if total_price > initial_credit:
            return Response({"message": "잔액이 부족합니다."}, status=402)

        # 5) 주문 생성 & OrderItem 생성
        order = Order.objects.create(user=user)
        ordered_products = []
        for item in cart_items:
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
            prod_total = item.quantity * item.product.price
            ordered_products.append({
                "product_id":     item.product.id,
                "product_name":   item.product.name,
                "quantity":       item.quantity,
                "price_per_item": item.product.price,
                "total_price":    prod_total,
            })

        # 6) 크레딧 차감
        user.credit = initial_credit - total_price
        user.save()

        # 7) 장바구니 삭제
        cart_items.delete()

        # 8) 응답 데이터 구성
        resp = {
            "order_id":         order.id,
            "user_id":          user.id,
            "total_price":      total_price,
            "status":           order.status,
            "created_at":       order.created_at,
            "ordered_products": ordered_products,
            "initial_credit":   initial_credit,
            "deducted_credit":  total_price,
            "remaining_credit": user.credit,
            "message":          "선택한 장바구니 상품으로 주문이 생성되었습니다."
        }
        return Response(resp, status=201)