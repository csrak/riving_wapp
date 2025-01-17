from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.template.exceptions import TemplateDoesNotExist
from django.conf import settings
import logging
logger = logging.getLogger(__name__)

def generic_data_view(request, template_name):
    """
    Generic view for serving templates with environment-aware error handling.
    Production environments will show user-friendly error pages while
    development environments will show detailed debug information.
    """
    context = {
        'api_base_url': '/api/v1/',
        'debug': settings.DEBUG,
    }

    try:
        return render(request, f'{template_name}.html', context)

    except TemplateDoesNotExist:
        # Log the error
        logger.warning(
            f"Template '{template_name}.html' not found. "
            f"Requested by user: {request.user}, "
            f"IP: {request.META.get('REMOTE_ADDR')}"
        )

        if settings.DEBUG:
            # In development, show detailed error
            return render(request, f'{template_name}.html', context)
        else:
            # In production, show generic "In Construction" page
            return render(request, 'errors/in_construction.html', context, status=404)

    except Exception as e:
        # Log the error with full traceback
        logger.error(
            f"Error rendering template '{template_name}.html'",
            exc_info=True,
            extra={
                'request': request,
                'template': template_name,
            }
        )

        if settings.DEBUG:
            # Re-raise the exception in development for full traceback
            raise
        else:
            # In production, show generic error page
            return render(
                request,
                'errors/500.html',
                context,
                status=500
            )


def _get_available_templates():
    """
    Helper function to list available templates for debug view.
    Only called in development when a template is not found.
    """
    from django.template.loader import get_template
    from django.template.loaders.app_directories import get_app_template_dirs
    import os

    template_dirs = get_app_template_dirs('templates')
    available_templates = []

    for template_dir in template_dirs:
        for root, _, files in os.walk(template_dir):
            for file in files:
                if file.endswith('.html'):
                    template_path = os.path.join(
                        root.replace(str(template_dir), '').lstrip('/'),
                        file
                    )
                    available_templates.append(template_path)

    return sorted(available_templates)