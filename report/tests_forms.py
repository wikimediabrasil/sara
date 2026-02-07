from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from metrics.models import Area
from users.models import Position, TeamArea, User

from .forms import NewReportForm
from .models import (
    Activity,
    Funding,
    Metric,
    Organizer,
    Partner,
    Project,
    Report,
    UserProfile,
)


class NewReportFormTest(TestCase):

    def setUp(self):
        self.user = User.objects.create(username="Username", password="<PASSWORD>")
        self.user_profile = UserProfile.objects.filter(user=self.user).first()
        self.area = Area.objects.create(text="Area Test")
        self.team_area = TeamArea.objects.create(text="Team Area", code="code")
        self.partner = Partner.objects.create(name="Partner Test")
        self.activity = Activity.objects.create(text="Activity Test", area=self.area)
        self.main_funding = Project.objects.create(text="Main", main_funding=True)
        self.project = Project.objects.create(
            text="Project", counts_for_main_funding=True
        )
        self.funding = Funding.objects.create(name="Funding Test", project=self.project)
        self.metric = Metric.objects.create(
            text="Metric Test", activity=self.activity, number_of_editors=13
        )
        self.metric.project.add(self.main_funding)
        self.area.project.add(self.project)

        self.form_data = {
            "activity_associated": self.activity.id,
            "area_responsible": self.team_area.id,
            "area_activated": [self.team_area.id],
            "initial_date": "2026-01-01",
            "end_date": "2026-01-10",
            "description": "Test description",
            "links": "http://example.com",
            "technologies_used": [],
            "directions_related": [],
            "learning_questions_related": [],
            "funding_associated": [self.funding.id],
            "editors_string": "editor1\neditor2",
            "organizers_string": "Organizer1|Partner1|Partner2",
            "participants": 5,
            "feedbacks": 3,
            "donors": 0,
            "submissions": 0,
            "partners_activated": [self.partner.id],
            "metrics_related": [self.metric.id],
            "wikipedia_created": 0,
            "wikipedia_edited": 0,
            "commons_created": 0,
            "commons_edited": 0,
            "wikidata_created": 0,
            "wikidata_edited": 0,
            "wikiversity_created": 0,
            "wikiversity_edited": 0,
            "wikibooks_created": 0,
            "wikibooks_edited": 0,
            "wikisource_created": 0,
            "wikisource_edited": 0,
            "wikinews_created": 0,
            "wikinews_edited": 0,
            "wikiquote_created": 0,
            "wikiquote_edited": 0,
            "wiktionary_created": 0,
            "wiktionary_edited": 0,
            "wikivoyage_created": 0,
            "wikivoyage_edited": 0,
            "wikispecies_created": 0,
            "wikispecies_edited": 0,
            "metawiki_created": 0,
            "metawiki_edited": 0,
            "mediawiki_created": 0,
            "mediawiki_edited": 0,
            "wikifunctions_created": 0,
            "wikifunctions_edited": 0,
            "incubator_created": 0,
            "incubator_edited": 0,
        }

    def test_form_initialization_sets_area_responsible_for_new(self):
        group = Group.objects.create(name="Test Group")
        position = Position.objects.create(
            text="Test Position", type=group, area_associated=self.team_area
        )
        self.user.profile.position = position
        self.user.profile.save()
        self.user.save()

        form = NewReportForm(user=self.user, data={}, is_update=False)
        self.assertEqual(form.fields["area_responsible"].initial, self.team_area.id)

    def test_clean_parses_editors_and_organizers_correctly(self):
        form = NewReportForm(user=self.user, data=self.form_data)
        self.assertTrue(form.is_valid())
        cleaned = form.clean()
        self.assertIn("_parsed_editors", cleaned)
        self.assertIn("_parsed_organizers", cleaned)
        self.assertEqual(set(cleaned["_parsed_editors"]), {"editor1", "editor2"})
        self.assertIn("Organizer1", cleaned["_parsed_organizers"][0]["name"])

    def test_clean_end_date_returns_initial_if_missing(self):
        data = self.form_data.copy()
        data.pop("end_date")
        form = NewReportForm(user=self.user, data=data)
        form.is_valid()
        self.assertEqual(form.clean_end_date(), timezone.datetime(2026, 1, 1).date())

    @patch("report.forms.get_user_date_of_registration")
    def test_save_creates_report_and_sets_relationships(self, mock_registration_date):
        mock_registration_date.return_value = timezone.now().date()
        form = NewReportForm(user=self.user, data=self.form_data)
        self.assertTrue(form.is_valid())
        report = form.save(commit=True, user=self.user)

        self.assertEqual(report.created_by, self.user_profile)
        self.assertEqual(report.modified_by, self.user_profile)
        self.assertEqual(report.description, "Test description")

        self.assertEqual(report.editors.count(), 2)
        self.assertEqual(report.organizers.count(), 1)

    def test_metrics_related_includes_main_funding_metrics(self):
        form = NewReportForm(user=self.user, data=self.form_data)
        self.assertTrue(form.is_valid())
        metrics = form._metrics_related()
        self.assertIn(self.metric, metrics)

    def test_apply_implicit_metrics_adds_correct_metrics(self):
        form = NewReportForm(user=self.user_profile, data=self.form_data)
        form.is_valid()
        report = Report.objects.create(
            created_by=self.user_profile,
            modified_by=self.user_profile,
            area_responsible=self.team_area,
            activity_associated=self.activity,
            initial_date="2026-01-01",
            description="Test",
            links="link",
        )
        form._has_editors = True
        form._has_new_editors = True
        metrics = form._apply_implicit_metrics(report, Metric.objects.none())
        self.assertTrue(metrics.exists())

    def test_save_handles_empty_editors_and_organizers(self):
        data = self.form_data.copy()
        data["editors_string"] = ""
        data["organizers_string"] = ""
        form = NewReportForm(user=self.user, data=data)
        self.assertTrue(form.is_valid())
        report = form.save(commit=True, user=self.user)
        self.assertEqual(report.editors.count(), 0)
        self.assertEqual(report.organizers.count(), 0)

    def test_save_handles_space_organizers(self):
        data = self.form_data.copy()
        data["organizers_string"] = "Organizer1\n \nOrganizer2"
        form = NewReportForm(user=self.user, data=data)
        self.assertTrue(form.is_valid())
        report = form.save(commit=True, user=self.user)
        self.assertEqual(report.organizers.count(), 2)
        self.assertTrue(Organizer.objects.filter(name="Organizer1").exists())
        self.assertTrue(Organizer.objects.filter(name="Organizer2").exists())
        self.assertFalse(Organizer.objects.filter(name=" ").exists())

    def test_save_handles_institutions_of_organizers(self):
        data = self.form_data.copy()
        data["organizers_string"] = (
            "Organizer1|Partner 1\n \nOrganizer2|Partner 2|Partner 3"
        )
        form = NewReportForm(user=self.user, data=data)
        self.assertTrue(form.is_valid())
        report = form.save(commit=True, user=self.user)
        self.assertEqual(report.organizers.count(), 2)
        self.assertTrue(Organizer.objects.filter(name="Organizer1").exists())
        self.assertTrue(Organizer.objects.filter(name="Organizer2").exists())
        self.assertFalse(Organizer.objects.filter(name=" ").exists())

    def test_save_handles_organizers_retained(self):
        data = self.form_data.copy()
        data["organizers_string"] = "Organizer1\nOrganizer2"

        form = NewReportForm(user=self.user, data=data)
        self.assertTrue(form.is_valid())
        form.save(commit=True, user=self.user)

        organizer1 = Organizer.objects.get(name="Organizer1")
        organizer2 = Organizer.objects.get(name="Organizer2")

        data["description"] = "New report"
        data["organizers_string"] = "Organizer1|Partner1\nOrganizer3"
        self.assertFalse(organizer1.retained)
        self.assertFalse(organizer2.retained)

        form_2 = NewReportForm(user=self.user, data=data)
        self.assertTrue(form_2.is_valid())
        form_2.save(commit=True, user=self.user)
        organizer1.refresh_from_db()
        organizer3 = Organizer.objects.get(name="Organizer3")

        self.assertTrue(organizer1.retained)
        self.assertFalse(organizer2.retained)
        self.assertFalse(organizer3.retained)

    def test_add_metrics_related_depending_on_values(self):
        form = NewReportForm(user=self.user_profile, data=self.form_data)
        form.is_valid()
        report = Report.objects.create(
            created_by=self.user_profile,
            modified_by=self.user_profile,
            area_responsible=self.team_area,
            activity_associated=self.activity,
            initial_date="2026-01-01",
            description="Test",
            links="link",
        )
        form._has_editors = True
        form._has_new_editors = True
        metrics = form._apply_implicit_metrics(report, Metric.objects.none())
        self.assertTrue(metrics.exists())
