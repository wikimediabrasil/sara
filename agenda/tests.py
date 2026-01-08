from io import StringIO
from datetime import datetime, date, timedelta
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.core import mail
from unittest.mock import patch

from agenda.models import Event
from agenda.services import send_event_reports
from users.models import User, UserProfile, TeamArea, Position
from agenda.views import get_activities_soon_to_be_finished, get_activities_already_finished,\
    get_activities_about_to_kickoff, show_list_of_reports_of_specific_area, show_list_of_reports_of_area
from agenda.templatetags.calendar_tags import date_tag, next_month_tag, previous_month_tag, next_year_tag, \
    previous_year_tag, next_day_tag, previous_day_tag


class EventModelTests(TestCase):
    def setUp(self):
        self.area_responsible = TeamArea.objects.create(text="Area Responsible", code="area_responsible")
        self.area_involved_1 = TeamArea.objects.create(text="Area Involved 1", code="area_involved_1")
        self.area_involved_2 = TeamArea.objects.create(text="Area Involved 2", code="area_involved_2")
        self.event = Event.objects.create(
            name="Test Event",
            initial_date=date(2023, 3, 24),
            end_date=date(2023, 3, 31),
            area_responsible=self.area_responsible,
        )

    def test_str_method_with_end_date_different_from_initial_date(self):
        correct_output = "Test Event (24/Mar - 31/Mar)"
        self.assertEqual(str(self.event), correct_output)

    def test_str_method_with_end_date_equal_from_initial_date(self):
        correct_output = "Test Event (24/Mar)"

        self.event.end_date = self.event.initial_date
        self.event.save()

        self.assertEqual(str(self.event), correct_output)

    def test_clean_method(self):
        event = Event.objects.create(
            name="Test Event 2",
            initial_date=date(2023, 3, 24),
            end_date=date(2023, 3, 31),
            area_responsible=self.area_responsible,
        )
        event.full_clean()

        with self.assertRaises(ValidationError):
            event.name = ""
            event.full_clean()

    def test_event_date_validation(self):
        event = Event(
            name="Valid",
            initial_date=date(2025, 1, 10),
            end_date=date(2025, 1, 10),
            area_responsible=self.area_responsible,
        )
        event.full_clean()

        invalid_event = Event(
            name="Invalid",
            initial_date=date(2025, 1, 10),
            end_date=date(2025, 1, 9),
            area_responsible=self.area_responsible,
        )

        with self.assertRaises(ValidationError):
            invalid_event.full_clean()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Event.objects.create(
                    name="Invalid DB",
                    initial_date=date(2025, 1, 10),
                    end_date=date(2025, 1, 9),
                    area_responsible=self.area_responsible,
                )


