from django.urls import path
from .views import SignUpAPI, LoginAPI

urlpatterns = [
    path("signup/", SignUpAPI.as_view(), name="api-signup"),
    path("login/",  LoginAPI.as_view(),  name="api-login"),
]
