import calendar
import datetime
from datetime import timedelta
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from agenda.models import Event
from agenda.services import build_message_about_reports, send_event_reports
from users.models import TeamArea, UserProfile


def days_of_the_month(year, month):
    """
    Creates an array with the days of the month.

    :param year: Year of the calendar.
    :param month: Month of the calendar.
    :return: Array: The days of the month as an array, divided into weeks.
    """
    return calendar.monthcalendar(int(year), int(month))


def events_by_date_map(start, end):
    """
    Builds a mapping of "YYYY-MM-DD" -> list of events that occur on that date,
    for every event overlapping the [start, end] interval.

    :param start: First date of the interval (inclusive).
    :param end: Last date of the interval (inclusive).
    :return: dict: Events grouped by the date (as string) they occur on.
    """
    all_events = (
        Event.objects.filter(Q(initial_date__lte=end) & Q(end_date__gte=start))
        .select_related("area_responsible")
        .order_by("initial_date", "end_date")
    )

    events_by_date = {}
    for event in all_events:
        current = max(event.initial_date, start)
        last = min(event.end_date, end)
        while current <= last:
            key = current.strftime("%Y-%m-%d")
            events_by_date.setdefault(key, []).append(event)
            current += timedelta(days=1)

    return events_by_date


def build_filled_days(days_month, year, month, events_by_date):
    """
    Fills each day of a month calendar grid with its scheduled activities.

    :param days_month: Weeks/days grid, as returned by days_of_the_month.
    :param year: Year of the calendar.
    :param month: Month of the calendar.
    :param events_by_date: Mapping of "YYYY-MM-DD" -> list of events, as returned by events_by_date_map.
    :return: Array: The weeks/days grid, with each day replaced by its activities.
    """
    filled_days = []
    for week in days_month:
        filled_week = []
        for day in week:
            if day:
                key = f"{year}-{month:02d}-{day:02d}"
                filled_week.append(
                    {
                        "day": day,
                        "activities": events_by_date.get(key, []),
                    }
                )
            else:
                filled_week.append(None)
        filled_days.append(filled_week)

    return filled_days


def list_of_reports_of_area(code="", user=None):
    try:
        if code:
            area = TeamArea.objects.get(code=code)
        else:
            if not user:
                return False

            current_position = (
                user.profile.position_history.filter(end_date__isnull=True)
                .order_by("-start_date")
                .first()
            )
            if not current_position:
                return False

            area = current_position.position.area_associated
    except (ObjectDoesNotExist, AttributeError):
        return False

    manager = (
        UserProfile.objects.filter(
            user__is_active=True,
            user__email__isnull=False,
            position_history__position__area_associated=area,
            position_history__position__type__name="Manager",
            position_history__end_date__isnull=True,
        )
        .order_by("-position_history__start_date")
        .select_related("user")
        .distinct()
        .first()
    )

    today = datetime.date.today()
    days_since_jan_01 = (today - datetime.date(today.year, 1, 1)).days
    days_until_dec_31 = (datetime.date(today.year, 12, 31) - today).days

    context = {
        "past_activities": build_message_about_reports(
            _get_activities_already_finished(area, delta=days_since_jan_01)
        ),
        "future_activities": build_message_about_reports(
            _get_activities_soon_to_be_finished(area, delta=days_until_dec_31)
        ),
        "manager": manager,
        "area": area,
    }

    return context


def _get_activities_soon_to_be_finished(area, delta=14):
    today = datetime.date.today()
    interval = min(today + timedelta(delta), datetime.date(today.year, 12, 31))
    query = Q(
        end_date__lte=interval,  # Before the interval
        end_date__gte=today,  # After today
        area_responsible=area,  # Under a specific manager responsibility
    )
    events = Event.objects.filter(query)
    return events


def _get_activities_already_finished(area, delta=28):
    today = datetime.date.today()
    interval = max(today - timedelta(delta), datetime.date(today.year, 1, 1))
    query = Q(
        end_date__lte=today - timedelta(1),  # Before today
        end_date__gte=interval,  # After the interval
        area_responsible=area,  # Under a specific manager responsibility
    )
    events = Event.objects.filter(query).distinct()
    return events


def _get_activities_about_to_kickoff(area, delta=14):
    today = datetime.date.today()
    interval = min(today + timedelta(delta), datetime.date(today.year, 12, 31))
    query = Q(
        initial_date__gte=today,  # Beginning after today
        initial_date__lte=interval,  # Beginning before interval
        area_responsible=area,  # Under a specific manager responsibility
    )
    events = Event.objects.filter(query)
    return events
