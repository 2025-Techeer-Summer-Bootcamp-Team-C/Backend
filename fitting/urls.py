from django.urls import path
from .views import *

urlpatterns = [
    path('images_test',VTOOneShotView.as_view(),name='generate_vto'),
    path('images/products',VTOProductView.as_view(),name='generate_vto_product'),
    path('images/test',VTOTestView.as_view(),name='vto_test'),
    path('images', ProductFittingGenerateView.as_view(),name='generate_product_fitting'),
    path('images/remove-bg', RemoveBgView.as_view(),name='remove_bg_test'),
    path('images/edit-bg-white', EditBgWhiteView.as_view(),name='edit_bg_white'),
    path('images/detail',ProductFittingGenerateDetailView.as_view(),name='generate_product_detail_fitting'),
    path('<int:product_id>/videos',ProductFittingVideoGenerateView.as_view(),name='generate_product_fitting_video'),
    path('<int:product_id>/videos/status',ProductFittingVideoStatusView.as_view(),name='fitting-status'),
]