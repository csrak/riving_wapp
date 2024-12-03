from django.core.cache import cache
from django.conf import settings

def get_analysis_cache_key(security_id, timerange):
    return f'stock_analysis:{security_id}:{timerange}'

def cache_analysis_data(security_id, timerange, data):
    cache_key = get_analysis_cache_key(security_id, timerange)
    cache.set(cache_key, data, timeout=settings.ANALYSIS_CACHE_TIMEOUT)

def get_cached_analysis_data(security_id, timerange):
    cache_key = get_analysis_cache_key(security_id, timerange)
    return cache.get(cache_key)
