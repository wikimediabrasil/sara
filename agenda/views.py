import calendar
import datetime
from django.db import transaction
from django.contrib import messages
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.db.models import Q
from django.conf import settings
from agenda.forms import EventForm
from agenda.models import Event
from users.models import TeamArea, UserProfile, Position


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
    days_month = days_of_the_month(int(year), int(month))
    month_name = _(calendar.month_name[int(month)])

    context = {"calendar": days_month, "month": month, "month_name": month_name, "year": year, "title": _("Calendar %(month_name)s/%(year)s") % {"month_name": month_name, "year": year}}
    return render(request, "agenda/calendar.html", context)


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
    day_aux = day
    month_aux = month
    year_aux = year
    month_name = _(calendar.month_name[int(month)])

    context = {"month_name": month_name, "year": year_aux, "month": month_aux, "day": day_aux, "title": _("Calendar %(day)s/%(month_name)s/%(year)s") % {"day": day_aux, "month_name": month_name, "year": year}}
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

    context = {"eventform": event_form, "title": _("Add event")}
    return render(request, "agenda/add_event.html", context)


# READ
def list_events(request):
    events = Event.objects.all().order_by("-initial_date__year")
    context = {"dataset": events, "title": _("List events")}
    return render(request, "agenda/list_events.html", context)


def detail_event(request, event_id):
    event = Event.objects.get(pk=event_id)
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

    context = {"eventform": event_form, "event_id": event_id, "title": _("Update event %(event_id)s") % {"event_id": event_id}}
    return render(request, "agenda/update_event.html", context)


# SEND EMAIL ABOUT EVENT
def send_email(request):
    html_template_path = "agenda/email_template.html"

    areas = TeamArea.objects.filter(team_area_of_position__type__name="Manager")
    for area in areas:
        manager = UserProfile.objects.filter(user__is_active=True, position__area_associated=area, position__type__name="Manager").first()
        manager_email = manager.user.email

        if manager_email:
            upcoming_reports = get_activities_soon_to_be_finished(area)
            late_reports = get_activities_already_finished(area)
            about_to_kickoff = get_activities_about_to_kickoff(area)

            context_data = {
                "late_reports": build_message_about_reports(late_reports),
                "upcoming_reports": build_message_about_reports(upcoming_reports),
                "about_to_kickoff": build_message_about_reports(about_to_kickoff),
                "manager": manager,
                "area": area
            }

            if upcoming_reports or late_reports or about_to_kickoff:
                email_html_template = get_template(html_template_path).render(context_data)

                email_msg = EmailMessage(
                    subject = _("SARA Report- %(area)s") % {"area": area},
                    body = email_html_template,
                    from_email = settings.EMAIL_HOST_USER,
                    to = [manager_email],
                    reply_to = [settings.EMAIL_HOST_USER],
                    bcc = [settings.EMAIL_COORDINATOR]
                )
                email_msg.content_subtype = "html"
                email_msg.send(fail_silently=False)
        else:
            pass
    return redirect(reverse("metrics:index"))


def show_list_of_reports_of_specific_area(request, area_id=None):
    if not area_id:
        user = request.user
        area = TeamArea.objects.get(team_area_of_position__user_position__user=user)
        manager = user.first_name
    else:
        area = TeamArea.objects.get(pk=area_id)
        manager = UserProfile.objects.filter(user__is_active=True, position__area_associated=area, position__type__name="Manager").first()

    today_boy = (datetime.date.today() - datetime.date(datetime.date.today().year, 1, 1)).days
    today_eoy = (datetime.date(datetime.date.today().year, 12, 31) - datetime.date.today()).days
    no_report = Q()
    past_activities = get_activities_already_finished(area, delta=today_boy, no_report=no_report)
    future_activities = get_activities_soon_to_be_finished(area, delta=today_eoy)

    context = {
        "past_activities": build_message_about_reports(past_activities),
        "future_activities": build_message_about_reports(future_activities),
        "manager": manager,
        "area": area
    }

    return render(request, "agenda/area_activities.html", context)


def show_list_of_reports_of_area(request):
    return redirect(reverse("agenda:specific_area_activities"))


def get_activities_soon_to_be_finished(area, delta=14):
    today = datetime.date.today()
    interval = min(today + datetime.timedelta(delta), datetime.date(today.year, 12, 31))
    query = Q(end_date__lte=interval, # Before the interval
              end_date__gte=today, # After today
              area_responsible=area, # Under a specific manager responsability
              )
    events = Event.objects.filter(query)
    return events


def get_activities_already_finished(area, delta=28, no_report=Q(activity_associated__report_activity__isnull=True)):
    today = datetime.date.today()
    interval = max(today - datetime.timedelta(delta), datetime.date(today.year, 1, 1))
    query = Q(end_date__lte=today - datetime.timedelta(1), # Before today
              end_date__gte=interval, # After the interval
              area_responsible=area, # Under a specific manager responsability
              ) & no_report
    events = Event.objects.filter(query).distinct()
    return events


def get_activities_about_to_kickoff(area, delta=14):
    today = datetime.date.today()
    interval = min(today + datetime.timedelta(delta), datetime.date(today.year, 12, 31))
    query = Q(initial_date__gte=today, # Begining after today
              initial_date__lte=interval, # Begining before interval
              area_responsible=area # Under a specific manager responsability
              )
    events = Event.objects.filter(query)
    return events


def build_message_about_reports(events):
    message = ""

    for event in events:
        if event.end_date == event.initial_date:
            date_string = event.initial_date.strftime("%d/%m")
        else:
            date_string = event.initial_date.strftime("%d/%m") + " - " + event.end_date.strftime("%d/%m")

        message += _("<li><a href='https://sara-wmb.toolforge.org/calendar/%(year)s/%(month)s/%(day)s'>%(name)s (%(date_string)s)</a></li>") % {
            "year": event.initial_date.year,
            "month": event.initial_date.month,
            "day": event.initial_date.day,
            "name": event.name,
            "date_string": date_string}

    if message:
        message = "<ul>\n" + message + "</ul>"

    return message
