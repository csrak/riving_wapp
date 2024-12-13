# viewsets.py
from .models import FinancialReport, FinancialRatio, RiskComparison, DividendData, PriceData, FinancialData, Security, \
    Exchange
from .serializers import FinancialReportSerializer, FinancialRatioSerializer, RiskComparisonSerializer, \
    DividendDataSerializer, PriceDataSerializer, FinancialDataSerializer
import logging
logger = logging.getLogger(__name__)
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models.functions import ExtractYear, ExtractMonth
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Max, Q, DecimalField
import calendar


class BaseFinancialViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Base ViewSet that all financial ViewSets inherit from.
    Provides common functionality for data access and filtering.
    """
    model = None
    serializer_class = None
    # Define which features this viewset supports
    supports_time_range = False  # For fetching data within date ranges
    supports_latest = False  # For fetching latest data points
    supports_screening = False  # For complex filtering/screening

    def get_queryset(self):
        """
        Core queryset method that all financial ViewSets use.
        Implements smart relationship loading and basic filtering.
        """
        if self.model is None:
            raise NotImplementedError("ViewSet must define 'model' attribute")

        # Start with optimized queryset including common relationships
        queryset = self.model.objects.select_related(
            'security',
            'security__exchange'
        ).order_by('-date')

        # Handle nested routes (e.g., /securities/{id}/financial-data/)
        security_pk = self.kwargs.get('security_pk')
        if security_pk:
            queryset = queryset.filter(security_id=security_pk)

        # Apply filters from URL parameters
        security = self.request.query_params.get('security')
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')

        if security:
            queryset = queryset.filter(security_id=security)
        if year:
            queryset = queryset.filter(date__year=year)
        if month:
            queryset = queryset.filter(date__month=month)

        return queryset

    def get_latest_queryset(self):
        """
        Get the latest data points for each security, with a 1-day tolerance
        to handle end-of-day updates.
        """
        queryset = self.get_queryset()

        if not queryset.exists():
            return queryset.none()

        # Find the absolute latest date in the dataset
        latest_possible_date = queryset.order_by('-date').values('date').first()['date']

        # Allow for data from either the latest date or one day before
        acceptable_dates = [
            latest_possible_date,
            latest_possible_date - timedelta(days=1)
        ]

        # Get securities with their latest dates
        latest_dates = queryset.values('security').annotate(
            max_date=Max('date')
        )

        # Build query for securities with data on either acceptable date
        date_filters = Q()
        for item in latest_dates:
            if item['max_date'] in acceptable_dates:
                date_filters |= Q(
                    security=item['security'],
                    date=item['max_date']
                )

        return queryset.filter(date_filters)
    @action(detail=False)
    def available_exchanges(self, request):
        """
        Get exchanges that have data available for this model.
        """
        try:
            print("Looking for exchanges...")

            # Get the correct related name by adding _data suffix
            model_name = f"{self.model._meta.model_name}_data"
            print(f"Looking for related name: {model_name}")

            # Use the correct related name in our query
            exchanges = Exchange.objects.filter(
                security__in=Security.objects.filter(
                    **{f"{model_name}__isnull": False}
                )
            ).distinct().order_by('name')

            print(f"Found {exchanges.count()} exchanges")

            response_data = {
                'exchanges': [
                    {
                        'id': exchange.id,
                        'name': exchange.name,
                        'code': exchange.code
                    }
                    for exchange in exchanges
                ]
            }

            return Response(response_data)

        except Exception as e:
            print(f"Error in available_exchanges: {str(e)}")
            return Response({'error': str(e)}, status=500)

    @action(detail=False)
    def securities_by_exchange(self, request):
        """Get securities with data for an exchange."""
        exchange_id = request.query_params.get('exchange_id')
        if not exchange_id:
            return Response({"error": "exchange_id is required"}, status=400)

        try:
            # Get the correct related name by adding _data suffix
            model_name = f"{self.model._meta.model_name}_data"

            securities = Security.objects.filter(
                exchange_id=exchange_id,
                **{f"{model_name}__isnull": False}
            ).distinct().order_by('ticker')

            return Response({
                'securities': [
                    {
                        'id': security.id,
                        'ticker': security.ticker,
                        'name': security.name
                    }
                    for security in securities
                ]
            })
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    @action(detail=False)
    def date_range(self, request):
        """
        Get data within a specified date range.
        Only available if supports_time_range is True.
        """
        if not self.supports_time_range:
            return Response(
                {"error": "Time range queries not supported"},
                status=400
            )

        security_id = request.query_params.get('security_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not all([security_id, start_date, end_date]):
            return Response(
                {"error": "security_id, start_date, and end_date are required"},
                status=400
            )

        queryset = self.get_queryset().filter(
            security_id=security_id,
            date__range=[start_date, end_date]
        ).order_by('date')

        return Response(self.serializer_class(queryset, many=True).data)

    @action(detail=False)
    def latest(self, request):
        """
        Get the latest data points.
        Only available if supports_latest is True.
        """
        if not self.supports_latest:
            return Response(
                {"error": "Latest data queries not supported"},
                status=400
            )

        queryset = self.get_latest_queryset()
        return Response(self.serializer_class(queryset, many=True).data)

    @action(detail=False)
    def screen(self, request):
        """
        Screen/filter data based on multiple criteria.
        Modified to work with both SQLite and PostgreSQL.
        """
        if not self.supports_screening:
            return Response(
                {"error": "Screening not supported"},
                status=400
            )

        filters = request.query_params.getlist('filters[]', [])
        exchange_id = request.query_params.get('exchange_id')

        queryset = self.get_queryset()

        if exchange_id:
            queryset = queryset.filter(security__exchange_id=exchange_id)

        for filter_string in filters:
            try:
                field, operator, value = filter_string.split(':')
                if operator in ['gt', 'lt', 'gte', 'lte']:
                    queryset = queryset.filter(
                        **{f"{field}__{operator}": float(value)}
                    )
            except (ValueError, TypeError) as e:
                print(f"Filter error {filter_string}: {e}")
                continue

        # Instead of using DISTINCT ON, we'll use a subquery to get the latest date
        # for each security, then join back to get the full records
        latest_dates = queryset.values('security_id').annotate(
            max_date=Max('date')
        )

        queryset = queryset.filter(
            date__in=[item['max_date'] for item in latest_dates],
            security_id__in=[item['security_id'] for item in latest_dates]
        )

        return Response(self.serializer_class(queryset, many=True).data)

    @action(detail=False)
    def available_dates(self, request) -> Response:
        """
        Get available years and months for a security.
        If year is provided, returns months for that year.
        """
        security_id = request.query_params.get('security_id')
        if not security_id:
            return Response({"error": "security_id is required"}, status=400)

        queryset = self.get_queryset().filter(security_id=security_id)
        year = request.query_params.get('year')

        if year:
            months = queryset.filter(
                date__year=year
            ).annotate(
                month_number=ExtractMonth('date')
            ).values('month_number').distinct().order_by('month_number')

            return Response({
                'months': [
                    {
                        'number': month['month_number'],
                        'name': calendar.month_name[month['month_number']]
                    }
                    for month in months
                ]
            })

        years = queryset.annotate(
            year=ExtractYear('date')
        ).values('year').distinct().order_by('year')

        return Response({
            'years': [year['year'] for year in years]
        })

# Now we can create specific ViewSets with minimal code
class FinancialRatioViewSet(BaseFinancialViewSet):
    """ViewSet for financial ratios with screening capability."""
    model = FinancialRatio
    serializer_class = FinancialRatioSerializer
    supports_latest = True
    supports_screening = True
    queryset = FinancialRatio.objects.all()  # Required by DRF


class PriceDataViewSet(BaseFinancialViewSet):
    model = PriceData
    serializer_class = PriceDataSerializer
    supports_time_range = True
    supports_latest = True
    queryset = PriceData.objects.all()

    @action(detail=False, methods=['get'])
    def candlestick_data(self, request):
        """Get historical price data for candlestick plotting."""
        ticker = request.query_params.get('ticker')
        timeframe = request.query_params.get('timeframe', '1Y')

        try:
            security = Security.objects.get(ticker=ticker)
            queryset = PriceData.objects.filter(security=security)

            # Print the first few records to see what we're working with
            print(f"First few records: {queryset.values()[:3]}")  # Debug print 2

            latest_date = queryset.order_by('-date').values('date').first()
            print(f"Latest date: {latest_date}")

            # Get the latest available date using the same logic as get_latest_queryset
            latest_possible_date = queryset.order_by('-date').values('date').first()['date']
            print(f"Latest possible date: {latest_possible_date}")
            # Define acceptable dates (today or yesterday)
            acceptable_dates = [
                latest_possible_date,
                latest_possible_date - timedelta(days=1)
            ]

            # Get the actual latest date with data
            latest_date = latest_possible_date

            # Calculate the start date based on timeframe
            if timeframe == '1W':
                start_date = latest_date - timedelta(days=7)
            elif timeframe == '1M':
                start_date = latest_date - timedelta(days=30)
            elif timeframe == '6M':
                start_date = latest_date - timedelta(days=180)
            elif timeframe == '1Y':
                start_date = latest_date - timedelta(days=365)
            elif timeframe == '5Y':
                start_date = latest_date - timedelta(days=1825)
            else:  # 'Max'
                start_date = None

            # Filter data
            if start_date:
                queryset = queryset.filter(date__gte=start_date)

            queryset = queryset.order_by('date')

            if not queryset.exists():
                return Response({
                    'error': f'No data available for {ticker} in the selected timeframe'
                }, status=404)

            # Process data with explicit type conversion and None handling
            data = []
            for record in queryset:
                try:
                    data_point = {
                        'date': record.date.strftime('%Y-%m-%d'),
                        'open_price': float(record.open_price if record.open_price is not None else 0),
                        'high_price': float(record.high_price if record.high_price is not None else 0),
                        'low_price': float(record.low_price if record.low_price is not None else 0),
                        'close_price': float(record.close_price if record.close_price is not None else 0),
                        'volume': int(record.volume if record.volume is not None else 0)
                    }
                    data.append(data_point)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Error processing record for {ticker} on {record.date}: {e}")
                    continue

            return Response({
                'data': data,
                'ticker': ticker,
                'timeframe': timeframe,
                'latest_date': latest_date.strftime('%Y-%m-%d')
            })

        except Security.DoesNotExist:
            return Response({'error': f'Security {ticker} not found'}, status=404)
        except Exception as e:
            logger.error(f"Error in candlestick_data: {str(e)}")
            return Response({'error': str(e)}, status=500)

class DividendDataViewSet(BaseFinancialViewSet):
    """ViewSet for dividend data with time range support."""
    model = DividendData
    serializer_class = DividendDataSerializer
    supports_time_range = True
    queryset = DividendData.objects.all()

    @action(detail=False)
    def annual_yield(self, request):
        """Custom method specific to dividend data."""
        security_id = request.query_params.get('security_id')
        if not security_id:
            return Response({'error': 'security_id required'}, status=400)

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=365)

        annual_dividends = self.get_queryset().filter(
            security_id=security_id,
            date__range=[start_date, end_date]
        ).aggregate(total=Sum('amount'))['total'] or 0

        return Response({'annual_yield': annual_dividends})


class FinancialDataViewSet(BaseFinancialViewSet):
    """ViewSet for financial statement data with metric plotting capabilities."""
    model = FinancialData
    serializer_class = FinancialDataSerializer
    supports_latest = True
    supports_time_range = True  # Enable time range support for plotting

    @action(detail=False, methods=['GET'])
    def metrics(self, request):
        """Return available metrics for plotting."""
        metrics = [
            {'field': field.name, 'display_name': field.verbose_name or field.name.replace('_', ' ').title()}
            for field in self.model._meta.fields
            if isinstance(field, DecimalField)
        ]
        return Response(metrics)

    def list(self, request, *args, **kwargs):
        """Enhanced list method to support metric plotting."""
        metrics = request.query_params.get('metrics', '').split(',')
        if not metrics or '' in metrics:
            return super().list(request, *args, **kwargs)

        # Use the base class queryset with our existing filters
        queryset = self.get_queryset()

        # Optimize query by selecting only needed fields
        fields_to_select = ['date'] + metrics
        queryset = queryset.values(*fields_to_select)

        # Transform data for plotting
        dates = []
        metric_data = {metric: [] for metric in metrics}

        for entry in queryset:
            dates.append(entry['date'])
            for metric in metrics:
                metric_data[metric].append(float(entry[metric]) if entry[metric] is not None else None)

        return Response({
            'dates': dates,
            **metric_data
        })


class FinancialReportViewSet(BaseFinancialViewSet):
    """ViewSet for financial reports."""
    model = FinancialReport
    serializer_class = FinancialReportSerializer
    queryset = FinancialReport.objects.all().order_by('-date')


class RiskComparisonViewSet(BaseFinancialViewSet):
    """ViewSet for risk comparisons."""
    model = RiskComparison
    serializer_class = RiskComparisonSerializer
    queryset = RiskComparison.objects.all().order_by('-date')

    # def get_queryset(self):
    #     queryset = super().get_queryset()
    #
    #     # Debug print the actual results
    #     results = list(queryset)
    #     print(f"Found {len(results)} results")
    #     if results:
    #         print("First result data:", {
    #             'id': results[0].id,
    #             'date': results[0].date,
    #             'new_risks': results[0].new_risks,
    #             'modified_risks': results[0].modified_risks,
    #             'old_risks': results[0].old_risks
    #         })
    #
    #     return queryset
