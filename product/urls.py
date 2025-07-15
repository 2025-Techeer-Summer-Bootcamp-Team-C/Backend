from django.urls import path
from .views import *

urlpatterns = [
    path('', ProductCreateView.as_view(), name='product-create'),
    path('<int:product_id>/images', ProductImageUploadView.as_view(), name='product-images-upload'),
]
