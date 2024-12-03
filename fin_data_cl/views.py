
from .models import FinancialData, FinancialRatio
from django.db.models import Q, Subquery, OuterRef
from .utils.search_view import generalized_search_view
from .forms import FinancialReportSearchForm, FinancialRisksSearchForm
from django.http import JsonResponse
from django.shortcuts import render
from django.core.cache import cache
from django.db.models import Max
from datetime import datetime, timedelta
from fin_data_cl.models import PriceData, Security
from django.db.models import F, ExpressionWrapper, FloatField
from django.db.models.functions import Cast
from django.core.serializers.json import DjangoJSONEncoder
import json
from .models import FinancialReport, RiskComparison


def get_securities_for_exchange(request, exchange_id):
    """Get securities for an exchange, checking if they have any associated data."""
    model = RiskComparison if 'risks' in request.path else FinancialReport

    securities = Security.objects.filter(
        exchange_id=exchange_id,
        is_active=True
    )

    return JsonResponse([
        {"id": security.id, "name": security.name}
        for security in securities
    ], safe=False)


# def get_years_for_security(request, security_id):
#     """Get available years for a security, handling both reports and risks."""
#     model = RiskComparison if 'risks' in request.path else FinancialReport
#
#     dates = model.objects.filter(
#         security_id=security_id
#     ).dates('date', 'month', order='DESC')
#
#     years = sorted(set(date.year for date in dates), reverse=True)
#     return JsonResponse({"years": years})
def get_years_for_security(request, security_id):
    """Get available years for a security, handling both reports and risks."""
    model = RiskComparison if 'risks' in request.path else FinancialReport

    print(f"Using model: {model.__name__}")  # Debug print

    dates = model.objects.filter(
        security_id=security_id
    ).dates('date', 'month', order='DESC')

    years = sorted(set(date.year for date in dates), reverse=True)
    print(f"Found years: {years}")  # Debug print

    return JsonResponse({"years": years})

# def get_months_for_year(request, security_id, year):
#     """Get available months for a security and year, handling both reports and risks."""
#     model = RiskComparison if 'risks' in request.path else FinancialReport
#
#     dates = model.objects.filter(
#         security_id=security_id,
#         date__year=year
#     ).dates('date', 'month', order='DESC')
#
#     months = [date.month for date in dates]
#     return JsonResponse({"months": months})

def get_months_for_year(request, security_id, year):
    """Get available months for a security and year, handling both reports and risks."""
    model = RiskComparison if 'risks' in request.path else FinancialReport

    print(f"Getting months for security {security_id}, year {year} using model {model.__name__}")

    dates = model.objects.filter(
        security_id=security_id,
        date__year=year
    ).dates('date', 'month', order='DESC')

    months = [date.month for date in dates]
    print(f"Found months: {months}")

    return JsonResponse({"months": sorted(months)})  # Sort months for consistency


# View functions using the generalized search view
def search_financial_report(request):
    """View for financial report comparison."""
    return generalized_search_view(
        request=request,
        model=FinancialReport,
        form_class=FinancialReportSearchForm,
        template_name='FinancialReports.html'
    )


def search_financial_risks(request):
    """View for risk comparison."""
    return generalized_search_view(
        request=request,
        model=RiskComparison,
        form_class=FinancialRisksSearchForm,
        template_name='FinancialRisks.html'
    )

