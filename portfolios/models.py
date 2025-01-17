from django.db import models
from fin_data_cl.models import BaseFinancialData, Security
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator


class Portfolio(BaseFinancialData):
    """
    Model to store portfolio configurations.
    Focuses on portfolio composition and analysis.
    """
    name = models.CharField(max_length=100, help_text="Portfolio name")
    description = models.TextField(null=True, blank=True, help_text="Portfolio description")
    session_key = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Session key for anonymous portfolios"
    )
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='portfolios',
        help_text="User who owns this portfolio (optional)"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this portfolio can be viewed by other users"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Portfolio"
        verbose_name_plural = "Portfolios"

    def __str__(self):
        return f"{self.name} ({self.created_at.date()})"

    def calculate_metrics(self, start_date=None, end_date=None):
        """Calculate basic portfolio metrics"""
        # To be implemented: returns, volatility, etc.
        pass


class PortfolioSecurity(models.Model):
    """
    Associates securities with portfolios and stores their current weights
    """
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='securities'
    )
    security = models.ForeignKey(
        Security,
        on_delete=models.CASCADE,
        related_name='portfolio_securities'
    )
    current_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        help_text="Current portfolio weight in percentage"
    )
    target_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ],
        null=True,
        blank=True,
        help_text="Target weight for rebalancing"
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="When this security was last updated"
    )

    class Meta:
        unique_together = ('portfolio', 'security')
        verbose_name = "Portfolio Security"
        verbose_name_plural = "Portfolio Securities"

    def __str__(self):
        return f"{self.portfolio.name} - {self.security.ticker}: {self.current_weight}%"


class OptimizationScenario(models.Model):
    """
    Model to store portfolio optimization scenarios.
    Can be based on existing portfolios or temporary security selections.
    """
    name = models.CharField(max_length=100, help_text="Scenario name")
    base_portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='optimization_scenarios',
        help_text="Original portfolio used for optimization"
    )
    session_key = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Session key for anonymous scenarios"
    )
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='optimization_scenarios'
    )
    optimization_type = models.CharField(
        max_length=20,
        choices=[
            ('MIN_VOL', 'Minimize Volatility'),
            ('MAX_PERF', 'Maximize Performance'),
            ('MAX_SHARPE', 'Maximize Sharpe Ratio'),
        ],
        default='MAX_SHARPE'
    )
    constraints = models.JSONField(
        default=dict,
        help_text="Optimization constraints in JSON format"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_run = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Optimization Scenario"
        verbose_name_plural = "Optimization Scenarios"

    def __str__(self):
        return f"{self.name} ({self.optimization_type})"


class OptimizedSecurity(models.Model):
    """
    Stores optimization results for each security
    """
    scenario = models.ForeignKey(
        OptimizationScenario,
        on_delete=models.CASCADE,
        related_name='optimized_securities'
    )
    security = models.ForeignKey(
        Security,
        on_delete=models.CASCADE,
        related_name='optimization_results'
    )
    optimized_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    original_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ('scenario', 'security')

    def __str__(self):
        return f"{self.scenario.name} - {self.security.ticker}: {self.optimized_weight}%"