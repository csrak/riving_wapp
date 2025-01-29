# portfolios/models.py
from django.db import models
from django.contrib.auth.models import User
from fin_data_cl.models import Security
from decimal import Decimal


class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Analysis fields
    target_risk = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )
    target_return = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )
    rebalancing_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
        ],
        default='monthly'
    )

    def get_total_value(self):
        """Calculate total portfolio value"""
        return sum(position.get_current_value() for position in self.positions.all())

    def get_positions_data(self):
        """Get formatted positions data"""
        return [{
            'id': position.id,
            'security': {
                'id': position.security.id,
                'ticker': position.security.ticker,
                'name': position.security.name
            },
            'shares': float(position.shares),
            'average_price': float(position.average_price),
            'current_value': float(position.get_current_value())
        } for position in self.positions.all()]


class Position(models.Model):
    portfolio = models.ForeignKey(
        Portfolio,
        related_name='positions',
        on_delete=models.CASCADE
    )
    security = models.ForeignKey(Security, on_delete=models.CASCADE)
    shares = models.DecimalField(max_digits=15, decimal_places=2)
    average_price = models.DecimalField(max_digits=15, decimal_places=2)
    date_added = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    def get_current_value(self):
        """Calculate current position value"""
        return self.shares * self.security.get_latest_price()


class PortfolioSnapshot(models.Model):
    """Tracks portfolio performance over time"""
    portfolio = models.ForeignKey(Portfolio, related_name='snapshots', on_delete=models.CASCADE)
    date = models.DateField()
    total_value = models.DecimalField(max_digits=20, decimal_places=2)
    cash_position = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    performance_metrics = models.JSONField(default=dict)
    positions = models.JSONField(default=dict)

    class Meta:
        unique_together = ('portfolio', 'date')


class PortfolioRebalanceHistory(models.Model):
    """Tracks portfolio rebalancing events"""
    portfolio = models.ForeignKey(Portfolio, related_name='rebalance_history', on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    old_weights = models.JSONField()
    new_weights = models.JSONField()
    rebalance_type = models.CharField(max_length=50)
    notes = models.TextField(blank=True)