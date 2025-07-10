from django.urls import path
from .views import *

urlpatterns = [
    path('images',VTOOneShotView.as_view(),name='generate_vto'),
]