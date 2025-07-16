# category/urls.py

from django.urls import path
from .views import CategoryProductByIdView

urlpatterns = [
    path('', CategoryProductByIdView.as_view(), name='category-products-list'),
]