# def search_financial_risks(request):
#     report_left = None
#     report_right = None
#     form_left = FinancialRisksSearchForm(prefix='left')
#     form_right = FinancialRisksSearchForm(prefix='right')
#
#     if request.method == 'POST':
#         form_id = request.POST.get('form_id')
#
#         if form_id == 'left':
#             form_left = FinancialRisksSearchForm(request.POST, prefix='left')
#             if form_left.is_valid():
#                 ticker = form_left.cleaned_data['ticker']
#                 year = form_left.cleaned_data['year']
#                 month = form_left.cleaned_data['month']
#                 try:
#                     report_left = RiskComparison.objects.get(
#                         ticker=ticker,
#                         year=year,
#                         month=month
#                     )
#                 except RiskComparison.DoesNotExist:
#                     report_left = None
#
#                 # Store the current values in session
#                 request.session['left-ticker'] = ticker
#                 request.session['left-year'] = year
#                 request.session['left-month'] = month
#
#         elif form_id == 'right':
#             form_right = FinancialRisksSearchForm(request.POST, prefix='right')
#             if form_right.is_valid():
#                 ticker = form_right.cleaned_data['ticker']
#                 year = form_right.cleaned_data['year']
#                 month = form_right.cleaned_data['month']
#                 try:
#                     report_right = RiskComparison.objects.get(
#                         ticker=ticker,
#                         year=year,
#                         month=month
#                     )
#                 except RiskComparison.DoesNotExist:
#                     report_right = None
#
#                 # Store the current values in session
#                 request.session['right-ticker'] = ticker
#                 request.session['right-year'] = year
#                 request.session['right-month'] = month
#
#     # Reinitialize forms with session data if available
#     if 'left-ticker' in request.session:
#         initial_left = {
#             'ticker': request.session['left-ticker'],
#             'year': request.session['left-year'],
#             'month': request.session['left-month']
#         }
#         form_left = FinancialRisksSearchForm(initial=initial_left, prefix='left')
#         try:
#             report_left = RiskComparison.objects.get(
#                 ticker=initial_left['ticker'],
#                 year=initial_left['year'],
#                 month=initial_left['month']
#             )
#         except RiskComparison.DoesNotExist:
#             report_left = None
#
#     if 'right-ticker' in request.session:
#         initial_right = {
#             'ticker': request.session['right-ticker'],
#             'year': request.session['right-year'],
#             'month': request.session['right-month']
#         }
#         form_right = FinancialRisksSearchForm(initial=initial_right, prefix='right')
#         try:
#             report_right = RiskComparison.objects.get(
#                 ticker=initial_right['ticker'],
#                 year=initial_right['year'],
#                 month=initial_right['month']
#             )
#         except RiskComparison.DoesNotExist:
#             report_right = None
#
#     context = {
#         'form_left': form_left,
#         'form_right': form_right,
#         'report_left': report_left,
#         'report_right': report_right
#     }
#     return render(request, 'FinancialRisks.html', context)
# def search_financial_report(request):
#     report_left = None
#     report_right = None
#     form_left = FinancialReportSearchForm(prefix='left')
#     form_right = FinancialReportSearchForm(prefix='right')
#
#     if request.method == 'POST':
#         form_id = request.POST.get('form_id')
#
#         if form_id == 'left':
#             form_left = FinancialReportSearchForm(request.POST, prefix='left')
#             if form_left.is_valid():
#                 ticker = form_left.cleaned_data['ticker']
#                 year = form_left.cleaned_data['year']
#                 month = form_left.cleaned_data['month']
#                 try:
#                     report_left = FinancialReport.objects.get(
#                         ticker=ticker,
#                         year=year,
#                         month=month
#                     )
#                 except FinancialReport.DoesNotExist:
#                     report_left = None
#
#                 # Store the current values in session
#                 request.session['left-ticker'] = ticker
#                 request.session['left-year'] = year
#                 request.session['left-month'] = month
#
#         elif form_id == 'right':
#             form_right = FinancialReportSearchForm(request.POST, prefix='right')
#             if form_right.is_valid():
#                 ticker = form_right.cleaned_data['ticker']
#                 year = form_right.cleaned_data['year']
#                 month = form_right.cleaned_data['month']
#                 try:
#                     report_right = FinancialReport.objects.get(
#                         ticker=ticker,
#                         year=year,
#                         month=month
#                     )
#                 except FinancialReport.DoesNotExist:
#                     report_right = None
#
#                 # Store the current values in session
#                 request.session['right-ticker'] = ticker
#                 request.session['right-year'] = year
#                 request.session['right-month'] = month
#
#     # Reinitialize forms with session data if available
#     if 'left-ticker' in request.session:
#         initial_left = {
#             'ticker': request.session['left-ticker'],
#             'year': request.session['left-year'],
#             'month': request.session['left-month']
#         }
#         form_left = FinancialReportSearchForm(initial=initial_left, prefix='left')
#         try:
#             report_left = FinancialReport.objects.get(
#                 ticker=initial_left['ticker'],
#                 year=initial_left['year'],
#                 month=initial_left['month']
#             )
#         except FinancialReport.DoesNotExist:
#             report_left = None
#
#     if 'right-ticker' in request.session:
#         initial_right = {
#             'ticker': request.session['right-ticker'],
#             'year': request.session['right-year'],
#             'month': request.session['right-month']
#         }
#         form_right = FinancialReportSearchForm(initial=initial_right, prefix='right')
#         try:
#             report_right = FinancialReport.objects.get(
#                 ticker=initial_right['ticker'],
#                 year=initial_right['year'],
#                 month=initial_right['month']
#             )
#         except FinancialReport.DoesNotExist:
#             report_right = None
#
#     context = {
#         'form_left': form_left,
#         'form_right': form_right,
#         'report_left': report_left,
#         'report_right': report_right
#     }
#     return render(request, 'FinancialReports.html', context)
class ScreenerService:
    """
    Service class to handle screener logic
    """
    VALID_RATIOS = [
        'pe_ratio', 'pb_ratio', 'ps_ratio', 'peg_ratio', 'ev_ebitda',
        'gross_profit_margin', 'operating_profit_margin', 'net_profit_margin',
        'return_on_assets', 'return_on_equity', 'debt_to_equity',
        'current_ratio', 'quick_ratio', 'dividend_yield', 'before_dividend_yield'
    ]

    @classmethod
    def build_filter_query(cls, filters):
        """
        Build Q objects from filter parameters
        """
        q_filters = Q()
        for filter_string in filters:
            try:
                ratio_name, operator, value = filter_string.split(':')
                if ratio_name in cls.VALID_RATIOS and operator in ['gt', 'lt', 'gte', 'lte']:
                    filter_expr = f'{ratio_name}__{operator}'
                    q_filters &= Q(**{filter_expr: float(value)})
            except ValueError:
                continue
        return q_filters

    @classmethod
    def get_filtered_ratios(cls, filters):
        """
        Get filtered financial ratios with latest data
        """
        q_filters = cls.build_filter_query(filters)

        # Subquery to find the latest date for each security
        latest_date_subquery = FinancialRatio.objects.filter(
            security=OuterRef('security')
        ).order_by('-date').values('date')[:1]

        # Apply filters to get the latest financial ratios
        filtered_ratios = FinancialRatio.objects.filter(
            date=Subquery(latest_date_subquery)
        ).filter(q_filters).select_related('security', 'security__exchange')

        # Prepare the response data
        return [
            {
                'ticker': ratio.security.ticker,
                'exchange': ratio.security.exchange.code,
                'full_symbol': ratio.security.full_symbol,
                'date': ratio.date,
                'price': ratio.price,
                **{field: getattr(ratio, field) for field in cls.VALID_RATIOS if getattr(ratio, field) is not None},
            }
            for ratio in filtered_ratios
        ]

