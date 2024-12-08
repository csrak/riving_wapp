# serializers.py
from rest_framework import serializers
from .models import (
    Exchange, Security, FinancialData, PriceData,
    FinancialRatio, FinancialReport, RiskComparison,
    DividendData
)
from fin_data_cl.templatetags.text_filters import format_subsection


class BaseFinancialSerializer(serializers.ModelSerializer):
    """
    Base serializer that provides common functionality for all financial data.
    This ensures consistent handling of dates and common fields across all serializers.
    """
    # Add formatted date field that will be consistent across all serializers
    formatted_date = serializers.SerializerMethodField()

    def get_formatted_date(self, obj):
        """Returns date in a consistent format for all financial data"""
        return obj.date.strftime('%Y-%m-%d') if obj.date else None

    class Meta:
        # This makes it an abstract base class
        abstract = True
        # Fields that should be included in all financial serializers
        fields = ['id', 'date', 'formatted_date', 'created_at', 'updated_at']


class ExchangeSerializer(serializers.ModelSerializer):
    """
    Serializer for Exchange model - needed for nested relationships
    """

    class Meta:
        model = Exchange
        fields = ['id', 'code', 'name', 'timezone', 'suffix']


class SecuritySerializer(serializers.ModelSerializer):
    """
    Enhanced Security serializer with proper nesting and computed fields
    """
    exchange = ExchangeSerializer(read_only=True)
    full_symbol = serializers.SerializerMethodField()

    class Meta:
        model = Security
        fields = [
            'id', 'ticker', 'exchange', 'name',
            'is_active', 'last_updated', 'full_symbol'
        ]

    def get_full_symbol(self, obj):
        return f"{obj.ticker}.{obj.exchange.suffix}"


class PriceDataSerializer(BaseFinancialSerializer):
    """
    Enhanced Price Data serializer with support for time-range queries
    """
    security = SecuritySerializer(read_only=True)
    price_change = serializers.SerializerMethodField()
    price_change_percentage = serializers.SerializerMethodField()

    class Meta(BaseFinancialSerializer.Meta):
        model = PriceData
        fields = BaseFinancialSerializer.Meta.fields + [
            'security', 'price', 'market_cap', 'open_price',
            'high_price', 'low_price', 'close_price', 'adj_close',
            'volume', 'price_change', 'price_change_percentage'
        ]

    def get_price_change(self, obj):
        """Calculate absolute price change"""
        if obj.close_price and obj.open_price:
            return float(obj.close_price - obj.open_price)
        return None

    def get_price_change_percentage(self, obj):
        """Calculate percentage price change"""
        if obj.open_price and obj.open_price != 0:
            return float((obj.close_price - obj.open_price) / obj.open_price * 100)
        return None


class FinancialDataSerializer(BaseFinancialSerializer):
    """
    Enhanced Financial Data serializer with computed ratios
    """
    security = SecuritySerializer(read_only=True)
    profit_margin = serializers.SerializerMethodField()

    class Meta(BaseFinancialSerializer.Meta):
        model = FinancialData
        fields = BaseFinancialSerializer.Meta.fields + [
            'security', 'revenue', 'net_profit', 'operating_profit',
            'eps', 'operating_eps', 'cash', 'assets', 'liabilities',
            'equity', 'profit_margin'
        ]

    def get_profit_margin(self, obj):
        """Calculate profit margin as percentage"""
        if obj.revenue and obj.revenue != 0:
            return float(obj.net_profit / obj.revenue * 100)
        return None


class FinancialRatioSerializer(BaseFinancialSerializer):
    """
    Serializer for financial ratios. Handles both positive and negative ratios
    as they can represent legitimate business situations.
    """
    security = SecuritySerializer(read_only=True)

    class Meta(BaseFinancialSerializer.Meta):
        model = FinancialRatio
        fields = BaseFinancialSerializer.Meta.fields + [
            'security', 'pe_ratio', 'pb_ratio', 'ps_ratio',
            'peg_ratio', 'ev_ebitda', 'gross_profit_margin',
            'operating_profit_margin', 'net_profit_margin',
            'return_on_assets', 'return_on_equity', 'debt_to_equity',
            'current_ratio', 'quick_ratio', 'dividend_yield', 'price','before_dividend_yield',
        ]

    def to_representation(self, instance):
        """
        Customize the output representation to handle special cases
        like infinite ratios or undefined values
        """
        data = super().to_representation(instance)

        # Handle cases where ratios might be undefined
        # For example, if equity is zero, debt_to_equity would be undefined
        # if instance.debt_to_equity is not None and instance.equity == 0:
        #     data['debt_to_equity'] = None

        return data


class RiskComparisonSerializer(BaseFinancialSerializer):
    """
    Enhanced Risk Comparison serializer with proper JSON field handling
    """
    security = SecuritySerializer(read_only=True)

    class Meta(BaseFinancialSerializer.Meta):
        model = RiskComparison
        fields = BaseFinancialSerializer.Meta.fields + [
            'security', 'new_risks', 'old_risks', 'modified_risks'
        ]

    def to_representation(self, instance):
        """Ensure JSON fields are properly formatted"""
        data = super().to_representation(instance)
        # Ensure JSON fields are lists even if null in database
        for field in ['new_risks', 'old_risks', 'modified_risks']:
            if data[field] is None:
                data[field] = []
        return data


class FinancialReportSerializer(BaseFinancialSerializer):
    """
    Enhanced Financial Report serializer with JSON field handling
    """
    security = SecuritySerializer(read_only=True)

    class Meta(BaseFinancialSerializer.Meta):
        model = FinancialReport
        fields = BaseFinancialSerializer.Meta.fields + [
            'security', 'business_overview', 'risks',
            'metrics', 'historical_changes', 'future_outlook'
        ]

    def get_business_overview(self, obj):
        return format_subsection(obj.business_overview) if obj.business_overview else ""

class DividendDataSerializer(BaseFinancialSerializer):
    """
    Enhanced Dividend Data serializer with time range support
    """
    security = SecuritySerializer(read_only=True)
    annualized_yield = serializers.SerializerMethodField()

    class Meta(BaseFinancialSerializer.Meta):
        model = DividendData
        fields = BaseFinancialSerializer.Meta.fields + [
            'security', 'amount', 'dividend_type', 'annualized_yield'
        ]

    def get_annualized_yield(self, obj):
        """Calculate annualized yield based on latest price"""
        try:
            latest_price = PriceData.objects.filter(
                security=obj.security
            ).latest('date').close_price

            if latest_price and latest_price != 0:
                return float(obj.amount / latest_price * 100)
        except PriceData.DoesNotExist:
            pass
        return None