# forms.py
from django import forms
from .models import FinancialReport, RiskComparison

class FinancialReportSearchForm(forms.Form):
    ticker = forms.ChoiceField(choices=[], label='Select Ticker')
    year = forms.ChoiceField(choices=[], label='Select Year')
    month = forms.ChoiceField(choices=[(3, 'March'), (6, 'June'), (9, 'September'), (12, 'December')], label='Select Month')

    def __init__(self, *args, **kwargs):
        super(FinancialReportSearchForm, self).__init__(*args, **kwargs)
        # Dynamically load available tickers and years from the database
        self.fields['ticker'].choices = [
            (report['ticker'], report['ticker']) for report in FinancialReport.objects.values('ticker').distinct()
        ]
        self.fields['year'].choices = [
            (report['year'], report['year']) for report in FinancialReport.objects.values('year').distinct()
        ]
class FinancialRisksSearchForm(forms.Form):
    ticker = forms.ChoiceField(choices=[], label='Select Ticker')
    year = forms.ChoiceField(choices=[], label='Select Year')
    month = forms.ChoiceField(choices=[(3, 'March'), (6, 'June'), (9, 'September'), (12, 'December')], label='Select Month')

    def __init__(self, *args, **kwargs):
        super(FinancialRisksSearchForm, self).__init__(*args, **kwargs)
        # Dynamically load available tickers and years from the database
        self.fields['ticker'].choices = [
            (report['ticker'], report['ticker']) for report in RiskComparison.objects.values('ticker').distinct()
        ]
        self.fields['year'].choices = [
            (report['year'], report['year']) for report in RiskComparison.objects.values('year').distinct()
        ]