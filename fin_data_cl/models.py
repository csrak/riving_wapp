from django.db import models
from django.db.models import Manager
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from finriv.utils.exchanges import ExchangeRegistry
from django.utils import timezone
from django.db.models import Q


class SecurityManager(Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('exchange')


class PriceDataManager(Manager):
    def get_data_in_range(self, security, start_date, end_date):
        return self.filter(
            security=security,
            date__range=[start_date, end_date]
        ).order_by('date')

    def valid(self):
        """
        Return only valid records where price fields are numeric and non-null.
        """
        return self.filter(
            ~Q(open_price=None) & ~Q(high_price=None) & ~Q(low_price=None) & ~Q(close_price=None),
        ).extra(where=[
            "CAST(open_price AS REAL) IS NOT NULL",
            "CAST(high_price AS REAL) IS NOT NULL",
            "CAST(low_price AS REAL) IS NOT NULL",
            "CAST(close_price AS REAL) IS NOT NULL"
        ])


class Exchange(models.Model):
    """
    Database representation of supported exchanges.
    This model mirrors the Exchange configuration from utils/exchanges.py but persists the data.
    """
    code = models.CharField(max_length=10, unique=True, help_text="Exchange code (e.g., 'NYSE')")
    name = models.CharField(max_length=100, help_text="Full exchange name")
    timezone = models.CharField(max_length=50, help_text="Timezone (e.g., 'America/New_York')")
    suffix = models.CharField(max_length=10, help_text="Symbol suffix (e.g., '.NYQ')")
    trading_start = models.TimeField(help_text="Trading session start time")
    trading_end = models.TimeField(help_text="Trading session end time")
    break_start = models.TimeField(null=True, blank=True, help_text="Break period start (optional)")
    break_end = models.TimeField(null=True, blank=True, help_text="Break period end (optional)")

    class Meta:
        verbose_name = "Exchange"
        verbose_name_plural = "Exchanges"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def clean(self):
        """Validate break times if they exist"""
        if bool(self.break_start) != bool(self.break_end):
            raise ValidationError("Both break start and end must be set if one is provided")
        if self.break_start and self.break_end:
            if not (self.trading_start < self.break_start < self.break_end < self.trading_end):
                raise ValidationError("Break period must be within trading hours")

    @classmethod
    def sync_from_registry(cls):
        """
        Synchronize database exchanges with the configuration in exchanges.py
        Returns tuple of (created_count, updated_count)
        """
        registry = ExchangeRegistry()
        created, updated = 0, 0

        for exchange_config in registry.get_all_exchanges():
            exchange, was_created = cls.objects.update_or_create(
                code=exchange_config.code,
                defaults={
                    'name': exchange_config.name,
                    'timezone': exchange_config.timezone,
                    'suffix': exchange_config.suffix,
                    'trading_start': exchange_config.trading_hours.trading_start,
                    'trading_end': exchange_config.trading_hours.trading_end,
                    'break_start': exchange_config.trading_hours.break_start,
                    'break_end': exchange_config.trading_hours.break_end,
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return created, updated


class Security(models.Model):
    """
    Base model for tradable securities across all exchanges
    """
    ticker = models.CharField(max_length=20, help_text="Security symbol without suffix")
    exchange = models.ForeignKey(
        Exchange,
        on_delete=models.CASCADE,
        help_text="Exchange where the security is traded"
    )
    name = models.CharField(max_length=200, help_text="Security name/description")
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this security is currently traded"
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('ticker', 'exchange')
        verbose_name = "Security"
        verbose_name_plural = "Securities"

    def __str__(self):
        return f"{self.ticker}.{self.exchange.suffix}"

    @property
    def full_symbol(self):
        """Return the complete symbol including exchange suffix"""
        return f"{self.ticker}.{self.exchange.suffix}"

    objects = SecurityManager()

    def get_analysis_data(self, start_date, end_date):
        """Get all analysis data for a security in date range"""
        price_data = self.pricedata_set.filter(
            date__range=[start_date, end_date]
        ).order_by('date')

        dividend_data = self.dividenddata_set.filter(
            date__range=[start_date, end_date]
        ).order_by('date')

        return {
            'dates': [p.date for p in price_data],
            'prices': [p.close_price for p in price_data],
            'open_prices': [p.open_price for p in price_data],
            'high_prices': [p.high_price for p in price_data],
            'low_prices': [p.low_price for p in price_data],
            'volumes': [p.volume for p in price_data],
            'dividends': list(dividend_data)
        }


class BaseFinancialData(models.Model):
    """
    Abstract base model for all financial data
    Using explicit timestamp fields instead of auto_now for better control
    """
    security = models.ForeignKey(
        'fin_data_cl.Security',  # Using string to avoid circular imports
        on_delete=models.CASCADE,
        related_name='%(class)s_data',  # This creates unique related names for each child class
        null=True,
        blank=True
    )
    date = models.DateField(
        help_text="Date this data point represents",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        default=timezone.now,  # Set default to timezone.now for creation timestamp
        help_text="When this record was first created",
        editable=True  # Making it editable gives us more control
    )
    updated_at = models.DateTimeField(
        default=timezone.now,  # Set default to timezone.now for creation timestamp
        help_text="When this record was last updated",
        editable=True
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Set timestamps explicitly if not provided
        if not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    @classmethod
    def get_last_update_date(cls, security):
        """Get the most recent data date for a security"""
        latest = cls.objects.filter(security=security).order_by('-date').first()
        return latest.date if latest else None

    @classmethod
    def get_start_date(cls, security):
        """
        Determine the start date for data fetching
        Returns either the day after the last update or 10 years ago
        """
        last_date = cls.get_last_update_date(security)
        if last_date:
            return last_date + timezone.timedelta(days=1)

        # If no data exists, start from 10 years ago
        return timezone.now().date() - timezone.timedelta(days=3650)  # 10 years


class RiskComparison(BaseFinancialData):
    new_risks = models.JSONField(blank=True, null=True)
    old_risks = models.JSONField(blank=True, null=True)
    modified_risks = models.JSONField(blank=True, null=True)


class FinancialReport(BaseFinancialData):
    business_overview = models.TextField()
    risks = models.JSONField()
    metrics = models.JSONField()
    historical_changes = models.JSONField()
    future_outlook = models.JSONField()
class FinancialData(BaseFinancialData):
    revenue = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    net_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    operating_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    non_controlling_profit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    eps = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    operating_eps = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    interest_revenue = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash_from_sales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash_from_yield = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash_from_rent = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash_to_payments = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash_to_other_payments = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    speculation_cash = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    current_payables = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cost_of_sales = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    ebit = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    depreciation = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    interest = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    current_assets = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    liabilities = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    marketable_securities = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    current_other_assets = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    provisions_for_employees = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    non_current_assets = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    goodwill = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    intangible_assets = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    assets = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    current_liabilities = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    equity = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    shares = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    inventories = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    shares_authorized = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    net_operating_cashflows = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    net_investing_cashflows = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    net_financing_cashflows = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    payment_for_supplies = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    payment_to_employees = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    dividends_paid = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    forex = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    trade_receivables = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    prepayments = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash_on_hands = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash_on_banks = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    cash_short_investment = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    employee_benefits = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)


class PriceData(BaseFinancialData):
    price = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    market_cap = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)  # New field for Market Cap
    open_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    high_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    low_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    close_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    adj_close = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    volume = models.BigIntegerField(null=True, blank=True)

    objects = PriceDataManager()


class FinancialRatio(BaseFinancialData):
    pe_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Price-to-Earnings
    pb_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Price-to-Book
    ps_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Price-to-Sales
    peg_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Price-to-Earnings Growth
    ev_ebitda = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # EV/EBITDA
    ev_sales = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # EV/Sales
    gross_profit_margin = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Gross Profit Margin
    operating_profit_margin = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Operating Profit Margin
    net_profit_margin = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Net Profit Margin
    return_on_assets = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Return on Assets
    return_on_equity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Return on Equity
    return_on_investment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Return on Investment
    debt_to_equity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Debt-to-Equity
    current_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Current Ratio
    quick_ratio = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Quick Ratio
    dividend_yield = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Dividend Yield this year
    before_dividend_yield = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Dividend Yield previous year
    price = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True) #Price used to calculate it

class DividendData(BaseFinancialData):
    """
    Comprehensive model to store detailed dividend history
    with methods for aggregation and summary retrieval
    """
    #ticker = models.CharField(max_length=10, db_index=True)
    #date = models.DateField(db_index=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    dividend_type = models.IntegerField(choices=[
        (1, 'Type 1'),
        (2, 'Type 2'),
        (3, 'Type 3')
    ])
