from django.contrib import admin
from .models import FinancialReport, FinancialData, RiskComparison, FinancialRatio,Exchange

admin.site.register(FinancialReport)
admin.site.register(FinancialData)
admin.site.register(FinancialRatio)
admin.site.register(RiskComparison)
admin.site.register(Exchange)

