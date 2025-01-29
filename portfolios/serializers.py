# portfolios/serializers.py
from rest_framework import serializers
from .models import Portfolio, Position
from fin_data_cl.serializers import SecuritySerializer

class PositionSerializer(serializers.ModelSerializer):
    security = SecuritySerializer(read_only=True)
    security_id = serializers.IntegerField(write_only=True)
    current_value = serializers.SerializerMethodField()

    class Meta:
        model = Position
        fields = [
            'id', 'security', 'security_id', 'shares',
            'average_price', 'current_value'
        ]

    def get_current_value(self, obj):
        return float(obj.get_current_value())

    def validate(self, data):
        if data.get('shares', 0) <= 0:
            raise serializers.ValidationError(
                {"shares": "Number of shares must be positive"}
            )
        if data.get('average_price', 0) <= 0:
            raise serializers.ValidationError(
                {"average_price": "Average price must be positive"}
            )
        return data

class PortfolioSerializer(serializers.ModelSerializer):
    positions = PositionSerializer(many=True, read_only=True)
    total_value = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = [
            'id', 'name', 'description', 'is_public',
            'positions', 'total_value', 'target_risk',
            'target_return', 'rebalancing_frequency',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_total_value(self, obj):
        return float(obj.get_total_value())