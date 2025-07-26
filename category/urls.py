# category/urls.py

from django.urls import path
from .views import CategoryProductByIdView, CategoryCreateView

urlpatterns = [
    path('', CategoryProductByIdView.as_view(), name='category-products-list'),
    path('category/', CategoryCreateView.as_view(), name='create-category'),
]
