from django.contrib import admin
from .models import FinancialReport, FinancialData, RiskComparison

admin.site.register(FinancialReport)
admin.site.register(FinancialData)
admin.site.register(RiskComparison)
