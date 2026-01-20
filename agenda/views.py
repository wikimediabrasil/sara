import calendar
import datetime
from datetime import date, timedelta
from django.db import transaction
from django.contrib import messages
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.translation import gettext as _
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

from users.models import TeamArea, UserProfile
from agenda.models import Event
from agenda.forms import EventForm
from agenda.services import send_event_reports, build_message_about_reports


# YEAR CALENDAR
def show_calendar_year(request):
    """
    Redirects to the calendar view for the current year.

    :param request: The HTTP request object.
    :return: HttpResponseRedirect: Redirects to the 'show_specific_year_calendar' view.
    """
    year = datetime.datetime.now().year

    return redirect('agenda:show_specific_calendar_year', year=year)


def show_specific_calendar_year(request, year):
    """
    Shows calendar for specific year.

    :param request: The HTTP request object.
    :param year: Year of the calendar.
    :return: HttpResponse: Renders a calendar spreadsheet
    """
    year = int(year)
    days_year = []
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    all_events = (Event.objects.filter(Q(initial_date__lte=end) & Q(end_date__gte=start))
                  .select_related("area_responsible")
                  .order_by("initial_date", "end_date"))

    events_by_date = {}
    for event in all_events:
        current = max(event.initial_date, start)
        last = min(event.end_date, end)
        while current <= last:
            key = current.strftime("%Y-%m-%d")
            events_by_date.setdefault(key, []).append(event)
            current += timedelta(days=1)

    for month in range(1, 13):
        month_name = _(calendar.month_name[int(month)])
        days_month = days_of_the_month(year, int(month))
        filled_days = []
        for week in days_month:
            filled_week = []
            for day in week:
                if day:
                    key = f"{year}-{month:02d}-{day:02d}"
                    filled_week.append({
                        "day": day,
                        "activities": events_by_date.get(key, []),
                    })
                else:
                    filled_week.append(None)
            filled_days.append(filled_week)

        days_year.append({
            "month_name": month_name,
            "month": month,
            "days": filled_days,
        })

    context = {"calendar": days_year, "year": year, "title": _("Calendar %(year)s") % {"year": year}}
    return render(request, "agenda/calendar_year.html", context)


# MONTH CALENDAR
def show_calendar(request):
    """
    Redirects to the calendar view for the current month and year.

    :param request: The HTTP request object.
    :return: HttpResponseRedirect: Redirects to the 'show_specific_calendar' view.
    """
    month = datetime.datetime.now().month
    year = datetime.datetime.now().year

    return redirect('agenda:show_specific_calendar', year=year, month=month)


def show_specific_calendar(request, year, month):
    """
    Shows calendar for specific month and year.

    :param request: The HTTP request object.
    :param year: Year of the calendar.
    :param month: Month of the calendar.
    :return: HttpResponse: Renders a calendar spreadsheet
    """
    year = int(year)
    month = int(month)

    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day)

    all_events = (Event.objects.filter(Q(initial_date__lte=end) & Q(end_date__gte=start))
                  .select_related("area_responsible")
                  .order_by("initial_date", "end_date"))
    events_by_date = {}
    for event in all_events:
        current = max(event.initial_date, start)
        last = min(event.end_date, end)
        while current <= last:
            key = current.strftime("%Y-%m-%d")
            events_by_date.setdefault(key, []).append(event)
            current += timedelta(days=1)

    days_month = days_of_the_month(year, month)
    filled_days = []
    for week in days_month:
        filled_week = []
        for day in week:
            if day:
                key = f"{year}-{month:02d}-{day:02d}"
                filled_week.append({
                    "day": day,
                    "activities": events_by_date.get(key, []),
                })
            else:
                filled_week.append(None)
        filled_days.append(filled_week)

    month_name = _(calendar.month_name[month])
    context = {
        "month_name": month_name,
        "month": month,
        "year": year,
        "calendar": filled_days,
        "title": _("Calendar %(month)s/%(year)s") % {"month": month_name, "year": year}
    }
    return render(request, "agenda/calendar_month.html", context)


# DAY CALENDAR
def show_calendar_day(request):
    """
    Shows calendar for specific month and year.

    :param request: The HTTP request object.
    :return: HttpResponseRedirect: Redirects to the 'show_specific_calendar_day' view.
    """
    day = datetime.datetime.now().day
    month = datetime.datetime.now().month
    year = datetime.datetime.now().year

    return redirect("agenda:show_specific_calendar_day", year=year, month=month, day=day)


def show_specific_calendar_day(request, year, month, day):
    """
    Shows calendar for specific day, month and year.

    :param request:
    :param year: Year of the calendar.
    :param month: Month of the calendar.
    :param day: Day of the calendar.
    :return: HttpResponse: Renders a calendar spreadsheet
    """
    year = int(year)
    month = int(month)
    day = int(day)

    current_day = date(year, month, day)

    month_name = _(calendar.month_name[month])

    all_events = (Event.objects.filter(Q(initial_date__lte=current_day) & Q(end_date__gte=current_day))
                  .select_related("area_responsible")
                  .order_by("initial_date", "end_date"))

    context = { "year": year, "month": month, "day": day, "month_name": month_name, "activities": all_events, "title": _("Calendar %(day)s/%(month_name)s/%(year)s") % {"day": day, "month_name": month_name, "year": year}}
    return render(request, "agenda/calendar_day.html", context)