def screener(request):
    """
    View to render the screener page
    """
    return render(request, 'complex_analysis.html')

def filter_ratios(request):
    """
    API view to handle ratio filtering
    """
    filters = request.GET.getlist('filters[]')
    data = ScreenerService.get_filtered_ratios(filters)
    return JsonResponse(data, safe=False)
# def screener(request):
#     return render(request, 'complex_analysis.html')
#
# def filter_ratios(request):
#     filters = request.GET.getlist('filters[]')
#
#     # Define valid ratios
#     valid_ratios = [
#         'pe_ratio', 'pb_ratio', 'ps_ratio', 'peg_ratio', 'ev_ebitda',
#         'gross_profit_margin', 'operating_profit_margin', 'net_profit_margin',
#         'return_on_assets', 'return_on_equity', 'debt_to_equity', 'current_ratio', 'quick_ratio', 'dividend_yield', 'before_dividend_yield'
#     ]
#
#     q_filters = Q()
#
#     # Apply each filter
#     for filter_string in filters:
#         ratio_name, operator, value = filter_string.split(':')
#         if ratio_name in valid_ratios and operator in ['gt', 'lt', 'gte', 'lte']:
#             filter_expr = f'{ratio_name}__{operator}'
#             q_filters &= Q(**{filter_expr: float(value)})
#
#     # Subquery to find the latest date for each ticker in FinancialRatio
#     latest_date_subquery = FinancialRatio.objects.filter(
#         ticker=OuterRef('ticker')
#     ).order_by('-date').values('date')[:1]
#
#     # Apply filters to get the latest financial ratios
#     filtered_ratios = FinancialRatio.objects.filter(
#         date=Subquery(latest_date_subquery)
#     ).filter(q_filters).annotate(
#         latest_price=Cast(
#             Subquery(
#                 PriceData.objects.filter(
#                     ticker=OuterRef('ticker')
#                 ).order_by('-date').values('price')[:1]
#             ), DecimalField(max_digits=20, decimal_places=2)
#         ),
#         latest_market_cap=Cast(
#             Subquery(
#                 PriceData.objects.filter(
#                     ticker=OuterRef('ticker')
#                 ).order_by('-date').values('market_cap')[:1]
#             ), DecimalField(max_digits=30, decimal_places=2)
#         )
#     ).values('ticker', 'date', *valid_ratios, 'latest_price', 'latest_market_cap').order_by('ticker')
#
#     data = list(filtered_ratios)
#
#     return JsonResponse(data, safe=False)
def get_metrics(request, ticker, metric_name):
    if metric_name not in [field.name for field in FinancialData._meta.get_fields() if field.name not in ['id', 'date', 'ticker']]:
        return JsonResponse({'error': 'Invalid metric name'}, status=400)

    data = FinancialData.objects.filter(ticker=ticker).values('date', metric_name)
    return JsonResponse(list(data), safe=False)

