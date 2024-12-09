#fin_data_cl/views.py
from django.urls import reverse
from .models import FinancialData, FinancialRatio, FinancialReport, RiskComparison, PriceData, Security
from django.db.models import Q, Subquery, OuterRef, Max, F, ExpressionWrapper, FloatField
from django.db.models.functions import Cast
from .utils.search_view import generalized_search_view
from .forms import FinancialReportSearchForm, FinancialRisksSearchForm
from django.http import JsonResponse
from django.template.exceptions import TemplateDoesNotExist
from django.shortcuts import render
from django.http import HttpResponse
from django.core.mail import send_mail
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime, timedelta
import json
from django.template.loader import render_to_string
from .viewsets import PriceDataViewSet
from rest_framework.test import APIRequestFactory
from django.conf import settings
import os
def get_securities_for_exchange(request, exchange_id):
    """Get securities for an exchange, ensuring they have associated data."""
    # Determine the model based on 'type' parameter
    is_risk = request.GET.get('type') == 'risk'
    model = RiskComparison if is_risk else FinancialReport

    # Filter securities that are associated with the correct model
    securities_with_data = model.objects.filter(
        security__exchange_id=exchange_id,
        security__is_active=True
    ).values_list('security_id', flat=True).distinct()

    # Use these securities to get the Security objects
    securities = Security.objects.filter(
        id__in=securities_with_data
    ).order_by('name')

    response_data = {
        "securities": [
            {"id": security.id, "name": security.name}
            for security in securities
        ]
    }

    return JsonResponse(response_data)


def get_years_for_security(request, security_id):
    """Get available years for a security."""
    is_risk = request.GET.get('type') == 'risk'
    model = RiskComparison if is_risk else FinancialReport

    # Only get distinct years where data is actually available
    dates = model.objects.filter(
        security_id=security_id
    ).dates('date', 'year', order='DESC')

    years = sorted(set(date.year for date in dates), reverse=True)
    return JsonResponse({"years": years})

def get_months_for_year(request, security_id, year):
    """Get available months for a security and year."""
    is_risk = request.GET.get('type') == 'risk'
    model = RiskComparison if is_risk else FinancialReport

    # Filter for the correct year and only get months with data
    dates = model.objects.filter(
        security_id=security_id,
        date__year=year
    ).dates('date', 'month', order='DESC')

    months = sorted([date.month for date in dates])
    return JsonResponse({"months": months})


def search_financial_risks(request):
    from django.template.loader import render_to_string
    from .forms import FinancialRisksSearchForm
    from .models import RiskComparison
    from django.http import JsonResponse
    import logging

    logger = logging.getLogger(__name__)

    def get_report_sections(report):
        if not report:
            return []
        return [
            {
                'id': 'Overview',
                'title': 'New Risks',
                'items': report.new_risks if hasattr(report, 'new_risks') else []
            },
            {
                'id': 'Risks',
                'title': 'Old Risks',
                'items': report.old_risks if hasattr(report, 'old_risks') else []
            },
            {
                'id': 'Changes',
                'title': 'Risk Changes',
                'items': report.modified_risks if hasattr(report, 'modified_risks') else []
            }
        ]

    if request.method == "POST" and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        form_id = request.POST.get('form_id')
        logger.debug(f"Received form data: {request.POST}")

        if form_id == 'left':
            form = FinancialRisksSearchForm(data=request.POST, prefix="left")
        else:
            form = FinancialRisksSearchForm(data=request.POST, prefix="right")

        if form.is_valid():
            logger.debug("Form is valid")
            report = form.get_risk_comparison()
            logger.debug(f"Got report: {report}")

            if report:
                html = render_to_string(
                    'fin_data_cl/financial_risks_accordion.html',
                    {'sections': get_report_sections(report), 'side': form_id.capitalize()}
                )
                return JsonResponse({'html': html})
            else:
                return JsonResponse({'error': 'No report found for the selected criteria'}, status=404)
        else:
            logger.error(f"Form errors: {form.errors}")
            return JsonResponse({
                'error': 'Invalid form data',
                'details': form.errors
            }, status=400)

    form_left = FinancialRisksSearchForm(prefix="left")
    form_right = FinancialRisksSearchForm(prefix="right")

    context = {
        "form_left": form_left,
        "form_right": form_right,
        "report_left": None,
        "report_right": None,
    }

    return render(request, "FinancialRisks.html", context)
