import datetime
from django.test import TestCase
from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from metrics.models import Metric, Activity
from agenda.models import Event
from users.models import User, UserProfile, TeamArea, Position
from agenda.views import get_activities_soon_to_be_finished, get_activities_already_finished,\
    get_activities_about_to_kickoff


class EventModelTests(TestCase):
    def setUp(self):
        self.area_responsible = TeamArea.objects.create(text="Area Responsible", code="area_responsible")
        self.area_involved_1 = TeamArea.objects.create(text="Area Involved 1", code="area_involved_1")
        self.area_involved_2 = TeamArea.objects.create(text="Area Involved 2", code="area_involved_2")
        self.event = Event.objects.create(
            name="Test Event",
            initial_date=datetime.date(2023, 3, 24),
            end_date=datetime.date(2023, 3, 31),
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
            initial_date=datetime.date(2023, 3, 24),
            end_date=datetime.date(2023, 3, 31),
            area_responsible=self.area_responsible,
        )
        event.full_clean()

        with self.assertRaises(ValidationError):
            event.name = ""
            event.full_clean()


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
                                          initial_date=datetime.date.today(),
                                          end_date=datetime.date.today(),
                                          area_responsible=self.team_area)

    def test_show_calendar_for_logged_user(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('agenda:show_calendar'))
        self.assertRedirects(response, reverse('agenda:show_specific_calendar',
                                               kwargs={"year": datetime.datetime.now().year,
                                                       "month": datetime.datetime.now().month}))

    def test_show_specific_calendar_for_logged_user(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('agenda:show_specific_calendar',
                                           kwargs={"year": self.year, "month": self.month}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'agenda/calendar.html')

    def test_show_calendar_day_for_logged_user(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('agenda:show_calendar_day'))
        self.assertRedirects(response, reverse('agenda:show_specific_calendar_day',
                                               kwargs={"year": datetime.datetime.now().year,
                                                       "month": datetime.datetime.now().month,
                                                       "day": datetime.datetime.now().day}))

    def test_show_specific_calendar_day_for_logged_user(self):
        self.client.login(username=self.username, password=self.password)
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
            "initial_date": datetime.date.today(),
            "end_date": datetime.date.today(),
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
            "initial_date": datetime.date.today(),
            "end_date": datetime.date.today(),
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
            "initial_date": datetime.date.today(),
            "end_date": datetime.date.today(),
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
            "initial_date": datetime.date.today(),
            "end_date": datetime.date.today(),
            "area_responsible": self.team_area.pk
        }

        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Event.objects.filter(name="").exists())
        self.assertTrue(Event.objects.filter(name=self.name).exists())


