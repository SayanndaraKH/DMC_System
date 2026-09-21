from django import template

register = template.Library()

@register.filter
def status_badge_class(status):
    classes = {
        'DRAFT': 'bg-secondary text-white',
        'PENDING_ADMIN': 'bg-warning text-dark',
        'PENDING_LEADERSHIP': 'bg-primary text-white',
        'ANNOTATED': 'bg-info text-dark',
        'ROUTED': 'bg-purple text-white',
        'IN_PROGRESS': 'bg-indigo text-white',
        'COMPLETED': 'bg-success text-white',
        'REJECTED': 'bg-danger text-white',
    }
    return classes.get(status, 'bg-secondary text-white')

@register.filter
def urgency_badge_class(urgency):
    classes = {
        'NORMAL': 'badge-normal',
        'URGENT': 'badge-urgent',
        'MOST_URGENT': 'badge-most-urgent',
    }
    return classes.get(urgency, 'badge-normal')

@register.filter
def secrecy_badge_class(secrecy):
    classes = {
        'NORMAL': 'bg-light text-dark border',
        'CONFIDENTIAL': 'bg-warning text-dark',
        'MOST_CONFIDENTIAL': 'bg-danger text-white',
    }
    return classes.get(secrecy, 'bg-light text-dark')

@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def format_date_dmy(val):
    """
    Standardizes any date value (date object or Khmer/Arabic string)
    into strictly 'DD-MM-YYYY' format (e.g. '27-07-1980').
    """
    if not val:
        return '-'
    from dms.views import _format_khmer_date_standard
    return _format_khmer_date_standard(val) or '-'
