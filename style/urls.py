from django.urls import path
from .views import GenerateGeminiStyleView

urlpatterns = [
    path('', GenerateGeminiStyleView.as_view(), name='gemini_style'),
]
