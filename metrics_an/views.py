from django.shortcuts import render
from django.http import JsonResponse
from django.core.serializers import serialize
from fin_data_cl.models import Exchange, Security, FinancialData
from django.db.models import F
import json


def metric_plotter_view(request):
    """Main view for the metric plotter interface"""
    return render(request, 'financial/metric_plotter.html')


def get_exchanges(request):
    """API endpoint to get all exchanges"""
    exchanges = Exchange.objects.all().values('code', 'name')
    return JsonResponse(list(exchanges), safe=False)


def get_securities(request, exchange_code):
    """API endpoint to get securities for a specific exchange"""
    securities = Security.objects.filter(
        exchange__code=exchange_code,
        is_active=True
    ).values('id', 'ticker', 'name')
    return JsonResponse(list(securities), safe=False)


def get_metric_data(request, security_id):
    """API endpoint to get metric data for a specific security"""
    metric_name = request.GET.get('metric')
    if not metric_name:
        return JsonResponse({'error': 'Metric name required'}, status=400)

    try:
        data = FinancialData.objects.filter(
            security_id=security_id
        ).exclude(**{f"{metric_name}__isnull": True}
                  ).values('date', metric_name
                           ).order_by('date')

        return JsonResponse({
            'dates': [item['date'].strftime('%Y-%m-%d') for item in data],
            'values': [float(item[metric_name]) for item in data]
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)