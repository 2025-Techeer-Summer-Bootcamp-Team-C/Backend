from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf.urls.static import static
from django.conf import settings
import os

if os.getenv('ENVIRONMENT') == 'prod':
    default_api_url = 'https://techeerfashion.shop/api/v1'
else:
    default_api_url = 'http://localhost:8000/api/v1'

schema_view = get_schema_view(
    openapi.Info(
        title="API Documentation",
        default_version='v1',
        description="API description",
        contact=openapi.Contact(email="contact@myapi.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    url=os.getenv('SWAGGER_BASE_URL') or default_api_url,
)

urlpatterns = [
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path("api/v1/", include([
        path("fittings/", include('fitting.urls')),
        path("users/", include("user.urls")),
        path('products/',include('product.urls')),
        path('categories/',include('category.urls')),
        
    ])),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
