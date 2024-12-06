#metrics_api/urls.py
from django.urls import path
from . import views

app_name = 'metrics_api'

urlpatterns = [
    path('exchanges/', views.get_exchanges, name='exchanges'),
    path('securities/<str:exchange_code>/', views.get_securities, name='securities'),
    path('data/<int:security_id>/', views.get_metric_data, name='metric_data'),
]