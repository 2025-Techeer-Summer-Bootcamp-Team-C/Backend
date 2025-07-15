from django.urls import path
from .views import SignUpAPI, LoginView, LogoutView, CookieTokenRefreshView, CartItemCreateAPIView

urlpatterns = [
    path("signup", SignUpAPI.as_view(), name="api-signup"),
    path("login",  LoginView.as_view(),  name="api-login"),
    path("logout", LogoutView.as_view(), name="api-logout"),
    path("token/refresh", CookieTokenRefreshView.as_view()),
    path('cart', CartItemCreateAPIView.as_view(), name='cart-add'),
]
