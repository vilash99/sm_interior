import json
from django import template

register = template.Library()


@register.filter
def has_access(user, arg: str) -> bool:
    """
    Usage in templates:
        {% if user|has_access:'doctors:view' %}
        {% if user|has_access:'letters' %}              # defaults to 'view'
        {% if user|has_access:'admin:full' %}

    arg format: 'page_code:access_type'  (access_type optional, defaults to 'view')
    """
    if not getattr(user, 'is_authenticated', False):
        return False

    if ':' in arg:
        page_code, access_type = arg.split(':', 1)
    else:
        page_code, access_type = arg, 'view'

    # Uses your User.has_page_access method
    return user.has_page_access(page_code, access_type)


@register.filter
def get_item(mapping, key):
    """
    Safely do mapping[key] in templates.
    """
    if mapping is None or key is None:
        return None
    try:
        return mapping.get(key)
    except AttributeError:
        return None

@register.filter
def pretty_json(value):
    try:
        return json.dumps(value, indent=2, ensure_ascii=False)
    except Exception:
        return value
