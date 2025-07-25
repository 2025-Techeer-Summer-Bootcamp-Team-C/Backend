from django.urls import path
from .views import SingleOrderCreateView, CartOrderCreateView

urlpatterns = [
    # 주문하기 (단일 상품)
    path('single/', SingleOrderCreateView.as_view(), name='order-single'),

    # 장바구니 상품으로 주문하기
    path('cart/', CartOrderCreateView.as_view(), name='order-cart'),
]