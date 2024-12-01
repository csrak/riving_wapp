from django.shortcuts import render
from fin_data_cl.models import FinancialReport, RiskComparison
from fin_data_cl.utils.fin_data_ops import FinancialRepository
from fin_data_cl.utils.session_utils import FinancialSessionManager
from django.contrib import messages


def generalized_search_view(request, model, form_class, template_name):
    """Generic view for financial data comparison."""
    repository = FinancialRepository(model)

    # Initialize session managers for both sides
    left_session = FinancialSessionManager(request, 'left')
    right_session = FinancialSessionManager(request, 'right')

    # Get initial data from session
    left_data = left_session.get_from_session()
    right_data = right_session.get_from_session()

    # Initialize forms with session data or POST data
    form_left = form_class(
        data=request.POST if 'left' in request.POST.get('form_id', '') else None,
        initial=left_data,
        prefix='left'
    )
    form_right = form_class(
        data=request.POST if 'right' in request.POST.get('form_id', '') else None,
        initial=right_data,
        prefix='right'
    )

    # Initialize reports
    report_left = None
    report_right = None

    if request.method == 'POST':
        if 'left' in request.POST.get('form_id', ''):
            if form_left.is_valid():
                data = form_left.cleaned_data
                left_session.save_to_session(
                    data['exchange'].id,
                    data['security'].id,
                    data['year'],
                    data['month']
                )
                report_left = repository.get_by_criteria(
                    data['security'].id,
                    data['year'],
                    data['month']
                )
                if not report_left:
                    messages.warning(request, "No left-side report found for the selected criteria.")

        elif 'right' in request.POST.get('form_id', ''):
            if form_right.is_valid():
                data = form_right.cleaned_data
                right_session.save_to_session(
                    data['exchange'].id,
                    data['security'].id,
                    data['year'],
                    data['month']
                )
                report_right = repository.get_by_criteria(
                    data['security'].id,
                    data['year'],
                    data['month']
                )
                if not report_right:
                    messages.warning(request, "No right-side report found for the selected criteria.")

    # Use session data for initial reports if not set by POST
    if report_left is None and all(left_data.values()):
        report_left = repository.get_by_criteria(
            left_data['security'],
            left_data['year'],
            left_data['month']
        )

    if report_right is None and all(right_data.values()):
        report_right = repository.get_by_criteria(
            right_data['security'],
            right_data['year'],
            right_data['month']
        )

    context = {
        'form_left': form_left,
        'form_right': form_right,
        'report_left': report_left,
        'report_right': report_right,
        # Additional context for template rendering
        'page_title': 'Financial Reports' if model == FinancialReport else 'Risk Comparison',
        'form_titles': {
            'left': 'Report #1',
            'right': 'Report #2'
        }
    }

    return render(request, template_name, context)