# serializers.py
from rest_framework import serializers
from fin_data_cl.models import (
    Security
)
from .models import (
    PortfolioSecurity, Portfolio, OptimizationScenario, OptimizedSecurity
)

from fin_data_cl.serializers import SecuritySerializer, BaseFinancialSerializer


class PortfolioSecuritySerializer(serializers.ModelSerializer):
    security = SecuritySerializer(read_only=True)
    security_id = serializers.PrimaryKeyRelatedField(
        queryset=Security.objects.all(),
        source='security',
        write_only=True
    )

    class Meta:
        model = PortfolioSecurity
        fields = [
            'id', 'security', 'security_id', 'current_weight',
            'target_weight', 'last_updated'
        ]
        read_only_fields = ['last_updated']


class PortfolioSerializer(BaseFinancialSerializer):
    securities = PortfolioSecuritySerializer(many=True, read_only=True)
    security_ids = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Security.objects.all()),
        write_only=True,
        required=False
    )

    class Meta(BaseFinancialSerializer.Meta):
        model = Portfolio
        fields = BaseFinancialSerializer.Meta.fields + [
            'name', 'description', 'securities', 'security_ids',
            'is_public', 'created_at', 'updated_at'
        ]
        read_only_fields = ['session_key', 'user']

    def create(self, validated_data):
        security_ids = validated_data.pop('security_ids', [])
        portfolio = Portfolio.objects.create(**validated_data)

        # Create portfolio securities with equal weights initially
        weight = 100.0 / len(security_ids) if security_ids else 0
        for security in security_ids:
            PortfolioSecurity.objects.create(
                portfolio=portfolio,
                security=security,
                current_weight=weight
            )

        return portfolio


class OptimizedSecuritySerializer(serializers.ModelSerializer):
    security = SecuritySerializer(read_only=True)

    class Meta:
        model = OptimizedSecurity
        fields = [
            'security', 'optimized_weight', 'original_weight'
        ]


class OptimizationScenarioSerializer(BaseFinancialSerializer):
    base_portfolio = PortfolioSerializer(read_only=True)
    base_portfolio_id = serializers.PrimaryKeyRelatedField(
        queryset=Portfolio.objects.all(),
        source='base_portfolio',
        write_only=True,
        required=False
    )
    optimized_securities = OptimizedSecuritySerializer(many=True, read_only=True)

    class Meta(BaseFinancialSerializer.Meta):
        model = OptimizationScenario
        fields = BaseFinancialSerializer.Meta.fields + [
            'name', 'base_portfolio', 'base_portfolio_id',
            'optimization_type', 'constraints', 'created_at',
            'last_run', 'optimized_securities'
        ]
        read_only_fields = ['session_key', 'user', 'last_run']