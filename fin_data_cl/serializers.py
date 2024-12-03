# serializers.py
from rest_framework import serializers
from .models import FinancialReport

class FinancialReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialReport
        fields = [
            'ticker',
            'year',
            'month',
            'business_overview',
            'risks',
            'metrics',
            'historical_changes',
            'future_outlook'
        ]