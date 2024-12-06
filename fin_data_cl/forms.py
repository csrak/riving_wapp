#fin_data_cl/forms.py
from django import forms
from django.db.models import Q
from .models import FinancialReport, RiskComparison, Security, Exchange


class BaseFinancialSearchForm(forms.Form):
    """
    Base form class for searching financial data with advanced filtering capabilities.
    Supports dynamic exchange-based security filtering and date-based queries.
    """
    exchange = forms.ModelChoiceField(
        queryset=Exchange.objects.none(),
        label="Select Exchange",
        required=True,
        widget=forms.Select(attrs={
            "class": "form-control",
            "data-dependent": "security"
        }),
        empty_label="Select an Exchange"
    )

    security = forms.ModelChoiceField(
        queryset=Security.objects.none(),
        label="Select Security",
        required=True,
        widget=forms.Select(attrs={
            "class": "form-control",
            "data-dependent": "year"
        }),
        empty_label="Select a Security"
    )

    year = forms.ChoiceField(
        choices=[],
        label="Select Year",
        required=True,
        widget=forms.Select(attrs={
            "class": "form-control",
            "data-dependent": "month"
        })
    )

    month = forms.ChoiceField(
        choices=[],
        label="Select Month",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"})
    )

    def __init__(self, *args, model_class=None, **kwargs):
        self.model_class = model_class  # Directly assign the model_class
        super().__init__(*args, **kwargs)

        if self.model_class:
            # Populate exchanges dynamically
            available_exchanges = Exchange.objects.filter(
                security__in=Security.objects.filter(
                    Q(**{f"{self.model_class.__name__.lower()}_data__isnull": False})
                )
            ).distinct().order_by("name")
            self.fields["exchange"].queryset = available_exchanges

        # Populate securities and date fields if initial data exists
        selected_exchange = self.data.get("exchange") or self.initial.get("exchange")
        selected_security = self.data.get("security") or self.initial.get("security")

        if selected_exchange:
            securities_queryset = Security.objects.filter(
                exchange_id=selected_exchange,
                is_active=True
            )
            if self.model_class:
                securities_queryset = securities_queryset.filter(
                    Q(**{f"{self.model_class.__name__.lower()}_data__isnull": False})
                ).distinct().order_by("name")
            self.fields["security"].queryset = securities_queryset

        if selected_security and self.model_class:
            available_dates = self.model_class.objects.filter(
                security_id=selected_security
            ).dates("date", "month", order="DESC")

            # Populate year choices
            years = sorted(set(date.year for date in available_dates), reverse=True)
            self.fields["year"].choices = [("", "Select Year")] + [
                (year, str(year)) for year in years
            ]

            # Populate month choices if year is selected
            selected_year = self.data.get("year") or self.initial.get("year")
            if selected_year:
                months = [
                    date.month for date in available_dates
                    if date.year == int(selected_year)
                ]
                self.fields["month"].choices = [("", "Select Month")] + [
                    (month, f"{month:02d}") for month in sorted(months)
                ]
            else:
                self.fields["month"].choices = [("", "Select Month")]

    def get_report_data(self):
        """
        Retrieve the financial data based on form selections.
        Returns None if the form is invalid.
        """
        if not self.is_valid() or not self.model_class:
            return None

        query = self.model_class.objects.filter(
            security=self.cleaned_data["security"],
            date__year=int(self.cleaned_data["year"]),
            date__month=int(self.cleaned_data["month"])
        )
        print(f"Constructed Query: {query.query}")  # Debugging output
        return query.first()


class FinancialReportSearchForm(BaseFinancialSearchForm):
    """Form for searching FinancialReport entries with specialized filtering."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, model_class=FinancialReport, **kwargs)

    def get_report(self):
        """Get the financial report matching the search criteria."""
        return self.get_report_data()


class FinancialRisksSearchForm(BaseFinancialSearchForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, model_class=RiskComparison, **kwargs)

        # Get current values
        current_security = self.data.get(f"{self.prefix}-security") if self.is_bound else None
        current_year = self.data.get(f"{self.prefix}-year") if self.is_bound else None
        current_month = self.data.get(f"{self.prefix}-month") if self.is_bound else None

        if current_security:
            # Update year choices
            dates = RiskComparison.objects.filter(
                security_id=current_security
            ).dates('date', 'year', order='DESC')
            years = sorted(set(date.year for date in dates), reverse=True)
            self.fields['year'].choices = [('', 'Select Year')] + [(str(y), str(y)) for y in years]

        if current_security and current_year:
            # Update month choices
            dates = RiskComparison.objects.filter(
                security_id=current_security,
                date__year=current_year
            ).dates('date', 'month', order='DESC')
            months = sorted(set(date.month for date in dates))
            self.fields['month'].choices = [('', 'Select Month')] + [(str(m), str(m)) for m in months]

    def get_risk_comparison(self):
        if not self.is_valid():
            return None
        return RiskComparison.objects.filter(
            security=self.cleaned_data['security'],
            date__year=int(self.cleaned_data['year']),
            date__month=int(self.cleaned_data['month'])
        ).first()
