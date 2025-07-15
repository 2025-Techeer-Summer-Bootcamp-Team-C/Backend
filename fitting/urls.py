from django.urls import path
from .views import *

urlpatterns = [
    path('images_test',VTOOneShotView.as_view(),name='generate_vto'),
    path('images/products',VTOProductView.as_view(),name='generate_vto_product'),
    path('images/test',VTOTestView.as_view(),name='vto_test'),
    path('images', ProductFittingGenerateView.as_view(), name='generate_product_fitting'),
]