#plot_app/urls.py
from django.urls import path
from . import views

app_name = 'plots'

urlpatterns = [
    path('analysis/', views.StockAnalysisView.as_view(), name='stock_analysis'),
]
