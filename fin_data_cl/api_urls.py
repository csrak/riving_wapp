# # fin_data_cl/api_url.py
# from django.urls import path
# from . import views
#
# app_name = 'fin_data_api'
#
# urlpatterns = [
#     # Risk comparison specific endpoints
#     path('risks/exchanges/<int:exchange_id>/securities/', views.get_securities_for_exchange, name='risk_securities'),
#     path('risks/securities/<int:security_id>/years/', views.get_years_for_security, name='risk_years'),
#     path('risks/securities/<int:security_id>/years/<int:year>/months/', views.get_months_for_year, name='risk_months'),
#     path('risks/save-session-data/', views.save_session_data, name='save_session_data'),
#
#     # Financial report specific endpoints
#     path('reports/exchanges/<int:exchange_id>/securities/', views.get_securities_for_exchange,
#          name='securities_by_exchange'),
#     path('reports/securities/<int:security_id>/years/', views.get_years_for_security, name='security_years'),
#     path('reports/securities/<int:security_id>/years/<int:year>/months/', views.get_months_for_year,
#          name='security_months'),
#
#     # Price data endpoints
#     path('securities/prices/', views.get_security_prices, name='security_prices'),
#
#     # Screener endpoints
#     path('ratios/filter/', views.filter_ratios, name='filter_ratios'),
#
#     path('data/', views.get_data, name='get_data'),
#     path('suggestions/', views.ticker_suggestions, name='ticker_suggestions'),
# ]