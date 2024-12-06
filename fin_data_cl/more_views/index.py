# more_views/index.py
from django.shortcuts import render
from django.db.models import F, ExpressionWrapper, FloatField, Count, Case, When, Value
from django.utils import timezone
from datetime import timedelta
from fin_data_cl.models import PriceData, Security
from django.conf import settings


def calculate_market_breadth(queryset):
    """Calculate market breadth statistics from price data."""
    market_stats = queryset.aggregate(
        gainers=Count(Case(
            When(daily_change__gt=0, then=1),
        )),
        losers=Count(Case(
            When(daily_change__lt=0, then=1),
        )),
        unchanged=Count(Case(
            When(daily_change=0, then=1),
        ))
    )

    total = sum(market_stats.values())

    if total == 0:
        return {
            'gainers': 0, 'losers': 0, 'unchanged': 0,
            'gainers_percentage': 0,
            'losers_percentage': 0,
            'unchanged_percentage': 0,
            'total': 0
        }

    return {
        'gainers': market_stats['gainers'],
        'losers': market_stats['losers'],
        'unchanged': market_stats['unchanged'],
        'gainers_percentage': (market_stats['gainers'] / total) * 100,
        'losers_percentage': (market_stats['losers'] / total) * 100,
        'unchanged_percentage': (market_stats['unchanged'] / total) * 100,
        'total': total
    }


def get_top_movers(queryset, limit=5):
    """Get top gainers and losers from price data."""
    gainers = queryset.order_by('-daily_change')[:limit]
    losers = queryset.order_by('daily_change')[:limit]

    format_mover = lambda x: {
        'symbol': x.security.ticker,
        'change': f"{x.daily_change:+.2f}%",
        'price': f"${x.close_price:.2f}"
    }

    return (
        [format_mover(g) for g in gainers],
        [format_mover(l) for l in losers]
    )


def get_latest_trading_data():
    """Get the most recent trading date with data and its data."""
    latest_data = (PriceData.objects
                   .select_related('security')
                   .order_by('-date')
                   .first())

    if not latest_data:
        return None, None, None

    # Get all data for the latest date
    latest_date = latest_data.date

    # Calculate daily changes
    latest_prices = (PriceData.objects
    .filter(date=latest_date)
    .select_related('security')
    .annotate(
        daily_change=ExpressionWrapper(
            (F('close_price') - F('open_price')) / F('open_price') * 100,
            output_field=FloatField()
        )
    ))

    return latest_date, latest_prices, latest_data.date.strftime("%B %d, %Y")


def index(request):
    """Homepage view showing market overview and interactive charts."""
    try:
        # Get latest trading data
        latest_date, latest_prices, formatted_date = get_latest_trading_data()

        if not latest_date:
            return render(request, 'fin_data_cl/index.html', {
                'error': 'No price data available'
            })

        # Calculate market breadth
        market_stats = latest_prices.aggregate(
            gainers=Count(Case(When(daily_change__gt=0, then=1))),
            losers=Count(Case(When(daily_change__lt=0, then=1))),
            unchanged=Count(Case(When(daily_change=0, then=1)))
        )

        total = sum(market_stats.values())

        market_breadth = {
            'gainers': market_stats['gainers'],
            'losers': market_stats['losers'],
            'unchanged': market_stats['unchanged'],
            'gainers_percentage': (market_stats['gainers'] / total * 100) if total > 0 else 0,
            'losers_percentage': (market_stats['losers'] / total * 100) if total > 0 else 0,
            'unchanged_percentage': (market_stats['unchanged'] / total * 100) if total > 0 else 0,
            'total': total
        }

        # Get top gainers and losers
        gainers = latest_prices.order_by('-daily_change')[:5]
        losers = latest_prices.order_by('daily_change')[:5]

        format_mover = lambda x: {
            'symbol': x.security.ticker,
            'change': f"{x.daily_change:+.2f}%",
            'price': f"${x.close_price:.2f}"
        }

        top_gainers = [format_mover(g) for g in gainers]
        bottom_performers = [format_mover(l) for l in losers]

        # Analysis tools definition
        analysis_tools = [
            {
                'name': 'Price Analysis',
                'description': 'Historical price trends and patterns',
                'url': f"{settings.API_BASE_URL}price-data/"
            },
            {
                'name': 'Stock Screener',
                'description': 'Filter stocks by key metrics',
                'url': '/screener/'
            },
            {
                'name': 'Financial Ratios',
                'description': 'Compare company metrics',
                'url': f"{settings.API_BASE_URL}financial-ratios/"
            },
            {
                'name': 'Risk Analysis',
                'description': 'Evaluate investment risks',
                'url': f"{settings.API_BASE_URL}risk-comparisons/"
            }
        ]

        context = {
            'latest_date': latest_date,
            'formatted_date': formatted_date,
            'market_breadth': market_breadth,
            'top_gainers': top_gainers,
            'bottom_performers': bottom_performers,
            'analysis_tools': analysis_tools,
            'api_base_url': settings.API_BASE_URL
        }

        return render(request, 'index.html', context)

    except Exception as e:
        return render(request, 'index.html', {
            'error': f'Error loading market data: {str(e)}'
        })