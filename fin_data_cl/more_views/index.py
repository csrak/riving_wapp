# more_views/index.py
from django.shortcuts import render
from django.db.models import F, ExpressionWrapper, FloatField, Count, Case, When, Value
from datetime import timedelta
from fin_data_cl.models import PriceData, Security
from django.conf import settings
from django.db.models import Subquery, OuterRef
from django.core.cache import cache
from functools import lru_cache
@lru_cache(maxsize=1)
def get_analysis_tools():
    return [
        {
            'name': 'Metric Plotter',
            'description': 'Plot and compare key metrics',
            'url': f"/metric_plotter/"
        },
        {
            'name': 'Stock Screener',
            'description': 'Filter stocks by key metrics',
            'url': '/screener/'
        },
        {
            'name': 'Financial Reports & Statements',
            'description': 'Compare AI Summarized Reports for Companies and Quarters',
            'url': f"/reports/"
        },
        {
            'name': 'Financial Risks',
            'description': 'Compare AI Summarized Risks and historical changes from Companies Reports',
            'url': f"/risks/"
        }
    ]


def get_cached_price_data(date, timeframe):
    """Cache price data for frequently accessed dates and timeframes."""
    cache_key = f'price_data_{date.isoformat()}_{timeframe}'
    cached_data = cache.get(cache_key)

    if cached_data:
        return cached_data

    previous_date = get_previous_date(date, timeframe)

    # Optimize query by selecting only needed fields
    latest_prices = (PriceData.objects
    .filter(date=date)
    .select_related('security')
    .only('security__ticker', 'close_price', 'date')
    .annotate(
        previous_close=Subquery(
            PriceData.objects
            .filter(
                security_id=OuterRef('security_id'),
                date=previous_date
            )
            .values('close_price')[:1]
        )
    )
    .annotate(
        price_change=Case(
            When(
                previous_close__isnull=False,
                previous_close__gt=0,
                then=ExpressionWrapper(
                    (F('close_price') - F('previous_close')) / F('previous_close') * 100,
                    output_field=FloatField()
                )
            ),
            default=Value(0.0),
            output_field=FloatField(),
        )
    ))

    # Cache for 5 minutes (adjust as needed)
    cache.set(cache_key, latest_prices, 300)
    return latest_prices


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

    def format_mover(x):
        try:
            change = x.daily_change if x.daily_change is not None else 0.0
            price = x.close_price if x.close_price is not None else 0.0
            return {
                'symbol': x.security.ticker,
                'change': f"{change:+.2f}%",
                'price': f"${price:.2f}"
            }
        except Exception as e:
            # Provide default values if formatting fails
            return {
                'symbol': x.security.ticker,
                'change': "0.00%",
                'price': "$0.00"
            }

    return (
        [format_mover(g) for g in gainers],
        [format_mover(l) for l in losers]
    )


def get_previous_date(current_date, timeframe):
    """
    Calculate the reference date for price comparison based on timeframe.

    This handles edge cases like weekends and holidays by ensuring we get
    the most recent trading day before our target date.
    """
    if timeframe == 'D':
        target_date = current_date - timedelta(days=1)
    elif timeframe == 'W':
        target_date = current_date - timedelta(days=7)
    else:  # Monthly
        target_date = current_date - timedelta(days=30)

    # Get the most recent trading day not exceeding our target date
    return (PriceData.objects
    .filter(date__lte=target_date)
    .order_by('-date')
    .values('date')
    .first()['date'])


