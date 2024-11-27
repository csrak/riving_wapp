from django.http import JsonResponse
from django.shortcuts import render
from .models import FinancialData, FinancialRatio, PriceData, FinancialReport, RiskComparison
from django.db.models import Q, Subquery, OuterRef, DecimalField, F
from django.db.models.functions import Cast
from .forms import FinancialReportSearchForm, FinancialRisksSearchForm

def search_financial_risks(request):
    report_left = None
    report_right = None
    form_left = FinancialRisksSearchForm(prefix='left')
    form_right = FinancialRisksSearchForm(prefix='right')

    if request.method == 'POST':
        form_id = request.POST.get('form_id')

        if form_id == 'left':
            form_left = FinancialRisksSearchForm(request.POST, prefix='left')
            if form_left.is_valid():
                ticker = form_left.cleaned_data['ticker']
                year = form_left.cleaned_data['year']
                month = form_left.cleaned_data['month']
                try:
                    report_left = RiskComparison.objects.get(
                        ticker=ticker,
                        year=year,
                        month=month
                    )
                except RiskComparison.DoesNotExist:
                    report_left = None

        elif form_id == 'right':
            form_right = FinancialRisksSearchForm(request.POST, prefix='right')
            if form_right.is_valid():
                ticker = form_right.cleaned_data['ticker']
                year = form_right.cleaned_data['year']
                month = form_right.cleaned_data['month']
                try:
                    report_right = RiskComparison.objects.get(
                        ticker=ticker,
                        year=year,
                        month=month
                    )
                except RiskComparison.DoesNotExist:
                    report_right = None

        # Reinitialize the other form if it wasn't submitted
        if form_id == 'left':
            if 'right-ticker' in request.session:
                initial_right = {
                    'ticker': request.session['right-ticker'],
                    'year': request.session['right-year'],
                    'month': request.session['right-month']
                }
                form_right = FinancialRisksSearchForm(initial=initial_right, prefix='right')
                try:
                    report_right = RiskComparison.objects.get(
                        ticker=initial_right['ticker'],
                        year=initial_right['year'],
                        month=initial_right['month']
                    )
                except RiskComparison.DoesNotExist:
                    report_right = None
        else:
            if 'left-ticker' in request.session:
                initial_left = {
                    'ticker': request.session['left-ticker'],
                    'year': request.session['left-year'],
                    'month': request.session['left-month']
                }
                form_left = FinancialRisksSearchForm(initial=initial_left, prefix='left')
                try:
                    report_left = RiskComparison.objects.get(
                        ticker=initial_left['ticker'],
                        year=initial_left['year'],
                        month=initial_left['month']
                    )
                except RiskComparison.DoesNotExist:
                    report_left = None

        # Store the current values in session
        if form_id == 'left' and form_left.is_valid():
            request.session['left-ticker'] = form_left.cleaned_data['ticker']
            request.session['left-year'] = form_left.cleaned_data['year']
            request.session['left-month'] = form_left.cleaned_data['month']
        elif form_id == 'right' and form_right.is_valid():
            request.session['right-ticker'] = form_right.cleaned_data['ticker']
            request.session['right-year'] = form_right.cleaned_data['year']
            request.session['right-month'] = form_right.cleaned_data['month']

    context = {
        'form_left': form_left,
        'form_right': form_right,
        'report_left': report_left,
        'report_right': report_right
    }
    return render(request, 'FinancialRisks.html', context)
