from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('screener/', views.screener, name='screener'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('get_data/', views.get_data, name='get_data'),
    path('ticker_suggestions/', views.ticker_suggestions, name='ticker_suggestions'),
    path('filter_ratios/', views.filter_ratios, name='filter_ratios'),
    path('financial_reports/', views.search_financial_report, name='financial_reports'),
    path('financial_risks/', views.search_financial_risks, name='financial_risks'),
    path('securities/<int:exchange_id>/', views.get_securities_for_exchange, name='get_securities'),
    path('dates/<int:security_id>/',  views.get_years_for_security, name='get_years'),
    path('months/<int:security_id>/<int:year>/',  views.get_months_for_year,    name='get_months'),
]

