from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StockAnalysisView,
    SecurityViewSet,
    StockAnalysisViewSet
)

router = DefaultRouter()
router.register(r'stock-securities', SecurityViewSet, basename='stock-security')
router.register(r'stock-analysis', StockAnalysisViewSet, basename='stock-analysis')

urlpatterns = [
    path('price_plot/', StockAnalysisView.as_view(), name='stock_analysis'),
    path('api/', include(router.urls)),
]