#price_plots/api_urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'plots_api'

router = DefaultRouter()
router.register(r'securities', views.SecurityViewSet, basename='securities')
router.register(r'analysis', views.StockAnalysisViewSet, basename='analysis')

urlpatterns = [
    path('', include(router.urls)),
]