class EventViewTests(TestCase):
    def setUp(self):
        self.username = "testuser"
        self.password = "testpass"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.user_profile = UserProfile.objects.filter(user=self.user).first()
        self.team_area = TeamArea.objects.create(text="Team Area", code="Code")
        self.name = "Setup"

        self.day = 19
        self.month = 4
        self.year = 2023

        self.event = Event.objects.create(name=self.name,
                                          initial_date=date.today(),
                                          end_date=date.today(),
                                          area_responsible=self.team_area)

    def test_show_calendar_year(self):
        response = self.client.get(reverse('agenda:show_calendar_year'))
        self.assertRedirects(response, reverse('agenda:show_specific_calendar_year',
                                               kwargs={"year": datetime.now().year}))

    def test_show_specific_calendar_year(self):
        response = self.client.get(reverse('agenda:show_specific_calendar_year',
                                           kwargs={"year": self.year}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'agenda/calendar_year.html')

    def test_show_calendar(self):
        response = self.client.get(reverse('agenda:show_calendar'))
        self.assertRedirects(response, reverse('agenda:show_specific_calendar',
                                               kwargs={"year": datetime.now().year,
                                                       "month": datetime.now().month}))

    def test_show_specific_calendar(self):
        response = self.client.get(reverse('agenda:show_specific_calendar',
                                           kwargs={"year": self.year, "month": self.month}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'agenda/calendar_month.html')

    def test_show_calendar_day(self):
        response = self.client.get(reverse('agenda:show_calendar_day'))
        self.assertRedirects(response, reverse('agenda:show_specific_calendar_day',
                                               kwargs={"year": datetime.now().year,
                                                       "month": datetime.now().month,
                                                       "day": datetime.now().day}))

    def test_show_specific_calendar_day(self):
        response = self.client.get(reverse('agenda:show_specific_calendar_day',
                                           kwargs={"year": self.year, "month": self.month, "day": self.day}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'agenda/calendar_day.html')

    def test_add_event_get(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("agenda:create_event")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_add_event_post(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("agenda:create_event")
        data = {
            "name": "Title",
            "initial_date": date.today(),
            "end_date": date.today(),
            "area_responsible": self.team_area.pk
        }
        response = self.client.post(url, data=data)

        event = Event.objects.get(name=data["name"],
                                  initial_date=data["initial_date"],
                                  end_date=data["end_date"],
                                  area_responsible=data["area_responsible"])
        self.assertRedirects(response, reverse('agenda:list_events'))
        self.assertEqual(event.area_responsible, self.team_area)

    def test_add_event_post_with_invalid_parameters(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("agenda:create_event")
        data = {
            "initial_date": date.today(),
            "end_date": date.today(),
            "area_responsible": self.team_area.pk,
            "name": "",
        }
        self.client.post(url, data=data)
        self.assertFalse(Event.objects.filter(name="").exists())

    def test_detail_event_view_success(self):
        response = self.client.get(reverse('agenda:detail_event', args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'agenda/detail_event.html')
        self.assertContains(response, self.event.name)

    def test_detail_event_view_context(self):
        response = self.client.get(reverse('agenda:detail_event', args=[self.event.id]))
        self.assertIn('event', response.context)
        self.assertEqual(response.context['event'], self.event)

    def test_list_events(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("agenda:list_events")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_delete_event_get(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("agenda:delete_event", kwargs={"event_id": self.event.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'agenda/delete_event.html')

    def test_delete_event_post(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("agenda:delete_event", kwargs={"event_id": self.event.pk})

        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())

    def test_update_event_get(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("agenda:edit_event", kwargs={"event_id": self.event.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'agenda/update_event.html')

    def test_update_event_post(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("agenda:edit_event", kwargs={"event_id": self.event.pk})

        data = {
            "name": "New title",
            "initial_date": date.today(),
            "end_date": date.today(),
            "area_responsible": self.team_area.pk
        }

        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Event.objects.filter(name="New title").exists())
        self.assertFalse(Event.objects.filter(name=self.name).exists())

    def test_update_event_post_with_invalid_parameters(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("agenda:edit_event", kwargs={"event_id": self.event.pk})

        data = {
            "name": "",
            "initial_date": date.today(),
            "end_date": date.today(),
            "area_responsible": self.team_area.pk
        }

        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Event.objects.filter(name="").exists())
        self.assertTrue(Event.objects.filter(name=self.name).exists())


class EventEmailTests(TestCase):
    def setUp(self):
        self.name = "Event"
        self.initial_date = date.today()
        self.end_date = self.initial_date + timedelta(7)
        self.area_responsible = TeamArea.objects.create(text="Area responsible", code="Ar code")
        self.event = Event.objects.create(
            name=self.name,
            initial_date=self.initial_date,
            end_date=self.end_date,
            area_responsible=self.area_responsible
        )
        self.event.save()

    def test_get_activities_soon_to_be_finished_returns_events_near_the_end(self):
        events = get_activities_soon_to_be_finished(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.filter(pk=self.event.pk))

    def test_if_events_are_too_far_away_get_activities_soon_to_be_finished_returns_empty_queryset(self):
        self.event.end_date += timedelta(16)
        self.event.save()
        events = get_activities_soon_to_be_finished(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.none())

    def test_if_get_activities_soon_to_be_finished_returns_empty_queryset_if_events_already_finished(self):
        self.event.initial_date = date.today() - timedelta(2)
        self.event.end_date = date.today() - timedelta(1)
        self.event.save()
        events = get_activities_soon_to_be_finished(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.none())

    def test_get_activities_already_finished_returns_events_already_finished(self):
        self.event.initial_date = date.today() - timedelta(3)
        self.event.end_date = date.today() - timedelta(2)
        self.event.save()
        events = get_activities_already_finished(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.filter(pk=self.event.pk))

    def test_if_events_are_too_far_away_get_activities_already_finished_returns_empty_queryset(self):
        self.event.initial_date -= timedelta(60)
        self.event.end_date -= timedelta(60)
        self.event.save()
        events = get_activities_already_finished(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.none())

    def test_get_activities_already_finished_returns_empty_queryset_if_events_are_not_finished(self):
        self.event.end_date = date.today()
        self.event.save()
        events = get_activities_already_finished(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.none())

    def test_get_activities_about_to_kickoff_returns_events_with_start_in_near_future(self):
        self.event.initial_date = date.today() + timedelta(1)
        self.event.save()
        events = get_activities_about_to_kickoff(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.filter(pk=self.event.pk))

    def test_if_events_are_too_far_away_get_activities_about_to_kickoff_returns_empty_queryset(self):
        self.event.initial_date += timedelta(60)
        self.event.end_date += timedelta(60)
        self.event.save()
        events = get_activities_about_to_kickoff(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.none())

    def test_get_activities_about_to_kickoff_returns_empty_queryset_if_events_started_before_today(self):
        self.event.initial_date = date.today() - timedelta(1)
        self.event.save()
        events = get_activities_about_to_kickoff(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.none())

    def test_trying_to_send_email_for_manager_without_email_doesnt_sends_the_email(self):
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(text="Position", type=group, area_associated=self.area_responsible)
        user = User.objects.create_user(username="Username", password="Password")
        user.profile.position = position
        user.profile.save()

        response = self.client.get(reverse('agenda:send_email'))
        self.assertEqual(response.status_code, 302)

    def test_trying_to_send_email_for_manager_with_email_sends_the_email(self):
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(text="Position", type=group, area_associated=self.area_responsible)
        user = User.objects.create_user(username="Username", password="Password")
        user.profile.position = position
        user.profile.save()
        user.email = "to@example.com"
        user.save()

        response = self.client.get(reverse('agenda:send_email'))
        self.assertEqual(response.status_code, 302)

    def test_trying_to_send_email_with_no_activities_doesnt_sends_the_email(self):
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(text="Position", type=group, area_associated=self.area_responsible)
        user = User.objects.create_user(username="Username", password="Password")
        user.profile.position = position
        user.profile.save()
        user.email = "to@example.com"
        user.save()

        self.event.delete()

        response = self.client.get(reverse('agenda:send_email'))
        self.assertEqual(response.status_code, 302)

    def test_trying_to_send_email_with_activities_of_one_day_sends_the_email_with_proper_representation(self):
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(text="Position", type=group, area_associated=self.area_responsible)
        user = User.objects.create_user(username="Username", password="Password")
        user.profile.position = position
        user.profile.save()
        user.email = "to@example.com"
        user.save()

        self.event.initial_date=self.event.end_date
        self.event.save()

        response = self.client.get(reverse('agenda:send_email'))
        self.assertEqual(response.status_code, 302)

    def test_trying_to_send_email_when_manager_has_not_email_fails(self):
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(text="Position", type=group, area_associated=self.area_responsible)
        user = User.objects.create_user(username="Username", password="Password")
        user.profile.position = position
        user.profile.save()

        response = self.client.get(reverse('agenda:send_email'))
        self.assertEqual(response.status_code, 302)

    def test_manager_with_no_relevant_events_does_not_receive_email(self):
        self.event.delete()
        Event.objects.create(
            name=self.name,
            initial_date=date.today() + timedelta(99),
            end_date=date.today() + timedelta(100),
            area_responsible=self.area_responsible
        )

        group = Group.objects.create(name="Manager")

        # Position
        position = Position.objects.create(
            text="Manager position",
            type=group,
            area_associated=self.area_responsible,
        )

        # User
        user = User.objects.create_user(
            username="manager",
            email="manager@test.com",
            password="pass",
            is_active=True,
        )

        # UserProfile
        user.profile.position = position
        user.profile.save()

        # Event outside reporting windows
        Event.objects.create(
            name="Old event",
            area_responsible=self.area_responsible,
            initial_date=datetime.now().date() - timedelta(days=120),
            end_date=datetime.now().date() - timedelta(days=100),
        )

        send_event_reports()

        self.assertEqual(len(mail.outbox), 0)

    @patch("agenda.management.commands.send_event_reports.send_event_reports")
    def test_command_calls_service_and_outputs_success(self, mock_send):
        out = StringIO()

        call_command("send_event_reports", stdout=out)

        mock_send.assert_called_once()
        self.assertIn("Reports sent", out.getvalue())


class ListReportsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.username = "testuser"
        self.password = "testpass"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.user.first_name = "First Name"
        self.user.save()

        self.profile = UserProfile.objects.get(user=self.user)
        self.group = Group.objects.create(name="Group")
        self.area = TeamArea.objects.create(text="Test Area")
        self.position = Position.objects.create(text="Position", type=self.group, area_associated=self.area)

    @patch("agenda.views.get_activities_already_finished")
    @patch("agenda.views.get_activities_soon_to_be_finished")
    @patch("agenda.views.build_message_about_reports")
    def test_view_with_area_id(self, mock_build_message, mock_future, mock_past):
        mock_past.return_value = "past"
        mock_future.return_value = "future"
        mock_build_message.side_effect = lambda x: f"built-{x}"

        request = self.factory.get("/fake-url")
        request.user = self.user

        with patch("agenda.views.TeamArea.objects.get") as mock_area_get, \
                patch("agenda.views.UserProfile.objects.filter") as mock_userprofile_filter:
            mock_area_get.return_value = self.area
            mock_userprofile_filter.return_value.first.return_value = self.profile

            response = show_list_of_reports_of_specific_area(request, area_id=self.area.pk)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"built-past", response.content)
            self.assertIn(b"built-future", response.content)

    @patch("agenda.views.get_activities_already_finished")
    @patch("agenda.views.get_activities_soon_to_be_finished")
    @patch("agenda.views.build_message_about_reports")
    def test_view_without_area_id(self, mock_build_message, mock_future, mock_past):
        mock_past.return_value = "past"
        mock_future.return_value = "future"
        mock_build_message.side_effect = lambda x: f"built-{x}"

        request = self.factory.get("/fake-url")
        request.user = self.user

        with patch("agenda.views.TeamArea.objects.get") as mock_area_get:
            mock_area_get.return_value = self.area

            response = show_list_of_reports_of_specific_area(request)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"built-past", response.content)
            self.assertIn(b"built-future", response.content)

    def test_redirect_from_area_view(self):
        request = self.factory.get("/fake-url")
        response = show_list_of_reports_of_area(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("agenda:specific_area_activities"))


class CalendarTagTest(TestCase):
    def setUp(self):
        self.today = datetime.today()
        self.current_date = date(self.today.year, 6, 15)
        self.current_tomorrow = self.current_date + timedelta(days=1)
        self.current_yesterday = self.current_date - timedelta(days=1)
        self.current_next_month = date(self.current_date.year, 7, 15)
        self.current_last_month = date(self.current_date.year, 5, 15)
        self.current_next_year = date(self.current_date.year + 1, 6, 15)
        self.current_last_year = date(self.current_date.year - 1, 6, 15)

    def test_returns_filtered_events(self):
        area = TeamArea.objects.create(text="Area", code="area")
        event = Event.objects.create(
            name="Test Event",
            initial_date = self.current_date,
            end_date = self.current_tomorrow,
            area_responsible = area,
        )
        result = date_tag(self.current_date.year, self.current_date.month, self.current_date.day)
        self.assertEqual(list(result), [event])

    def test_returns_empty_string_if_no_event(self):
        result = date_tag(2025, 10, 15)
        self.assertEqual(result , "")

    def test_returns_empty_if_day_is_zero(self):
        result = date_tag(2025, 10, 0)
        self.assertEqual(result , "")

    def test_returns_empty_if_day_is_none(self):
        result = date_tag(2025, 10, None)
        self.assertEqual(result , "")

    def test_next_month_tag_normal_case(self):
        url = next_month_tag(2025, 10)
        expected = reverse('agenda:show_specific_calendar', kwargs={'year': 2025, 'month': 11})
        self.assertEqual(url, expected)

    def test_next_month_tag_wraps_to_next_year(self):
        url = next_month_tag(2025, 12)
        expected = reverse('agenda:show_specific_calendar', kwargs={'year': 2026, 'month': 1})
        self.assertEqual(url, expected)

    def test_previous_month_tag_normal_case(self):
        url = previous_month_tag(2025, 10)
        expected = reverse('agenda:show_specific_calendar', kwargs={'year': 2025, 'month': 9})
        self.assertEqual(url, expected)

    def test_previous_month_tag_wraps_to_previous_year(self):
        url = previous_month_tag(2025, 1)
        expected = reverse('agenda:show_specific_calendar', kwargs={'year': 2024, 'month': 12})
        self.assertEqual(url, expected)

    def test_next_year_tag(self):
        url = next_year_tag(2025)
        expected = reverse('agenda:show_specific_calendar_year', kwargs={'year': 2026})
        self.assertEqual(url, expected)

    def test_previous_year_tag(self):
        url = previous_year_tag(2025)
        expected = reverse('agenda:show_specific_calendar_year', kwargs={'year': 2024})
        self.assertEqual(url, expected)

    def test_next_day_tag_normal_case(self):
        url = next_day_tag(2025, 10, 17)
        expected = reverse('agenda:show_specific_calendar_day', kwargs={'year': 2025, 'month': 10, 'day': 18})
        self.assertEqual(url, expected)

    def test_next_day_tag_wraps_to_next_month(self):
        url = next_day_tag(2025, 1, 31)
        expected = reverse('agenda:show_specific_calendar_day', kwargs={'year': 2025, 'month': 2, 'day': 1})
        self.assertEqual(url, expected)

    def test_previous_day_tag_normal_case(self):
        url = previous_day_tag(2025, 10, 17)
        expected = reverse('agenda:show_specific_calendar_day', kwargs={'year': 2025, 'month': 10, 'day': 16})
        self.assertEqual(url, expected)

    def test_previous_day_tag_wraps_to_previous_month(self):
        url = previous_day_tag(2025, 3, 1)
        expected = reverse('agenda:show_specific_calendar_day', kwargs={'year': 2025, 'month': 2, 'day': 28})
        self.assertEqual(url, expected)