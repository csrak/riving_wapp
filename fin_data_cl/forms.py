# forms.py

from django import forms
from django.db.models import Q
from .models import FinancialReport, RiskComparison, Security, Exchange


class BaseFinancialSearchForm(forms.Form):
    """
    Base form class for searching financial data with advanced filtering capabilities.
    Supports dynamic exchange-based security filtering and date-based queries.
    """
    exchange = forms.ModelChoiceField(
        queryset=Exchange.objects.all().order_by('name'),  # Alphabetical order
        label='Select Exchange',
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-dependent': 'security'  # Used by JavaScript to identify dependent fields
        }),
        empty_label="Select an Exchange"
    )

    security = forms.ModelChoiceField(
        queryset=Security.objects.none(),
        label='Select Security',
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-dependent': 'year'
        }),
        empty_label="Select a Security"
    )

    year = forms.ChoiceField(
        choices=[],
        label='Select Year',
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-dependent': 'month'
        })
    )

    month = forms.ChoiceField(
        choices=[],
        label='Select Month',
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, model_class=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_class = model_class

        # Filter exchanges and order alphabetically
        if model_class:
            available_exchanges = Exchange.objects.filter(
                security__in=Security.objects.filter(
                    Q(**{f'{model_class.__name__.lower()}_data__isnull': False})
                )
            ).distinct().order_by('name')  # Ensure sorting alphabetically
            self.fields['exchange'].queryset = available_exchanges

        selected_exchange = self.data.get('exchange') or self.initial.get('exchange')
        selected_security = self.data.get('security') or self.initial.get('security')

        # Populate securities dropdown if exchange is selected
        if selected_exchange:
            securities_queryset = Security.objects.filter(
                exchange_id=selected_exchange,
                is_active=True
            ).order_by('name')  # Ensure sorting alphabetically
            if model_class:
                securities_queryset = securities_queryset.filter(
                    Q(**{f'{model_class.__name__.lower()}_data__isnull': False})
                ).distinct()
            self.fields['security'].queryset = securities_queryset

        # Populate date fields if security is selected
        if selected_security and model_class:
            available_dates = model_class.objects.filter(
                security_id=selected_security
            ).dates('date', 'month', order='DESC')

            # Set year choices
            years = sorted(set(date.year for date in available_dates), reverse=True)
            self.fields['year'].choices = [('', 'Select Year')] + [
                (year, str(year)) for year in years
            ]

            # Set month choices if year is selected
            selected_year = self.data.get('year') or self.initial.get('year')

            if selected_year:
                months = [
                    date.month for date in available_dates
                    if date.year == int(selected_year)
                ]
                self.fields['month'].choices = [('', 'Select Month')] + [
                    (month, f"{month:02d}") for month in sorted(months)  # Numeric sorting
                ]
            else:
                self.fields['month'].choices = [('', 'Select Month')]
    def get_report_data(self):
        """
        Retrieve the financial data based on form selections.
        Returns None if the form is invalid.
        """
        if not self.is_valid() or not self.model_class:
            return None

        return self.model_class.objects.filter(
            security=self.cleaned_data['security'],
            date__year=int(self.cleaned_data['year']),
            date__month=int(self.cleaned_data['month'])
        ).select_related('security', 'security__exchange').first()


class FinancialReportSearchForm(BaseFinancialSearchForm):
    """Form for searching FinancialReport entries with specialized filtering."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, model_class=FinancialReport, **kwargs)

    def get_report(self):
        """Get the financial report matching the search criteria."""
        return self.get_report_data()


class FinancialRisksSearchForm(BaseFinancialSearchForm):
    """Form for searching RiskComparison entries with specialized filtering."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, model_class=RiskComparison, **kwargs)

    def get_risk_comparison(self):
        """Get the risk comparison data matching the search criteria."""
        return self.get_report_data()