def get_latest_trading_data(timeframe='D'):
    """
    Get market data and calculate price changes based on the selected timeframe.
    Supports daily (D), weekly (W), and monthly (M) comparisons.
    """
    latest_data = (PriceData.objects
                   .select_related('security')
                   .order_by('-date')
                   .first())

    if not latest_data:
        return None, None, None

    latest_date = latest_data.date
    previous_date = get_previous_date(latest_date, timeframe)

    # Get price changes comparing current close to previous period's close
    latest_prices = (PriceData.objects
    .filter(date=latest_date)
    .select_related('security')
    .annotate(
        previous_close=Subquery(
            PriceData.objects
            .filter(
                security_id=OuterRef('security_id'),
                date=previous_date
            )
            .values('close_price')[:1]
        )
    )
    .annotate(
        daily_change=Case(
            When(
                previous_close__isnull=False,
                previous_close__gt=0,
                then=ExpressionWrapper(
                    (F('close_price') - F('previous_close')) / F('previous_close') * 100,
                    output_field=FloatField()
                )
            ),
            default=Value(0.0),
            output_field=FloatField(),
        )
    ))

    timeframe_text = {
        'D': 'Daily',
        'W': 'Weekly',
        'M': 'Monthly'
    }[timeframe]

    return latest_date, latest_prices, f"{timeframe_text} Change - {latest_date.strftime('%B %d, %Y')}"


def calculate_market_stats(prices_queryset):
    """Calculate market statistics with a single query."""
    cache_key = f'market_stats_{prices_queryset.query.__str__()}'
    cached_stats = cache.get(cache_key)

    if cached_stats:
        return cached_stats

    stats = prices_queryset.aggregate(
        gainers=Count(Case(When(price_change__gt=0, then=1))),
        losers=Count(Case(When(price_change__lt=0, then=1))),
        unchanged=Count(Case(When(price_change=0, then=1)))
    )

    total = sum(stats.values())

    market_breadth = {
        'gainers': stats['gainers'],
        'losers': stats['losers'],
        'unchanged': stats['unchanged'],
        'gainers_percentage': (stats['gainers'] / total * 100) if total > 0 else 0,
        'losers_percentage': (stats['losers'] / total * 100) if total > 0 else 0,
        'unchanged_percentage': (stats['unchanged'] / total * 100) if total > 0 else 0
    }

    cache.set(cache_key, market_breadth, 300)
    return market_breadth


def index(request):
    try:
        timeframe = request.GET.get('timeframe', 'D')
        if timeframe not in ['D', 'W', 'M']:
            timeframe = 'D'

        # Get latest date from cache or database
        latest_date_key = 'latest_trading_date'
        latest_date = cache.get(latest_date_key)

        if not latest_date:
            latest_data = PriceData.objects.valid().order_by('-date').first()
            if not latest_data:
                return render(request, 'index.html', {
                    'error': 'No valid price data available'
                })
            latest_date = latest_data.date
            cache.set(latest_date_key, latest_date, 300)

        # Get price data with caching
        latest_prices = get_cached_price_data(latest_date, timeframe)

        # Calculate market statistics
        market_breadth = calculate_market_stats(latest_prices)

        # Get top movers efficiently
        movers_cache_key = f'top_movers_{latest_date.isoformat()}_{timeframe}'
        top_movers = cache.get(movers_cache_key)

        if not top_movers:
            gainers = latest_prices.order_by('-price_change')[:5]
            losers = latest_prices.order_by('price_change')[:5]

            format_mover = lambda x: {
                'symbol': x.security.ticker,
                'change': f"{x.price_change:+.2f}%",
                'price': f"${x.close_price:.2f}"
            }

            top_movers = {
                'gainers': [format_mover(g) for g in gainers],
                'losers': [format_mover(l) for l in losers]
            }
            cache.set(movers_cache_key, top_movers, 300)

        period_map = {'D': 'Daily', 'W': 'Weekly', 'M': 'Monthly'}

        context = {
            'formatted_date': f"{period_map[timeframe]} Change - {latest_date.strftime('%B %d, %Y')}",
            'market_breadth': market_breadth,
            'top_gainers': top_movers['gainers'],
            'bottom_performers': top_movers['losers'],
            'analysis_tools': get_analysis_tools(),
            'api_base_url': settings.API_BASE_URL,
            'current_timeframe': timeframe
        }

        return render(request, 'index.html', context)

    except Exception as e:
        return render(request, 'index.html', {
            'error': f'Error loading market data: {str(e)}'
        })