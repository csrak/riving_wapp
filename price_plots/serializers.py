# serializers.py
from rest_framework import serializers
from fin_data_cl.models import Exchange, Security, PriceData, DividendData

class ExchangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exchange
        fields = ['code', 'name', 'timezone', 'suffix']


class SecuritySerializer(serializers.ModelSerializer):
    exchange_code = serializers.CharField(source='exchange.code')
    exchange_name = serializers.CharField(source='exchange.name')

    class Meta:
        model = Security
        fields = ['id', 'ticker', 'name', 'exchange_code', 'exchange_name', 'full_symbol']


class PriceDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceData
        fields = ['date', 'open_price', 'high_price', 'low_price',
                 'close_price', 'adj_close', 'volume']


class DividendDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = DividendData
        fields = ['date', 'amount', 'dividend_type']


class StockAnalysisDataSerializer(serializers.Serializer):
    dates = serializers.ListField(child=serializers.DateField())
    prices = serializers.ListField(child=serializers.DecimalField(max_digits=10, decimal_places=2))
    open_prices = serializers.ListField(child=serializers.DecimalField(max_digits=10, decimal_places=2))
    high_prices = serializers.ListField(child=serializers.DecimalField(max_digits=10, decimal_places=2))
    low_prices = serializers.ListField(child=serializers.DecimalField(max_digits=10, decimal_places=2))
    volumes = serializers.ListField(child=serializers.IntegerField())
    dividends = DividendDataSerializer(many=True)