from django import template
import re
import markdown
import ast
import json

register = template.Library()

@register.filter(name='format_subsection')
def format_subsection(value):
    formatted_value = value.replace('Business Overview', '')
    formatted_value = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted_value)
    formatted_value = re.sub(r'\#\#(.*?)\#\#', r'<strong>\1</strong>', formatted_value)
    formatted_value = formatted_value.replace('<strong></strong>', '')#get rid of any text, for now only buss overview that creates empty lines
    print(repr(formatted_value))
    formatted_value=formatted_value.strip()
    formatted_value = formatted_value.replace('\n', '<br>')
    formatted_value = formatted_value.replace('<strong></strong>', '')
    print(repr(formatted_value))
    #Step 4: Format general subtitles (anything between ** ... **) in bold

    #formatted_value = markdown.markdown(value)
    return formatted_value


@register.filter
def format_risks(value):
    """
    Formats risks from JSONField, handling different possible input types
    """
    # Handle None
    if value is None:
        return []

    # If already a list, return as-is
    if isinstance(value, list):
        return value

    # Try parsing as JSON string
    try:
        parsed_value = json.loads(value)
        if isinstance(parsed_value, list):
            return parsed_value
        return [parsed_value]
    except (TypeError, json.JSONDecodeError):
        # If not JSON, convert to list
        return [str(value)]