import datetime
from django import template
from django.shortcuts import reverse
from agenda.models import Event


register = template.Library()


@register.simple_tag
def date_tag(year, month, day):
    if day and int(day) != 0:
        date = datetime.date(year=int(year), month=int(month), day=int(day))
        filtered_events = Event.objects.filter(initial_date__lte=date, end_date__gte=date)
        if filtered_events.count() > 0:
            return filtered_events
        else:
            return ""
    else:
        return ""


@register.simple_tag
def next_month_tag(year, month):
    date_aux = datetime.date(year=int(year), month=int(month), day=28) + datetime.timedelta(days=7)
    month_aux = date_aux.month
    year_aux = date_aux.year

    return reverse('agenda:show_specific_calendar', kwargs={'year': year_aux, 'month': month_aux})


@register.simple_tag
def previous_month_tag(year, month):
    date_aux = datetime.date(year=int(year), month=int(month), day=1) - datetime.timedelta(days=1)

    month_aux = date_aux.month
    year_aux = date_aux.year

    return reverse('agenda:show_specific_calendar', kwargs={'year': year_aux, 'month': month_aux})


@register.simple_tag
def next_year_tag(year):
    date_aux = datetime.date(year=int(year), month=12, day=31) + datetime.timedelta(days=1)
    year_aux = date_aux.year

    return reverse('agenda:show_specific_calendar_year', kwargs={'year': year_aux})


@register.simple_tag
def previous_year_tag(year):
    date_aux = datetime.date(year=int(year), month=1, day=1) - datetime.timedelta(days=1)
    year_aux = date_aux.year

    return reverse('agenda:show_specific_calendar_year', kwargs={'year': year_aux})


@register.simple_tag
def next_day_tag(year, month, day):
    date_aux = datetime.date(year=int(year), month=int(month), day=int(day)) + datetime.timedelta(days=1)

    day_aux = date_aux.day
    month_aux = date_aux.month
    year_aux = date_aux.year

    return reverse('agenda:show_specific_calendar_day', kwargs={'year': year_aux, 'month': month_aux, 'day': day_aux})


@register.simple_tag
def previous_day_tag(year, month, day):
    date_aux = datetime.date(year=int(year), month=int(month), day=int(day)) - datetime.timedelta(days=1)

    day_aux = date_aux.day
    month_aux = date_aux.month
    year_aux = date_aux.year

    return reverse('agenda:show_specific_calendar_day', kwargs={'year': year_aux, 'month': month_aux, 'day': day_aux})
