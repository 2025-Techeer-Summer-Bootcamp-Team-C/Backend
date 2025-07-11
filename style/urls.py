from django.urls import path
from .views import GenerateGeminiStyleView,GoogleShoppingSearchView

urlpatterns = [
    path('', GenerateGeminiStyleView.as_view(), name='gemini_style'),
    path('search/', GoogleShoppingSearchView.as_view(), name='google_shopping_search'),
]
