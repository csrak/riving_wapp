# fin_data_cl.utils.search_view.py

from django.shortcuts import render
from fin_data_cl.models import FinancialReport, RiskComparison
from fin_data_cl.utils.fin_data_ops import FinancialRepository
from fin_data_cl.utils.session_utils import FinancialSessionManager
from django.contrib import messages
from django.urls import reverse
from django.template.loader import render_to_string
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


def generalized_search_view(request, model, form_class, template_name, extra_context=None):
    """Generic view for financial data comparison, fully rewritten for clarity."""

    # Initialize repositories and session managers for left and right forms
    repository = FinancialRepository(model)
    sides = ['left', 'right']
    session_managers = {side: FinancialSessionManager(request, side) for side in sides}

    # Retrieve initial data from the session for each side
    session_data = {side: session_managers[side].get_from_session() for side in sides}
    logger.debug(f"Initial session data: {session_data}")

    # Initialize forms for each side with session data or POST data
    forms = {
        side: form_class(
            data=request.POST if request.method == 'POST' and f'{side}-form' in request.POST.get('form_id',
                                                                                                 '') else None,
            initial=session_data[side],
            prefix=side
        ) for side in sides
    }

    # Initialize reports for each side (initially None)
    reports = {side: None for side in sides}

    # If there's a POST request, process the specific side's form
    if request.method == 'POST':
        form_id = request.POST.get('form_id', '')
        side = 'left' if 'left' in form_id else 'right'
        logger.debug(f"Processing POST for form_id: {form_id} (Side: {side})")

        form = forms[side]
        if form.is_valid():
            # Extract cleaned data from the form
            data = form.cleaned_data
            logger.debug(f"Form {side.capitalize()} cleaned data: {data}")

            # Save current form data to the session for persistence
            session_managers[side].save_to_session(
                data['exchange'].id,
                data['security'].id,
                data['year'],
                data['month']
            )

            # Retrieve report data based on cleaned form data
            security_id = data['security'].id
            year = int(data['year'])
            month = int(data['month'])
            logger.debug(f"Attempting to retrieve report for Security ID: {security_id}, Year: {year}, Month: {month}")

            reports[side] = repository.get_by_criteria(security_id, year, month)
            logger.debug(f"Retrieved {side.capitalize()} Report: {reports[side]}")

            if not reports[side]:
                messages.warning(request, f"No {side}-side report found for the selected criteria.")
        else:
            logger.debug(f"Form {side.capitalize()} validation failed. Errors: {form.errors}")

    # Use session data for initial reports if no valid report was found during POST
    for side in sides:
        if reports[side] is None and all(session_data[side].values()):
            logger.debug(f"Using session data to retrieve {side.capitalize()} report: {session_data[side]}")
            reports[side] = repository.get_by_criteria(
                session_data[side]['security'],
                int(session_data[side]['year']),
                int(session_data[side]['month'])
            )
            logger.debug(f"Initial {side.capitalize()} Report from session: {reports[side]}")

    # Prepare context data for rendering the template
    sections = {side: [] for side in sides}
    for side in sides:
        if reports[side]:
            sections[side] = [
                {
                    'id': 'Overview',
                    'title': 'New Risks',
                    'items': reports[side].new_risks if hasattr(reports[side], 'new_risks') else []
                },
                {
                    'id': 'Risks',
                    'title': 'Old Risks',
                    'items': reports[side].old_risks if hasattr(reports[side], 'old_risks') else []
                },
                {
                    'id': 'Changes',
                    'title': 'Risk Changes',
                    'items': reports[side].modified_risks if hasattr(reports[side], 'modified_risks') else []
                }
            ]
            logger.debug(f"{side.capitalize()} Sections for Report: {sections[side]}")

    # Prepare the complete context for rendering the page
    context = {
        'form_left': forms['left'],
        'form_right': forms['right'],
        'report_left': reports['left'],
        'report_right': reports['right'],
        'page_title': 'Financial Reports' if model == FinancialReport else 'Risk Comparison',
        'form_titles': {
            'left': 'Report #1',
            'right': 'Report #2'
        },
        'left_sections': sections['left'],
        'right_sections': sections['right'],
    }

    # Merge extra context if provided
    if extra_context:
        context.update(extra_context)

    # Handle AJAX request to dynamically update report section
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        logger.debug(f"Processing AJAX request for form_id: {form_id}")

        try:
            side = 'left' if 'left' in form_id else 'right'
            sections_to_render = sections[side]

            report_html = render_to_string(
                "fin_data_cl/financial_risks_accordion.html",
                context={
                    'side': side.capitalize(),
                    'sections': sections_to_render
                }
            )
            logger.debug(
                f"Generated HTML for {side.capitalize()} Report (AJAX): {report_html[:200]}...")  # Log first 200 chars
            return JsonResponse({'html': report_html})
        except Exception as e:
            logger.error(f"Error while rendering AJAX report HTML: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'An error occurred while rendering the report.'}, status=500)

    # Render the page with the context data
    return render(request, template_name, context)
