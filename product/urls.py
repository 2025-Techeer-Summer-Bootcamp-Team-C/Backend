from django.urls import path
from .views import ProductCreateView

urlpatterns = [
    path('products', ProductCreateView.as_view(), name='product-create'),
]
