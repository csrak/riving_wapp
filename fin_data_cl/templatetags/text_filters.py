from django import template
import re
import markdown

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