class EventEmailTests(TestCase):
    def setUp(self):
        self.name = "Event"
        self.initial_date = datetime.date.today()
        self.end_date = self.initial_date + datetime.timedelta(7)
        self.area_responsible = TeamArea.objects.create(text="Area responsible", code="Ar code", color_code="AR")
        self.area_involved = TeamArea.objects.create(text="Area involved", code="Ai code", color_code="AI")
        self.activity_associated = Activity.objects.create(text="Activity", area_responsible=self.area_responsible)
        self.metric_associated = Metric.objects.create(text="Metric", activity=self.activity_associated)
        self.event = Event.objects.create(
            name=self.name,
            initial_date=self.initial_date,
            end_date=self.end_date,
            area_responsible=self.area_responsible,
            activity_associated=self.activity_associated)

        self.event.metric_associated.add(self.metric_associated)
        self.event.save()

    def test_get_activities_soon_to_be_finished_returns_events_near_the_end(self):
        events = get_activities_soon_to_be_finished(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.filter(pk=self.event.pk))

    def test_if_events_are_too_far_away_get_activities_soon_to_be_finished_returns_empty_queryset(self):
        self.event.end_date += datetime.timedelta(16)
        self.event.save()
        events = get_activities_soon_to_be_finished(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.none())

    def test_if_get_activities_soon_to_be_finished_returns_empty_queryset_if_events_already_finished(self):
        self.event.end_date = datetime.date.today() - datetime.timedelta(1)
        self.event.save()
        events = get_activities_soon_to_be_finished(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.none())

    def test_get_activities_already_finished_returns_events_already_finished(self):
        self.event.initial_date = datetime.date.today() - datetime.timedelta(3)
        self.event.end_date = datetime.date.today() - datetime.timedelta(2)
        self.event.save()
        events = get_activities_already_finished(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.filter(pk=self.event.pk))

    def test_if_events_are_too_far_away_get_activities_already_finished_returns_empty_queryset(self):
        self.event.initial_date -= datetime.timedelta(60)
        self.event.end_date -= datetime.timedelta(60)
        self.event.save()
        events = get_activities_already_finished(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.none())

    def test_get_activities_already_finished_returns_empty_queryset_if_events_are_not_finished(self):
        self.event.end_date = datetime.date.today()
        self.event.save()
        events = get_activities_already_finished(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.none())


    def test_get_activities_about_to_kickoff_returns_events_with_start_in_near_future(self):
        self.event.initial_date = datetime.date.today() + datetime.timedelta(1)
        self.event.save()
        events = get_activities_about_to_kickoff(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.filter(pk=self.event.pk))

    def test_if_events_are_too_far_away_get_activities_about_to_kickoff_returns_empty_queryset(self):
        self.event.initial_date += datetime.timedelta(60)
        self.event.save()
        events = get_activities_about_to_kickoff(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.none())

    def test_get_activities_about_to_kickoff_returns_empty_queryset_if_events_started_before_today(self):
        self.event.initial_date = datetime.date.today() - datetime.timedelta(1)
        self.event.save()
        events = get_activities_about_to_kickoff(self.area_responsible)
        self.assertQuerySetEqual(events, Event.objects.none())

    def test_trying_to_send_email_for_manager_without_email_doesnt_sends_the_email(self):
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(text="Position", type=group, area_associated=self.area_responsible)
        user = User.objects.create_user(username="Username", password="Password")
        user.userprofile.position = position
        user.userprofile.save()

        response = self.client.get(reverse('agenda:send_email'))
        self.assertEqual(response.status_code, 302)

    def test_trying_to_send_email_for_manager_with_email_sends_the_email(self):
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(text="Position", type=group, area_associated=self.area_responsible)
        user = User.objects.create_user(username="Username", password="Password")
        user.userprofile.position = position
        user.userprofile.save()
        user.email = "to@example.com"
        user.save()

        response = self.client.get(reverse('agenda:send_email'))
        self.assertEqual(response.status_code, 302)

    def test_trying_to_send_email_with_no_activities_doesnt_sends_the_email(self):
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(text="Position", type=group, area_associated=self.area_responsible)
        user = User.objects.create_user(username="Username", password="Password")
        user.userprofile.position = position
        user.userprofile.save()
        user.email = "to@example.com"
        user.save()

        self.event.delete()

        response = self.client.get(reverse('agenda:send_email'))
        self.assertEqual(response.status_code, 302)

    def test_trying_to_send_email_with_activities_of_one_day_sends_the_email_with_proper_representation(self):
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(text="Position", type=group, area_associated=self.area_responsible)
        user = User.objects.create_user(username="Username", password="Password")
        user.userprofile.position = position
        user.userprofile.save()
        user.email = "to@example.com"
        user.save()

        self.event.initial_date=self.event.end_date
        self.event.save()

        response = self.client.get(reverse('agenda:send_email'))
        self.assertEqual(response.status_code, 302)

    def test_trying_to_send_email_when_manager_hasnt_email_fails(self):
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(text="Position", type=group, area_associated=self.area_responsible)
        user = User.objects.create_user(username="Username", password="Password")
        user.userprofile.position = position
        user.userprofile.save()

        response = self.client.get(reverse('agenda:send_email'))
        self.assertEqual(response.status_code, 302)