def days_of_the_month(year, month):
    """
    Creates an array with the days of the month.

    :param year: Year of the calendar.
    :param month: Month of the calendar.
    :return: Array: The days of the month as an array, divided into weeks.
    """
    return calendar.monthcalendar(int(year), int(month))


# CREATE
@login_required
@transaction.atomic
def add_event(request):
    form_valid_message = _("Changes done successfully!")
    form_invalid_message = _("Something went wrong!")

    if request.method == "POST":
        event_form = EventForm(request.POST)

        if event_form.is_valid():
            event_form.save()

            messages.success(request, form_valid_message)
            return redirect(reverse("agenda:list_events"))
        else:
            messages.error(request, form_invalid_message)

    else:
        event_form = EventForm()

    context = {"event_form": event_form, "title": _("Add event")}
    return render(request, "agenda/add_event.html", context)


# READ
def list_events(request):
    events = Event.objects.all().order_by("-initial_date__year")
    context = {"dataset": events, "title": _("List events")}
    return render(request, "agenda/list_events.html", context)


def detail_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    context = {"event": event}
    return render(request, "agenda/detail_event.html", context)


@login_required
@transaction.atomic
def delete_event(request, event_id):
    event = Event.objects.get(pk=event_id)
    context = {"event": event, "title": _("Delete event %(event_id)s") % {"event_id": event_id}}

    if request.method == "POST":
        event.delete()
        return redirect(reverse('agenda:list_events'))

    return render(request, 'agenda/delete_event.html', context)


@login_required
@transaction.atomic
def update_event(request, event_id):
    form_valid_message = _("Changes done successfully!")
    form_invalid_message = _("Something went wrong!")
    event = get_object_or_404(Event, pk=event_id)

    if request.method == "POST":
        event_form = EventForm(request.POST or None, instance=event)
        year = datetime.datetime.today().year
        month = datetime.datetime.today().month

        if event_form.is_valid():
            event_form.save()
            messages.success(request, form_valid_message)
            year = event_form.instance.initial_date.year
            month = event_form.instance.initial_date.month
        else:
            messages.error(request, form_invalid_message)

        return redirect("agenda:show_specific_calendar", year=year, month=month)
    else:
        event_form = EventForm(instance=event)

    context = {"event_form": event_form, "event_id": event_id, "title": _("Update event %(event_id)s") % {"event_id": event_id}}
    return render(request, "agenda/update_event.html", context)


def send_email(request):
    if send_event_reports:
        send_event_reports()
    return redirect(reverse("metrics:index"))


def list_of_reports_of_area(code="", user=None):
    if code:
        try:
            area = TeamArea.objects.get(code=code)
            manager = UserProfile.objects.filter(
                user__is_active=True,
                position__area_associated=area,
                position__type__name="Manager").first()
        except ObjectDoesNotExist:
            return False
    else:
        try:
            area = user.profile.position.area_associated
            manager = user.first_name
        except AttributeError:
            return False

    today = datetime.date.today()
    days_since_jan_01 = (today - datetime.date(today.year, 1, 1)).days
    days_until_dec_31 = (datetime.date(today.year, 12, 31) - today).days

    context = {
        "past_activities": build_message_about_reports(
            get_activities_already_finished(area, delta=days_since_jan_01)
        ),
        "future_activities": build_message_about_reports(
            get_activities_soon_to_be_finished(area, delta=days_until_dec_31)
        ),
        "manager": manager,
        "area": area
    }

    return context


@permission_required("report.add_report")
def show_list_of_reports_of_area(request):
    context = list_of_reports_of_area("", request.user)
    if context:
        return render(request, "agenda/area_activities.html", context)
    else:
        return redirect(reverse("metrics:index"))


@permission_required("report.add_report")
def show_list_of_reports_of_specific_area(request, code=""):
    context = list_of_reports_of_area(code)
    if context:
        return render(request, "agenda/area_activities.html", context)
    else:
        return redirect(reverse("metrics:index"))


def get_activities_soon_to_be_finished(area, delta=14):
    today = datetime.date.today()
    interval = min(today + timedelta(delta), datetime.date(today.year, 12, 31))
    query = Q(end_date__lte=interval, # Before the interval
              end_date__gte=today, # After today
              area_responsible=area, # Under a specific manager responsibility
              )
    events = Event.objects.filter(query)
    return events


def get_activities_already_finished(area, delta=28):
    today = datetime.date.today()
    interval = max(today - timedelta(delta), datetime.date(today.year, 1, 1))
    query = Q(end_date__lte=today - timedelta(1), # Before today
              end_date__gte=interval, # After the interval
              area_responsible=area, # Under a specific manager responsibility
              )
    events = Event.objects.filter(query).distinct()
    return events


def get_activities_about_to_kickoff(area, delta=14):
    today = datetime.date.today()
    interval = min(today + timedelta(delta), datetime.date(today.year, 12, 31))
    query = Q(initial_date__gte=today, # Beginning after today
              initial_date__lte=interval, # Beginning before interval
              area_responsible=area # Under a specific manager responsibility
              )
    events = Event.objects.filter(query)
    return events
