from django.contrib import admin
from .models import FinancialReport, FinancialData

admin.site.register(FinancialReport)
admin.site.register(FinancialData)