def metric_plotter(request):
    tickers = FinancialData.objects.values_list('ticker', flat=True).distinct()
    metrics = [field.name for field in FinancialData._meta.get_fields() if field.name not in ['id', 'date', 'ticker']]
    return render(request, 'metric_plotter.html', {'tickers': tickers, 'metrics': metrics})

def get_data(request):
    ticker = request.GET.get('ticker')
    metrics = request.GET.getlist('metric[]')

    # Ensure 'date' is always included
    fields_to_fetch = ['date'] + metrics

    # Query the database for the selected metrics
    data = FinancialData.objects.filter(ticker=ticker).order_by('date').values(*fields_to_fetch)

    # Convert QuerySet to a list to return as JSON
    data_list = list(data)

    return JsonResponse(data_list, safe=False)

def ticker_suggestions(request):
    query = request.GET.get('query', '')
    suggestions = FinancialData.objects.filter(ticker__icontains=query).values_list('ticker', flat=True).distinct()
    return JsonResponse(list(suggestions), safe=False)

def about(request):
    return render(request, 'about.html')

def contact(request):
    return render(request, 'contact.html')

####
def get_price_data(security_id, period='1d'):
    """Helper function to get price data for a specific period"""
    latest_date = PriceData.objects.aggregate(Max('date'))['date__max']

    if not latest_date:
        return None

    # Calculate start date based on period
    if period == '1d':
        start_date = latest_date
    elif period == '1w':
        start_date = latest_date - timedelta(days=7)
    elif period == '1m':
        start_date = latest_date - timedelta(days=30)
    elif period == '1y':
        start_date = latest_date - timedelta(days=365)
    elif period == '5y':
        start_date = latest_date - timedelta(days=1825)
    else:
        start_date = latest_date

    price_data = PriceData.objects.filter(
        security_id=security_id,
        date__gte=start_date
    ).order_by('date').values(
        'date', 'open_price', 'high_price',
        'low_price', 'close_price', 'volume'
    )

    return list(price_data)


