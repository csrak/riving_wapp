from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('portfolios', views.PortfolioViewSet, basename='portfolio')

urlpatterns = [
    path('management/', views.PortfolioManagementView.as_view(), name='management'),
    path('api/', include(router.urls)),
]