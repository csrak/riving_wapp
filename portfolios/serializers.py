# portfolios/serializers.py
from rest_framework import serializers
from .models import Portfolio, Position
from fin_data_cl.serializers import SecuritySerializer


# serializers.py improvements:
class PositionSerializer(serializers.ModelSerializer):
    security_id = serializers.IntegerField(write_only=True)
    security = SecuritySerializer(read_only=True)
    current_value = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )

    class Meta:
        model = Position
        fields = [
            'id', 'security_id', 'security', 'shares',
            'average_price', 'current_value', 'target_weight'
        ]
        read_only_fields = ['current_value']

    def validate(self, data):
        if data.get('shares', 0) <= 0:
            raise serializers.ValidationError(
                {"shares": "Number of shares must be positive"}
            )
        return data


class PortfolioSerializer(serializers.ModelSerializer):
    positions = PositionSerializer(many=True, read_only=True)
    total_value = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = ['id', 'name', 'description', 'is_public', 'positions', 'total_value',
                  'target_risk', 'target_return', 'rebalancing_frequency']
        read_only_fields = ['user']  # Ensure user can't be set via API

    def get_total_value(self, obj):
        return obj.get_total_value()