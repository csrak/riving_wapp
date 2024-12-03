# views/stock_analysis.py
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta

from fin_data_cl.models import Exchange, Security, PriceData, DividendData
from .serializers import (
    ExchangeSerializer,
    SecuritySerializer,
    PriceDataSerializer,
    StockAnalysisDataSerializer
)


@method_decorator(ensure_csrf_cookie, name='dispatch')
class StockAnalysisView(TemplateView):
    """Main view for stock analysis page"""
    template_name = 'stock_chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['exchanges'] = Exchange.objects.all()
        return context


class ExchangeViewSet(ReadOnlyModelViewSet):
    """API endpoint for exchanges"""
    queryset = Exchange.objects.all()
    serializer_class = ExchangeSerializer


from django.views.generic import TemplateView
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class StockAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for stock analysis data"""
    queryset = Security.objects.filter(is_active=True)
    serializer_class = SecuritySerializer

    @action(detail=True, methods=['get'])
    def price_data(self, request, pk=None):
        """Get price data for a specific security"""
        try:
            # Get security
            security = self.get_object()

            # Get date range
            timerange = request.query_params.get('timerange', '1y')
            end_date = timezone.now().date()

            # Define timerange mappings
            timerange_mapping = {
                '1w': timedelta(days=7),
                '1m': timedelta(days=30),
                '6m': timedelta(days=180),
                '1y': timedelta(days=365),
                '3y': timedelta(days=1095),
                '5y': timedelta(days=1825),
                'max': timedelta(days=36500)
            }

            start_date = end_date - timerange_mapping.get(timerange, timerange_mapping['1y'])

            # Get price data
            price_data = PriceData.objects.filter(
                security=security,
                date__range=[start_date, end_date]
            ).order_by('date')

            # Get dividend data
            dividend_data = DividendData.objects.filter(
                security=security,
                date__range=[start_date, end_date]
            ).order_by('date')

            # Prepare response data
            response_data = {
                'dates': [p.date.isoformat() for p in price_data],
                'prices': [float(p.close_price) if p.close_price else None for p in price_data],
                'open_prices': [float(p.open_price) if p.open_price else None for p in price_data],
                'high_prices': [float(p.high_price) if p.high_price else None for p in price_data],
                'low_prices': [float(p.low_price) if p.low_price else None for p in price_data],
                'volumes': [p.volume if p.volume else 0 for p in price_data],
                'dividends': [{
                    'date': d.date.isoformat(),
                    'amount': float(d.amount),
                    'type': d.dividend_type
                } for d in dividend_data]
            }

            return Response(response_data)

        except Security.DoesNotExist:
            logger.error(f"Security with ID {pk} not found")
            return Response({"error": "Security not found"}, status=404)
        except Exception as e:
            logger.exception(f"Error processing price data for security {pk}: {str(e)}")
            return Response(
                {"error": "An error occurred while processing the request"},
                status=500
            )


class SecurityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SecuritySerializer

    def get_queryset(self):
        queryset = Security.objects.filter(is_active=True)
        exchange_code = self.request.query_params.get('exchange', None)

        if exchange_code:
            queryset = queryset.filter(exchange__code=exchange_code)

        return queryset.select_related('exchange')