def get_report_sections(report):
    if not report:
        return []
    return [
        {
            'id': 'Overview',
            'title': 'New Risks',
            'items': report.new_risks if hasattr(report, 'new_risks') else []
        },
        {
            'id': 'Risks',
            'title': 'Old Risks',
            'items': report.old_risks if hasattr(report, 'old_risks') else []
        },
        {
            'id': 'Changes',
            'title': 'Risk Changes',
            'items': report.modified_risks if hasattr(report, 'modified_risks') else []
        }
    ]


def search_financial_report(request):
    """View for financial report comparison."""
    extra_context = {
        'securities_url': reverse('fin_data_api:securities_by_exchange', kwargs={'exchange_id': 0}),
        'years_url': reverse('fin_data_api:security_years', kwargs={'security_id': 0}),
        'months_url': reverse('fin_data_api:security_months', kwargs={'security_id': 0, 'year': 0})
    }

    return generalized_search_view(
        request=request,
        model=FinancialReport,
        form_class=FinancialReportSearchForm,
        template_name='FinancialReports.html',
        extra_context=extra_context
    )


class ScreenerService:
    """Service class to handle screener logic"""
    VALID_RATIOS = [
        'pe_ratio', 'pb_ratio', 'ps_ratio', 'peg_ratio', 'ev_ebitda',
        'gross_profit_margin', 'operating_profit_margin', 'net_profit_margin',
        'return_on_assets', 'return_on_equity', 'debt_to_equity',
        'current_ratio', 'quick_ratio', 'dividend_yield', 'before_dividend_yield'
    ]

    @classmethod
    def build_filter_query(cls, filters):
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
        q_filters = cls.build_filter_query(filters)
        latest_date_subquery = FinancialRatio.objects.filter(
            security=OuterRef('security')
        ).order_by('-date').values('date')[:1]

        filtered_ratios = FinancialRatio.objects.filter(
            date=Subquery(latest_date_subquery)
        ).filter(q_filters).select_related('security', 'security__exchange')

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
    """View to render the screener page"""
    return render(request, 'screener.html', {
        'screener_url': reverse('fin_data:screener'),
        'filter_url': reverse('fin_data_api:filter_ratios')
    })


def filter_ratios(request):
    """API view to handle ratio filtering"""
    filters = request.GET.getlist('filters[]')
    data = ScreenerService.get_filtered_ratios(filters)
    return JsonResponse(data, safe=False)


def get_metrics(request, ticker, metric_name):
    if metric_name not in [field.name for field in FinancialData._meta.get_fields() if field.name not in ['id', 'date', 'ticker']]:
        return JsonResponse({'error': 'Invalid metric name'}, status=400)

    data = FinancialData.objects.filter(ticker=ticker).values('date', metric_name).order_by('date')
    return JsonResponse(list(data), safe=False)


def metric_plotter(request):
    tickers = FinancialData.objects.values_list('ticker', flat=True).distinct()
    metrics = [field.name for field in FinancialData._meta.get_fields() if field.name not in ['id', 'date', 'ticker']]
    return render(request, 'metric_plotter.html', {
        'tickers': tickers,
        'metrics': metrics,
        'data_url': reverse('fin_data_api:get_data'),
        'suggestions_url': reverse('fin_data_api:ticker_suggestions')
    })


