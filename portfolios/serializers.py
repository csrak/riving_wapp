# portfolios/serializers.py
from rest_framework import serializers
from .models import Portfolio, Position
from fin_data_cl.serializers import SecuritySerializer


class PositionSerializer(serializers.ModelSerializer):
    security = SecuritySerializer(read_only=True)
    current_value = serializers.SerializerMethodField()

    class Meta:
        model = Position
        fields = ['id', 'security', 'shares', 'average_price', 'current_value']

    def get_current_value(self, obj):
        return obj.get_current_value()


class PortfolioSerializer(serializers.ModelSerializer):
    positions = PositionSerializer(many=True, read_only=True)
    total_value = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = ['id', 'name', 'description', 'positions', 'total_value']

    def get_total_value(self, obj):
        return obj.get_total_value()