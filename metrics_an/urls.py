#metrics_an/urls.py
from django.urls import path
from . import views

app_name = 'metrics'

urlpatterns = [
    path('plotter/', views.metric_plotter_view, name='metric_plotter'),
]