def get_security_prices(request):
    """AJAX endpoint for getting price data"""
    security_id = request.GET.get('security_id')
    period = request.GET.get('period', '1d')

    if not security_id:
        return JsonResponse({'error': 'Security ID required'}, status=400)

    price_data = get_price_data(security_id, period)

    if not price_data:
        return JsonResponse({'error': 'No data available'}, status=404)

    return JsonResponse({
        'prices': price_data,
        'period': period
    })


def index(request):
    """Landing page view with interactive price chart"""
    # try:
    # Get the latest date with data
    latest_date = PriceData.objects.aggregate(Max('date'))['date__max']
    if not latest_date:
        return render(request, 'fin_data_cl/index.html', {
            'error': 'No price data available'
        })

    # Calculate daily performance and get top movers
    daily_performance = PriceData.objects.filter(
        date=latest_date
    ).annotate(
        daily_return=ExpressionWrapper(
            (F('close_price') - F('open_price')) * 100.0 / F('open_price'),  # Fixed calculation
            output_field=FloatField()
        ),
        volume_formatted=ExpressionWrapper(
            Cast(F('volume'), FloatField()) / 1000000,
            output_field=FloatField()
        )
    ).select_related('security').exclude(  # Add exclusion for null values
        open_price=0
    ).exclude(
        open_price__isnull=True
    ).order_by('-daily_return')
    # Get top gainers and losers
    top_gainers = [
        {
            'symbol': perf.security.ticker,
            'name': perf.security.name,
            'change': f"+{perf.daily_return:.1f}%",
            'price': f"${float(perf.close_price):.2f}",
            'volume': f"{perf.volume_formatted:.1f}M",
            'is_positive': str(perf.daily_return > 0).lower(),  # Convert to JavaScript boolean string
            'security_id': perf.security.id
        }
        for perf in daily_performance[:5]
    ]
    print(top_gainers)
    bottom_performers = [
        {
            'symbol': perf.security.ticker,
            'name': perf.security.name,
            'change': f"+{perf.daily_return:.1f}%",
            'price': f"${float(perf.close_price):.2f}",
            'volume': f"{perf.volume_formatted:.1f}M",
            'is_positive': str(perf.daily_return > 0).lower(),  # Convert to JavaScript boolean string
            'security_id': perf.security.id
        }
        for perf in daily_performance.reverse()[:5]
    ]

    # Get market breadth data
    total_stocks = daily_performance.count()
    gainers_count = daily_performance.filter(daily_return__gt=0).count()
    losers_count = daily_performance.filter(daily_return__lt=0).count()
    unchanged_count = total_stocks - gainers_count - losers_count

    # Get initial price data for top gainer
    initial_security = None
    initial_price_data = None
    if top_gainers:
        initial_security = {
            **top_gainers[0],  # Spread existing data
        }
        initial_price_data = get_price_data(initial_security['security_id'], '1w') #Default shown

    context = {
        'latest_date': latest_date,
        'top_gainers': top_gainers,
        'bottom_performers': bottom_performers,
        'initial_security': initial_security,
        'initial_price_data': json.dumps(initial_price_data, cls=DjangoJSONEncoder),  # Serialize properly
        'market_breadth': {
            'gainers': gainers_count,
            'losers': losers_count,
            'unchanged': unchanged_count,
            'total': total_stocks,
            'gainers_percentage': (gainers_count / total_stocks * 100) if total_stocks > 0 else 0,
            'losers_percentage': (losers_count / total_stocks * 100) if total_stocks > 0 else 0,
        }
    }
    #
    # except Exception as e:
    #     context = {
    #         'error': f"Unable to fetch market data: {str(e)}"
    #     }

    return render(request, 'index.html', context)