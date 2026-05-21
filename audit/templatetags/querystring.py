from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def qs(context, **kwargs):
    query = context['request'].GET.copy()
    for k, v in kwargs.items():
        if v is None and k in query:
            del query[k]
        else:
            query[k] = v

    return query.urlencode()