# def get_data(request):
#     ticker = request.GET.get('ticker')
#     metrics = request.GET.getlist('metric[]')
#     fields_to_fetch = ['date'] + metrics
#     data = FinancialData.objects.filter(ticker=ticker).order_by('date').values(*fields_to_fetch)
#     return JsonResponse(list(data), safe=False)
#
#
# def ticker_suggestions(request):
#     query = request.GET.get('query', '')
#     suggestions = FinancialData.objects.filter(
#         ticker__icontains=query
#     ).values_list('ticker', flat=True).distinct().order_by('ticker')
#     return JsonResponse(list(suggestions), safe=False)
#
#
def about(request):
    return render(request, 'about.html')


def contact(request):
    if request.method == "POST":
        # Get form data
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()

        # Define the directory and filename
        messages_dir = os.path.join(settings.BASE_DIR, 'user_messages')
        os.makedirs(messages_dir, exist_ok=True)  # Ensure the directory exists
        message_file = os.path.join(messages_dir, f"{name}_{email.replace('@', '_')}.txt")

        # Save the message to a file
        with open(message_file, 'w', encoding='utf-8') as file:
            file.write(f"Name: {name}\n")
            file.write(f"Email: {email}\n")
            file.write("Message:\n")
            file.write(message)

        return HttpResponse("Thank you for your message! We'll get back to you soon.")

    return render(request, 'contact.html')
# def get_price_data(security_id, period='1d'):
#     """Helper function to get price data for a specific period"""
#     latest_date = PriceData.objects.aggregate(Max('date'))['date__max']
#
#     if not latest_date:
#         return None
#
#     if period == '1d':
#         start_date = latest_date
#     elif period == '1w':
#         start_date = latest_date - timedelta(days=7)
#     elif period == '1m':
#         start_date = latest_date - timedelta(days=30)
#     elif period == '1y':
#         start_date = latest_date - timedelta(days=365)
#     elif period == '5y':
#         start_date = latest_date - timedelta(days=1825)
#     else:
#         start_date = latest_date
#
#     price_data = PriceData.objects.filter(
#         security_id=security_id,
#         date__gte=start_date
#     ).order_by('date').values(
#         'date', 'open_price', 'high_price',
#         'low_price', 'close_price', 'volume'
#     )
#
#     return list(price_data)
#
#
# def get_security_prices(request):
#     """AJAX endpoint for getting price data"""
#     security_id = request.GET.get('security_id')
#     period = request.GET.get('period', '1d')
#
#     if not security_id:
#         return JsonResponse({'error': 'Security ID required'}, status=400)
#
#     price_data = get_price_data(security_id, period)
#
#     if not price_data:
#         return JsonResponse({'error': 'No data available'}, status=404)
#
#     return JsonResponse({
#         'prices': price_data,
#         'period': period
#     })
# def save_session_data(request):
#     if request.method != 'POST':
#         return JsonResponse({'error': 'Method not allowed'}, status=405)
#
#     try:
#         data = json.loads(request.body)
#         form_id = data.pop('formId', None)
#
#         if not form_id:
#             return JsonResponse({'error': 'Form ID required'}, status=400)
#
#         for key, value in data.items():
#             request.session[f'{form_id}-{key}'] = value
#         request.session.modified = True
#
#         return JsonResponse({'status': 'success'})
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=400)


from django.urls import reverse


def generic_data_view(request, template_name):
    """
    Our generic view for serving templates with the correct API base URL.
    We need to make sure we're providing the correct context.
    """
    context = {
        'api_base_url': '/api/v1/',  # This trailing slash is important
        'debug': True,  # Adding debug flag to help troubleshoot
    }

    # Let's log what template we're trying to render
    print(f"Rendering template: {template_name}")
    print(f"Context being passed: {context}")

    try:
        # Attempt to render the requested template
        return render(request, f'{template_name}.html', context)
    except TemplateDoesNotExist:
        # Log the missing template for debugging purposes
        print(f"Template '{template_name}.html' does not exist. Rendering 'In Construction' page.")
        return render(request, 'in_construction.html', context, status=404)
    except Exception as e:
        # Handle other exceptions if necessary
        print(f"An unexpected error occurred: {e}")
        return HttpResponse("An error occurred. Please try again later.", status=500)