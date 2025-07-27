from django.urls import path
from .views import *

urlpatterns = [
    path("signup", SignUpAPI.as_view(), name="api-signup"),
    path("login",  LoginView.as_view(),  name="api-login"),
    path("logout", LogoutView.as_view(), name="api-logout"),
    path("token/refresh", CookieTokenRefreshView.as_view()),
    path('cart', CartItemCreateAPIView.as_view(), name='cart-add'),
    path('cart/list', CartItemListAPIView.as_view(), name='cart-list'),
    path('cart/<int:cart_product_id>', CartItemUpdateAPIView.as_view(), name='cart-update'),
    path("profile-image", UpdateProfileImageAPI.as_view(), name="update_profile_image"),
    path("images", UserImageListAPI.as_view(), name="user_image_list"),
    path('images/<int:user_image_id>', UserImageDeleteAPI.as_view(), name='users_image_delete'),
]
