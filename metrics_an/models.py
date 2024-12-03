from django.db import models


class MetricPlotterSettings(models.Model):
    """Store user preferences for metric plotting"""
    exchange = models.CharField(max_length=50)
    stock = models.CharField(max_length=50)
    selected_metrics = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']


