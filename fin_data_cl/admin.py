from django.contrib import admin
from .models import FinancialReport, FinancialData, RiskComparison, FinancialRatio,Exchange, Security, DividendData, PriceData

admin.site.register(FinancialReport)
admin.site.register(FinancialData)
admin.site.register(FinancialRatio)
admin.site.register(RiskComparison)
admin.site.register(Exchange)
admin.site.register(Security)
admin.site.register(DividendData)
admin.site.register(PriceData)