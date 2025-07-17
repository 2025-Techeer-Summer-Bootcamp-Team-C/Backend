from django.urls import path
from .views import *

urlpatterns = [
    path('', ProductCreateView.as_view(), name='product-create'),
    path('<int:product_id>/images', ProductImageUploadView.as_view(), name='product-images-upload'),
    path('information/', ProductInfoListView.as_view(), name='product-info-list'),
    path('<int:product_id>', ProductDetailView.as_view(), name='product-detail'),
]
