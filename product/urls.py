from django.urls import path
from .views import ProductCreateListView, ProductDetailImageView

urlpatterns = [
    path('', ProductCreateListView.as_view(), name='product-create'),                         # POST /products/
    path('<int:product_id>', ProductDetailImageView.as_view(), name='product-detail'),        # GET  /products/{product_id}    path('<int:product_id>/images', ProductDetailImageView.as_view(), name='product-images'), # POST /products/{product_id}/images
]
