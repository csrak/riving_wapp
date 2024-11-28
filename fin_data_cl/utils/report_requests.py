from django.shortcuts import render
from django.contrib import messages
from django.db.models import Model

def get_object_by_criteria(model, ticker, year, month):
    """Fetches an object from the database based on ticker, year, and month."""
    try:
        return model.objects.get(ticker=ticker, year=year, month=month)
    except model.DoesNotExist:
        return None

def save_to_session(request, prefix, ticker, year, month):
    """Saves the search criteria to the session."""
    request.session[f'{prefix}-ticker'] = ticker
    request.session[f'{prefix}-year'] = year
    request.session[f'{prefix}-month'] = month

def get_from_session(request, prefix):
    """Retrieves search criteria from the session."""
    return {
        'ticker': request.session.get(f'{prefix}-ticker'),
        'year': request.session.get(f'{prefix}-year'),
        'month': request.session.get(f'{prefix}-month')
    }

def generalized_search_view(request, model: Model, form_class, template_name: str):
    """
    A generalized search view for models with ticker, year, and month as keys.

    Args:
        request: The HTTP request object.
        model: The model class to query.
        form_class: The form class for the search form.
        template_name: The name of the template to render.
    """
    # Fetch previous reports from the session
    report_left = get_object_by_criteria(
        model,
        ticker=request.session.get('left-ticker'),
        year=request.session.get('left-year'),
        month=request.session.get('left-month')
    ) if 'left-ticker' in request.session else None

    report_right = get_object_by_criteria(
        model,
        ticker=request.session.get('right-ticker'),
        year=request.session.get('right-year'),
        month=request.session.get('right-month')
    ) if 'right-ticker' in request.session else None

    # Initialize forms with session data if no new POST request for them
    form_left = form_class(initial=get_from_session(request, 'left'), prefix='left')
    form_right = form_class(initial=get_from_session(request, 'right'), prefix='right')

    if request.method == 'POST':
        if 'left' in request.POST.get('form_id', ''):
            form_left = form_class(request.POST, prefix='left')
            if form_left.is_valid():
                ticker = form_left.cleaned_data['ticker']
                year = form_left.cleaned_data['year']
                month = form_left.cleaned_data['month']
                report_left = get_object_by_criteria(model, ticker, year, month)
                save_to_session(request, 'left', ticker, year, month)
                if not report_left:
                    messages.warning(request, "No left-side report found for the selected criteria.")
        elif 'right' in request.POST.get('form_id', ''):
            form_right = form_class(request.POST, prefix='right')
            if form_right.is_valid():
                ticker = form_right.cleaned_data['ticker']
                year = form_right.cleaned_data['year']
                month = form_right.cleaned_data['month']
                report_right = get_object_by_criteria(model, ticker, year, month)
                save_to_session(request, 'right', ticker, year, month)
                if not report_right:
                    messages.warning(request, "No right-side report found for the selected criteria.")

    # Pass the reports and forms to the template
    context = {
        'form_left': form_left,
        'form_right': form_right,
        'report_left': report_left,
        'report_right': report_right,
    }
    return render(request, template_name, context)