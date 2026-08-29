from datetime import datetime, timedelta

from django.db import IntegrityError
from django.test import TestCase

from metrics.models import Activity, Metric
from report.models import (
    Editor,
    Funding,
    OperationReport,
    Organizer,
    Partner,
    Project,
    Report,
    Technology,
)
from strategy.models import (
    Direction,
    LearningArea,
    StrategicAxis,
    StrategicLearningQuestion,
)
from users.models import TeamArea, User, UserProfile


class FundingModelTest(TestCase):
    def setUp(self):
        self.name = "Funding"
        self.value = 1000
        self.project = Project.objects.create(text="Project")
        self.funding = Funding.objects.create(
            name=self.name, value=self.value, project=self.project
        )

    def test_funding_str_method_returns_its_text(self):
        self.assertEqual(str(self.funding), self.name)

    def test_funding_value(self):
        funding_value = self.funding.value
        self.assertEqual(funding_value, self.value)


class EditorModelTest(TestCase):
    def setUp(self):
        self.username = "Editor"
        self.editor = Editor.objects.create(username=self.username)

    def test_editor_str_method_returns_its_username(self):
        self.assertEqual(str(self.editor), self.username)


class PartnerModelTest(TestCase):
    def setUp(self):
        self.name = "Partner"
        self.partner = Partner.objects.create(name=self.name)

    def test_partner_str_method_returns_its_name(self):
        self.assertEqual(str(self.partner), self.name)


class OrganizerModelTest(TestCase):
    def setUp(self):
        self.organizer_name = "Organizer"
        self.partner = Partner.objects.create(name="Partner")
        self.organizer = Organizer.objects.create(name=self.organizer_name)
        self.organizer.institution.add(self.partner)

    def test_organizer_str_method_returns_their_name(self):
        self.assertEqual(str(self.organizer), self.organizer_name)

    def test_organizer_institution(self):
        institutions = self.organizer.institution.all()
        self.assertEqual(institutions.count(), 1)
        self.assertEqual(institutions.first(), self.partner)


class TechnologyModelTest(TestCase):
    def setUp(self):
        self.name = "Technology"
        self.technology = Technology.objects.create(name=self.name)

    def test_partner_str_method_returns_its_name(self):
        self.assertEqual(str(self.technology), self.name)


# class AreaActivatedModelTest(TestCase):
#     def setUp(self):
#         self.text = "Area Activated"
#         self.area_activated = AreaActivated.objects.create(text=self.text)
#
#     def test_area_activated_str_method_returns_the_text(self):
#         self.assertEqual(str(self.area_activated), self.text)
#
#     def test_area_activated_contact(self):
#         self.area_activated.contact = "Contact"
#         self.area_activated.save()
#         area_activated_contact = self.area_activated.contact
#         self.assertEqual(area_activated_contact, "Contact")
#
#     def test_area_activated_clean_method(self):
#         area_activated = AreaActivated()
#         with self.assertRaises(ValidationError):
#             area_activated.clean()
#
#     def test_creating_team_area_creates_an_area_activated_instance(self):
#         self.assertEqual(AreaActivated.objects.count(), 1)
#         self.assertFalse(AreaActivated.objects.filter(text="Team Area").exists())
#         TeamArea.objects.create(text="Team Area", code="Code")
#         self.assertEqual(AreaActivated.objects.count(), 2)
#         self.assertTrue(AreaActivated.objects.filter(text="Team Area").exists())


class ReportModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.team_area = TeamArea.objects.create(text="Area")
        self.activity = Activity.objects.create(text="Activity")
        project = Project.objects.create(text="Project")
        self.funding = Funding.objects.create(name="Funding", project=project)
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        self.direction = Direction.objects.create(
            text="Direction", strategic_axis=strategic_axis
        )
        learning_area = LearningArea.objects.create(text="Learning area")
        self.slq = StrategicLearningQuestion.objects.create(
            text="SLQ", learning_area=learning_area
        )

    def test_report_creation(self):
        report = Report.objects.create(
            created_by=self.user_profile,
            modified_by=self.user_profile,
            activity_associated=self.activity,
            area_responsible=self.team_area,
            initial_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=1),
            description="Report",
            links="https://testlink.com",
            participants=10,
            feedbacks=3,
            learning="Learning" * 60,
        )
        self.assertEqual(report.description, "Report")

    def test_report_end_date_default(self):
        report = Report.objects.create(
            created_by=self.user_profile,
            modified_by=self.user_profile,
            activity_associated=self.activity,
            area_responsible=self.team_area,
            initial_date=datetime.now().date(),
            description="Report",
            links="https://testlink.com",
            participants=10,
            feedbacks=3,
            learning="Learning",
        )
        self.assertEqual(report.end_date, report.initial_date)

    def test_report_string_representation(self):
        report = Report.objects.create(
            created_by=self.user_profile,
            modified_by=self.user_profile,
            activity_associated=self.activity,
            area_responsible=self.team_area,
            initial_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=1),
            description="Report",
            links="https://testlink.com",
            participants=10,
            feedbacks=3,
            learning="Learning",
        )
        self.assertEqual(str(report), "Report")


class OperationReportModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.team_area = TeamArea.objects.create(text="Area")
        self.activity = Activity.objects.create(text="Activity")
        self.report = Report.objects.create(
            created_by=self.user_profile,
            modified_by=self.user_profile,
            activity_associated=self.activity,
            area_responsible=self.team_area,
            initial_date=datetime.now().date(),
            description="Report",
            links="https://testlink.com",
        )
        self.metric = Metric.objects.create(text="Metric", activity=self.activity)

    def test_operation_report_creation(self):
        self.assertEqual(OperationReport.objects.count(), 0)
        OperationReport.objects.create(report=self.report, metric=self.metric)
        self.assertEqual(OperationReport.objects.count(), 1)

    def test_operation_str_representation(self):
        operation_report = OperationReport.objects.create(
            report=self.report, metric=self.metric
        )
        self.assertEqual(
            str(operation_report), self.report.description + " - " + self.metric.text
        )

    def test_operation_report_without_report_fails(self):
        with self.assertRaises(IntegrityError):
            OperationReport.objects.create(metric=self.metric)

    def test_operation_report_without_metric_fails(self):
        with self.assertRaises(IntegrityError):
            OperationReport.objects.create(report=self.report)
