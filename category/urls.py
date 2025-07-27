from django.urls import path
from .views import CategoryProductByIdView, CategoryView, CategoryListView

urlpatterns = [
    path('<int:category_id>', CategoryProductByIdView.as_view(), name='category-products-list'),
    path('', CategoryView.as_view(), name='create-category'),
    path('list', CategoryListView.as_view(), name='category-list'),
]
