from django.urls import path
from .views import *

urlpatterns = [
    path('products', ProductCreateView.as_view(), name='product-create'),
    path('products/<int:product_id>/images', ProductImageUploadView.as_view(), name='product-images-upload'),
]
