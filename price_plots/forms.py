from django import forms

class StockRangeForm(forms.Form):
    RANGE_CHOICES = [
        ("1W", "1 Week"),
        ("1M", "1 Month"),
        ("3M", "3 Months"),
        ("6M", "6 Months"),
        ("1Y", "1 Year"),
        ("3Y", "3 Years"),
        ("5Y", "5 Years"),
        ("Max", "Max"),
    ]
    range = forms.ChoiceField(choices=RANGE_CHOICES, required=True, initial="6M", widget=forms.RadioSelect)
    security = forms.ChoiceField(required=True)

    def __init__(self, securities, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically populate the security choices
        self.fields['security'].choices = [(s.id, f"{s.ticker} - {s.name}") for s in securities]
