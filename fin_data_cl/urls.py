#fin_data_cl/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets, views
from .more_views import index
app_name = 'fin_data'
# Create router and register viewsets
router = DefaultRouter()

# Dictionary mapping URL prefixes to viewsets and their templates
VIEWSET_MAPPING = {
    'price-data': {
        'viewset': viewsets.PriceDataViewSet,
        'templates': ['price_charts', 'price_analysis']  # Example templates that use this viewset
    },
    'financial-data': {
        'viewset': viewsets.FinancialDataViewSet,
        'templates': ['financial_analysis']
    },
    'financial-ratios': {
        'viewset': viewsets.FinancialRatioViewSet,
        'templates': ['screener', 'ratio_analysis']
    },
    'financial-reports': {
        'viewset': viewsets.FinancialReportViewSet,
        'templates': ['reports', 'reports_comparison']
    },
    'risk-comparisons': {
        'viewset': viewsets.RiskComparisonViewSet,
        'templates': ['risks','risk_analysis']
    },
    'dividends': {
        'viewset': viewsets.DividendDataViewSet,
        'templates': ['dividend_analysis']
    },
}

# Register all viewsets
for prefix, config in VIEWSET_MAPPING.items():
    router.register(prefix, config['viewset'], basename=prefix)

# Generate URL patterns for templates
template_patterns = [
    path(f"{template}/",
         views.generic_data_view,
         {'template_name': template},
         name=template)
    for config in VIEWSET_MAPPING.values()
    for template in config['templates']
]

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('', index.index, name='index'),
    *template_patterns,  # Unpack all template patterns
]
