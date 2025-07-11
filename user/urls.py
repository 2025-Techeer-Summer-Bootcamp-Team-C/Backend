from django.urls import path
from .views import SignUpAPI, LoginView

urlpatterns = [
    path("signup", SignUpAPI.as_view(), name="api-signup"),
    path("login",  LoginView.as_view(),  name="api-login"),
]
