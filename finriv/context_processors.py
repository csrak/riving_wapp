def google_analytics(request):
    """
    Add the Google Analytics tracking ID to the context of all templates.
    """
    from django.conf import settings
    ga_id = getattr(settings, 'GOOGLE_ANALYTICS_ID', '')
    return {
        'GOOGLE_ANALYTICS_ID': ga_id
    }