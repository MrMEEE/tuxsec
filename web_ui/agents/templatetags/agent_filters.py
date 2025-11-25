"""Custom template filters for the agents app."""
import json
from django import template

register = template.Library()


@register.filter(name='pprint')
def pprint(value):
    """Pretty print JSON data."""
    if value is None:
        return ''
    try:
        return json.dumps(value, indent=2, sort_keys=True)
    except (TypeError, ValueError):
        return str(value)
