from django.urls import path
from . import views

urlpatterns = [
    path('price_plot/', views.stock_chart_view, name='price_plot'),
]

