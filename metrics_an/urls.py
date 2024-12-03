from django.urls import path
from . import views

urlpatterns = [
    path('financial/metric-plotter/', views.metric_plotter_view, name='financial_metric_plotter'),
    path('api/exchanges/', views.get_exchanges, name='api_get_exchanges'),
    path('api/securities/<str:exchange_code>/', views.get_securities, name='api_get_securities'),
    path('api/metrics/<int:security_id>/', views.get_metric_data, name='api_get_metric_data'),
]