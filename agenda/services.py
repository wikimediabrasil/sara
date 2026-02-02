from datetime import timedelta
from collections import defaultdict

from django.utils.timezone import now
from django.core.mail import EmailMessage, get_connection
from django.template.loader import get_template
from django.conf import settings
from django.db.models import Case, When, Value, CharField
from django.utils.translation import gettext as _

from users.models import UserProfile
from agenda.models import Event

def send_event_reports():
    template = get_template("agenda/email_template.html")
    today = now().date()

    managers = (
        UserProfile.objects
        .filter(
            user__is_active=True,
            user__email__isnull=False,
            position_history__position__type__name="Manager",
            position_history__end_date__isnull=True,
        )
        .select_related("user")
        .prefetch_related("position_history__position__area_associated")
        .distinct()
    )

    areas_ids = {manager.position_history.position.area_associated_id for manager in managers}

    events = (
        Event.objects
        .filter(area_responsible_id__in=areas_ids)
        .annotate(
            report_state=Case(
                When(
                    end_date__lt=today,
                    end_date__gte=today - timedelta(days=28),
                    then=Value("late")
                ),
                When(
                    end_date__gte=today,
                    end_date__lte=today + timedelta(days=14),
                    then=Value("upcoming")
                ),
                When(
                    initial_date__gte=today,
                    initial_date__lte=today + timedelta(days=14),
                    then=Value("kickoff")
                ),
                default=Value(None),
                output_field=CharField(),
            )
        )
    )

    grouped = defaultdict(lambda: {
        "late": [],
        "upcoming": [],
        "kickoff": [],
    })

    for event in events:
        if event.report_state:
            grouped[event.area_responsible_id][event.report_state].append(event)

    emails = []

    for manager in managers:
        area = manager.position_history.position.area_associated
        data = grouped.get(area.id)

        if not data:
            continue

        context = {
            "upcoming_reports": build_message_about_reports(data["upcoming"]),
            "late_reports": build_message_about_reports(data["late"]),
            "about_to_kickoff": build_message_about_reports(data["kickoff"]),
            "manager": manager,
            "area": area
        }

        emails.append(
            EmailMessage(
                subject=_("SARA Report - %(area)s") % {"area": area},
                body=template.render(context),
                from_email=settings.EMAIL_HOST_USER,
                to=[manager.user.email],
                reply_to=[settings.EMAIL_HOST_USER],
                bcc=[settings.EMAIL_COORDINATOR],
            )
        )

    connection = get_connection()
    for email in emails:
        email.content_subtype = "html"
    connection.send_messages(emails)

    pass


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
