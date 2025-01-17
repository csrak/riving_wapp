
#portfolios/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import viewsets, views
from fin_data_cl import views as parent_views
app_name = 'portfolios'
# Create router and register viewsets
router = DefaultRouter()

# Dictionary mapping URL prefixes to viewsets and their templates
VIEWSET_MAPPING = {
    'portfolios': {
        'viewset': viewsets.PortfolioViewSet,
        'templates': ['portfolio_manager', 'portfolio_analysis']
    },
    'optimizations': {
        'viewset': viewsets.OptimizationViewSet,
        'templates': ['portfolio_optimizer', 'optimization_results']
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
    *template_patterns,  # Unpack all template patterns
]
