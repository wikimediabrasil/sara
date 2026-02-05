from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.filter
def categorize(a, b):
    if isinstance(a, bool) and not a:
        return "-"
    try:
        return min(int(a / (0.25 * b)) + 1, 5)
    except (TypeError, ValueError, ZeroDivisionError):
        return "-"


@register.filter
def perc(a, b):
    if isinstance(a, bool) and not a:
        return "-"
    try:
        return "{:.0f}%".format(100 * a / b)
    except (TypeError, ValueError, ZeroDivisionError):
        return "-"


@register.filter
def bool_yesnopartial(a, b=False):
    if isinstance(a, bool):
        if not b:
            return _("Part.") if a else _("No")
        else:
            return _("Yes")
    else:
        return a


@register.filter
def bool_yesno(a):
    if isinstance(a, bool):
        return _("Yes") if a else _("No")
    else:
        return a


@register.filter
def is_yesno(a):
    if isinstance(a, bool):
        return True
    else:
        return False