def search_financial_report(request):
    report_left = None
    report_right = None
    form_left = FinancialReportSearchForm(prefix='left')
    form_right = FinancialReportSearchForm(prefix='right')

    if request.method == 'POST':
        form_id = request.POST.get('form_id')

        if form_id == 'left':
            form_left = FinancialReportSearchForm(request.POST, prefix='left')
            if form_left.is_valid():
                ticker = form_left.cleaned_data['ticker']
                year = form_left.cleaned_data['year']
                month = form_left.cleaned_data['month']
                try:
                    report_left = FinancialReport.objects.get(
                        ticker=ticker,
                        year=year,
                        month=month
                    )
                except FinancialReport.DoesNotExist:
                    report_left = None

                # Store the current values in session
                request.session['left-ticker'] = ticker
                request.session['left-year'] = year
                request.session['left-month'] = month

        elif form_id == 'right':
            form_right = FinancialReportSearchForm(request.POST, prefix='right')
            if form_right.is_valid():
                ticker = form_right.cleaned_data['ticker']
                year = form_right.cleaned_data['year']
                month = form_right.cleaned_data['month']
                try:
                    report_right = FinancialReport.objects.get(
                        ticker=ticker,
                        year=year,
                        month=month
                    )
                except FinancialReport.DoesNotExist:
                    report_right = None

                # Store the current values in session
                request.session['right-ticker'] = ticker
                request.session['right-year'] = year
                request.session['right-month'] = month

    # Reinitialize forms with session data if available
    if 'left-ticker' in request.session:
        initial_left = {
            'ticker': request.session['left-ticker'],
            'year': request.session['left-year'],
            'month': request.session['left-month']
        }
        form_left = FinancialReportSearchForm(initial=initial_left, prefix='left')
        try:
            report_left = FinancialReport.objects.get(
                ticker=initial_left['ticker'],
                year=initial_left['year'],
                month=initial_left['month']
            )
        except FinancialReport.DoesNotExist:
            report_left = None

    if 'right-ticker' in request.session:
        initial_right = {
            'ticker': request.session['right-ticker'],
            'year': request.session['right-year'],
            'month': request.session['right-month']
        }
        form_right = FinancialReportSearchForm(initial=initial_right, prefix='right')
        try:
            report_right = FinancialReport.objects.get(
                ticker=initial_right['ticker'],
                year=initial_right['year'],
                month=initial_right['month']
            )
        except FinancialReport.DoesNotExist:
            report_right = None

    context = {
        'form_left': form_left,
        'form_right': form_right,
        'report_left': report_left,
        'report_right': report_right
    }
    return render(request, 'FinancialReports.html', context)

def screener(request):
    return render(request, 'complex_analysis.html')

def filter_ratios(request):
    filters = request.GET.getlist('filters[]')

    # Define valid ratios
    valid_ratios = [
        'pe_ratio', 'pb_ratio', 'ps_ratio', 'peg_ratio', 'ev_ebitda',
        'gross_profit_margin', 'operating_profit_margin', 'net_profit_margin',
        'return_on_assets', 'return_on_equity', 'debt_to_equity', 'current_ratio', 'quick_ratio', 'dividend_yield', 'before_dividend_yield'
    ]

    q_filters = Q()

    # Apply each filter
    for filter_string in filters:
        ratio_name, operator, value = filter_string.split(':')
        if ratio_name in valid_ratios and operator in ['gt', 'lt', 'gte', 'lte']:
            filter_expr = f'{ratio_name}__{operator}'
            q_filters &= Q(**{filter_expr: float(value)})

    # Subquery to find the latest date for each ticker in FinancialRatio
    latest_date_subquery = FinancialRatio.objects.filter(
        ticker=OuterRef('ticker')
    ).order_by('-date').values('date')[:1]

    # Apply filters to get the latest financial ratios
    filtered_ratios = FinancialRatio.objects.filter(
        date=Subquery(latest_date_subquery)
    ).filter(q_filters).annotate(
        latest_price=Cast(
            Subquery(
                PriceData.objects.filter(
                    ticker=OuterRef('ticker')
                ).order_by('-date').values('price')[:1]
            ), DecimalField(max_digits=20, decimal_places=2)
        ),
        latest_market_cap=Cast(
            Subquery(
                PriceData.objects.filter(
                    ticker=OuterRef('ticker')
                ).order_by('-date').values('market_cap')[:1]
            ), DecimalField(max_digits=30, decimal_places=2)
        )
    ).values('ticker', 'date', *valid_ratios, 'latest_price', 'latest_market_cap').order_by('ticker')

    data = list(filtered_ratios)

    return JsonResponse(data, safe=False)

def get_metrics(request, ticker, metric_name):
    if metric_name not in [field.name for field in FinancialData._meta.get_fields() if field.name not in ['id', 'date', 'ticker']]:
        return JsonResponse({'error': 'Invalid metric name'}, status=400)

    data = FinancialData.objects.filter(ticker=ticker).values('date', metric_name)
    return JsonResponse(list(data), safe=False)

def index(request):
    tickers = FinancialData.objects.values_list('ticker', flat=True).distinct()
    metrics = [field.name for field in FinancialData._meta.get_fields() if field.name not in ['id', 'date', 'ticker']]
    return render(request, 'index.html', {'tickers': tickers, 'metrics': metrics})

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
