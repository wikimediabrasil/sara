import zipfile
import pandas as pd
from io import BytesIO
from datetime import datetime
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from django.utils.translation import gettext as _

from metrics.models import Metric
from users.models import TeamArea, UserProfile, User
from metrics.models import Activity, Area
from strategy.models import Direction, StrategicAxis, LearningArea
from report.models import Funding, Partner, Technology, AreaActivated, StrategicLearningQuestion, Report, Editor, Organizer, Project, OperationReport
from report.forms import NewReportForm, activities_associated_as_choices, learning_areas_as_choices
from report.views import export_report_instance, export_metrics, export_user_profile, export_area_activated, export_directions_related, export_editors, export_learning_questions_related, export_organizers, export_partners_activated, export_technologies_used, get_or_create_editors, get_or_create_organizers, export_operation_report, export_funding


class ReportAddViewTest(TestCase):
    def setUp(self):
        self.username = "testuser"
        self.password = "testpass"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.user_profile = UserProfile.objects.filter(user=self.user).first()
        self.add_permission = Permission.objects.get(codename="add_report")
        self.delete_permission = Permission.objects.get(codename="delete_report")
        self.user.user_permissions.add(self.add_permission)
        self.user.user_permissions.add(self.delete_permission)

    def test_add_report_view_fails_if_user_doesnt_have_permission(self):
        self.user.user_permissions.remove(self.add_permission)
        self.client.login(username=self.username, password=self.password)
        url = reverse("report:add_report")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={reverse('report:add_report')}")

    def test_add_report_view_get(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("report:add_report")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["report_form"], NewReportForm)
        self.assertEqual(response.context["directions_related_set"], [])
        self.assertEqual(response.context["learning_questions_related_set"], [])

    def test_add_report_view_post_associates_metrics_based_on_values(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("report:add_report")

        project = Project.objects.create(text="Wikimedia Community Fund", main_funding=True)
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        direction = Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        slq = StrategicLearningQuestion.objects.create(text="SLQ", learning_area=learning_area)
        activity_associated = Activity.objects.create(text="Activity")
        area_responsible = TeamArea.objects.create(text="Area")
        metric = Metric.objects.create(text="Metric", activity=activity_associated, number_of_editors=10)
        metric_2 = Metric.objects.create(text="Metric 2", activity=activity_associated, wikipedia_edited=2)
        metric_2.project.add(project)
        metric_2.save()
        metric_3 = Metric.objects.create(text="Metric 3", activity=activity_associated, number_of_editors=23)
        metric_3.project.add(project)
        metric_3.save()
        Editor.objects.create(username="Editor")

        data = {
            "wikipedia_created": 0, "wikipedia_edited": 5,
            "commons_created": 0, "commons_edited": 0,
            "wikidata_created": 0, "wikidata_edited": 0,
            "wikiversity_created": 0, "wikiversity_edited": 0,
            "wikibooks_created": 0, "wikibooks_edited": 0,
            "wikisource_created": 0, "wikisource_edited": 0,
            "wikinews_created": 0, "wikinews_edited": 0,
            "wikiquote_created": 0, "wikiquote_edited": 0,
            "wiktionary_created": 0, "wiktionary_edited": 0,
            "wikivoyage_created": 0, "wikivoyage_edited": 0,
            "wikispecies_created": 0, "wikispecies_edited": 0,
            "metawiki_created": 0, "metawiki_edited": 0,
            "mediawiki_created": 0, "mediawiki_edited": 0,
            "participants": 10, "resources": 0, "feedbacks": 0,
            "number_of_people_reached_through_social_media": 0,
            "description": "Report",
            "initial_date": datetime.now().date().strftime("%Y-%m-%d"),
            "directions_related": [direction.id],
            "editors_string": "Editor",
            "learning": "Learnings!"*51,
            "learning_questions_related": [slq.id],
            "activity_associated": activity_associated.id,
            "area_responsible": area_responsible.id,
            "links": "Links",
            "donors": 0,
            "submissions": 0,
            "metrics_related": [metric.id]
        }
        operation_data = {
            "Operation-TOTAL_FORMS": 1,
            "Operation-INITIAL_FORMS": 0,
            "Operation-MIN_NUM_FORMS": 0,
            "Operation-MAX_NUM_FORMS": 1000,
            "Operation-0-metric": metric.id,
            "Operation-0-number_of_people_reached_through_social_media": 1,
            "Operation-0-number_of_new_followers": 2,
            "Operation-0-number_of_mentions": 3,
            "Operation-0-number_of_community_communications": 0,
            "Operation-0-number_of_events": 4,
            "Operation-0-number_of_resources": 5,
            "Operation-0-number_of_partnerships_activated": 6,
            "Operation-0-number_of_new_partnerships": 0
        }
        data.update(operation_data)
        self.client.post(url, data=data)
        report = Report.objects.get(id=1)
        self.assertIn(metric_2, report.metrics_related.all())
        self.assertIn(metric_3, report.metrics_related.all())

    def test_add_report_view_post(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("report:add_report")

        Project.objects.create(text="Wikimedia Community Fund", main_funding=True)
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        direction = Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        slq = StrategicLearningQuestion.objects.create(text="SLQ", learning_area=learning_area)
        activity_associated = Activity.objects.create(text="Activity")
        area_responsible = TeamArea.objects.create(text="Area")
        metric = Metric.objects.create(text="Metric", activity=activity_associated, number_of_editors=10, is_operation=True)

        data = {
            "wikipedia_created": 0, "wikipedia_edited": 0,
            "commons_created": 0, "commons_edited": 0,
            "wikidata_created": 0, "wikidata_edited": 0,
            "wikiversity_created": 0, "wikiversity_edited": 0,
            "wikibooks_created": 0, "wikibooks_edited": 0,
            "wikisource_created": 0, "wikisource_edited": 0,
            "wikinews_created": 0, "wikinews_edited": 0,
            "wikiquote_created": 0, "wikiquote_edited": 0,
            "wiktionary_created": 0, "wiktionary_edited": 0,
            "wikivoyage_created": 0, "wikivoyage_edited": 0,
            "wikispecies_created": 0, "wikispecies_edited": 0,
            "metawiki_created": 0, "metawiki_edited": 0,
            "mediawiki_created": 0, "mediawiki_edited": 0,
            "participants": 0, "resources": 0, "feedbacks": 0,
            "number_of_people_reached_through_social_media": 0,
            "description": "Report",
            "initial_date": datetime.now().date().strftime("%Y-%m-%d"),
            "directions_related": [direction.id],
            "learning": "Learnings!"*51,
            "learning_questions_related": [slq.id],
            "activity_associated": activity_associated.id,
            "area_responsible": area_responsible.id,
            "links": "Links",
            "metrics_related": [metric.id],
            "organizers_string": "Organizer 1;Institution 1;Institution 2",
            "donors": 0,
            "submissions": 0
        }
        form = NewReportForm(data, user=self.user)
        self.assertTrue(form.is_valid())

        operation_data = {
            "Operation-TOTAL_FORMS": 1,
            "Operation-INITIAL_FORMS": 0,
            "Operation-MIN_NUM_FORMS": 0,
            "Operation-MAX_NUM_FORMS": 1000,
            "Operation-0-metric":metric.id,
            "Operation-0-number_of_people_reached_through_social_media": 1,
            "Operation-0-number_of_new_followers": 2,
            "Operation-0-number_of_mentions": 3,
            "Operation-0-number_of_community_communications": 0,
            "Operation-0-number_of_events": 4,
            "Operation-0-number_of_resources": 5,
            "Operation-0-number_of_partnerships_activated": 6,
            "Operation-0-number_of_new_partnerships": 0
        }

        data.update(operation_data)
        response = self.client.post(url, data=data)
        report = Report.objects.get(description=data["description"])
        self.assertRedirects(response, reverse("report:detail_report", kwargs={"report_id": report.id}), target_status_code=302)

        report = Report.objects.get(id=1)
        self.assertEqual(report.description, "Report")

    def test_add_report_view_post_fails_with_invalid_parameters(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("report:add_report")

        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        direction = Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        slq = StrategicLearningQuestion.objects.create(text="SLQ", learning_area=learning_area)
        activity_associated = Activity.objects.create(text="Activity")
        area_responsible = TeamArea.objects.create(text="Area")

        data = {
            "description": "Report",
            "initial_date": datetime.now().date().strftime("%Y-%m-%d"),
            "directions_related": [direction.id],
            "learning": "Learnings!" * 49,
            "learning_questions_related": [slq.id],
            "activity_associated": activity_associated.id,
            "area_responsible": area_responsible.id,
            "links": "Links"
        }
        form = NewReportForm(data, user=self.user)
        self.assertFalse(form.is_valid())
        self.client.post(url, data=data)
        self.assertFalse(Report.objects.filter(description=data["description"]).exists())

    def test_add_report_fails_if_it_is_a_duplicate(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("report:add_report")

        Project.objects.create(text="Wikimedia Community Fund", main_funding=True)
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        direction = Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        slq = StrategicLearningQuestion.objects.create(text="SLQ", learning_area=learning_area)
        activity_associated = Activity.objects.create(text="Activity")
        area_responsible = TeamArea.objects.create(text="Area")
        metric = Metric.objects.create(text="Metric", activity=activity_associated, number_of_editors=10, is_operation=True)

        data = {
            "wikipedia_created": 0, "wikipedia_edited": 0,
            "commons_created": 0, "commons_edited": 0,
            "wikidata_created": 0, "wikidata_edited": 0,
            "wikiversity_created": 0, "wikiversity_edited": 0,
            "wikibooks_created": 0, "wikibooks_edited": 0,
            "wikisource_created": 0, "wikisource_edited": 0,
            "wikinews_created": 0, "wikinews_edited": 0,
            "wikiquote_created": 0, "wikiquote_edited": 0,
            "wiktionary_created": 0, "wiktionary_edited": 0,
            "wikivoyage_created": 0, "wikivoyage_edited": 0,
            "wikispecies_created": 0, "wikispecies_edited": 0,
            "metawiki_created": 0, "metawiki_edited": 0,
            "mediawiki_created": 0, "mediawiki_edited": 0,
            "participants": 0, "resources": 0, "feedbacks": 0,
            "number_of_people_reached_through_social_media": 0,
            "description": "Report",
            "initial_date": datetime.now().date().strftime("%Y-%m-%d"),
            "directions_related": [direction.id],
            "learning": "Learnings!" * 51,
            "learning_questions_related": [slq.id],
            "activity_associated": activity_associated.id,
            "area_responsible": area_responsible.id,
            "links": "Links",
            "metrics_related": [metric.id],
            "organizers_string": "Organizer 1;Institution 1;Institution 2",
            "donors": 0,
            "submissions": 0
        }
        form = NewReportForm(data, user=self.user)
        self.assertTrue(form.is_valid())

        operation_data = {
            "Operation-TOTAL_FORMS": 1,
            "Operation-INITIAL_FORMS": 0,
            "Operation-MIN_NUM_FORMS": 0,
            "Operation-MAX_NUM_FORMS": 1000,
            "Operation-0-metric": metric.id,
            "Operation-0-number_of_people_reached_through_social_media": 1,
            "Operation-0-number_of_new_followers": 2,
            "Operation-0-number_of_mentions": 3,
            "Operation-0-number_of_community_communications": 0,
            "Operation-0-number_of_events": 4,
            "Operation-0-number_of_resources": 5,
            "Operation-0-number_of_partnerships_activated": 6,
            "Operation-0-number_of_new_partnerships": 0
        }

        data.update(operation_data)
        response_1 = self.client.post(url, data=data)
        self.assertEqual(Report.objects.count(), 1)
        response_2 = self.client.post(url, data=data)
        self.assertEqual(Report.objects.count(), 1)
        self.assertIn(_("It seems that you already submitted this report!"), response_2.content.decode('utf-8'))

    def test_delete_report_fails_if_user_doesnt_have_permission(self):
        activity_associated = Activity.objects.create(text="Activity")
        area_responsible = TeamArea.objects.create(text="Area")

        report_1 = Report.objects.create(description="Report 1",
                                         created_by=self.user_profile,
                                         modified_by=self.user_profile,
                                         initial_date=datetime.now().date(),
                                         learning="Learnings!" * 51,
                                         activity_associated=activity_associated,
                                         area_responsible=area_responsible,
                                         links="Links")

        self.user.user_permissions.remove(self.delete_permission)
        self.client.login(username=self.username, password=self.password)
        url = reverse("report:delete_report", kwargs={"report_id": report_1.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={reverse('report:delete_report', kwargs={'report_id': report_1.id})}")

    def test_delete_report_view_get(self):
        activity_associated = Activity.objects.create(text="Activity")
        area_responsible = TeamArea.objects.create(text="Area")

        report_1 = Report.objects.create(description="Report 1",
                                         created_by=self.user_profile,
                                         modified_by=self.user_profile,
                                         initial_date=datetime.now().date(),
                                         learning="Learnings!" * 51,
                                         activity_associated=activity_associated,
                                         area_responsible=area_responsible,
                                         links="Links")
        self.client.login(username=self.username, password=self.password)
        url = reverse("report:delete_report", kwargs={"report_id": report_1.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["report"], Report)

    def test_delete_report_view_post(self):
        activity_associated = Activity.objects.create(text="Activity")
        area_responsible = TeamArea.objects.create(text="Area")

        report_1 = Report.objects.create(description="Report 1",
                                         created_by=self.user_profile,
                                         modified_by=self.user_profile,
                                         initial_date=datetime.now().date(),
                                         learning="Learnings!" * 51,
                                         activity_associated=activity_associated,
                                         area_responsible=area_responsible,
                                         links="Links")
        self.assertEqual(Report.objects.count(), 1)
        self.client.login(username=self.username, password=self.password)
        url = reverse("report:delete_report", kwargs={"report_id": report_1.id})
        response = self.client.post(url)

        self.assertEqual(Report.objects.count(), 0)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("report:list_reports"), target_status_code=302)

    def test_get_or_create_editors_with_empty_string(self):
        editors_string = ""
        result = get_or_create_editors(editors_string)
        self.assertFalse(result)

    def test_get_or_create_editors_with_usernames_of_new_editors_creates_editors(self):
        editors_string = "New editor 1\r\nNew editor 2"
        result = get_or_create_editors(editors_string)
        for editor in result:
            self.assertTrue(Editor.objects.filter(username=editor.username).exists())

    def test_get_or_create_editors_with_usernames_of_existing_editors_do_not_duplicate_editors(self):
        Editor.objects.create(username="New editor 1")
        editors_string = "New editor 1\r\nNew editor 2"
        self.assertEqual(Editor.objects.count(), 1)
        result = get_or_create_editors(editors_string)

        for editor in result:
            self.assertTrue(Editor.objects.filter(username=editor.username).exists())

        self.assertEqual(Editor.objects.count(), 2)

    def test_get_or_create_organizers_with_empty_string(self):
        organizers_string = ""
        result = get_or_create_organizers(organizers_string)
        self.assertFalse(result)

    def test_get_or_create_organizers_creates_organizers(self):
        organizers_string = "New organizer 1\r\nNew organizer 2"
        result = get_or_create_organizers(organizers_string)
        for organizer in result:
            self.assertTrue(Organizer.objects.filter(name=organizer.name).exists())

    def test_get_or_create_organizers_do_not_duplicate_organizers(self):
        institution = Partner.objects.create(name="Partner")
        organizer_1 = Organizer.objects.create(name="New organizer 1")
        organizer_1.institution.add(institution)
        organizers_string = "New organizer 1\r\nNew organizer 2"
        result = get_or_create_organizers(organizers_string)
        for organizer in result:
            self.assertTrue(Organizer.objects.filter(name=organizer.name).exists())

    def test_get_or_create_organizers_do_not_duplicate_organizers_and_create_institutions(self):
        organizers_string = "New organizer 1;Institution 1;Institution 2\r\nNew organizer 2;Institution 3"
        result = get_or_create_organizers(organizers_string)

        expected_result = {
            "New organizer 1": ["Institution 1", "Institution 2"],
            "New organizer 2": ["Institution 3"],
        }

        for organizer in result:
            expected_partners = expected_result.get(organizer.name)
            expected_queryset = Partner.objects.filter(name__in=expected_partners)
            self.assertQuerySetEqual(organizer.institution.all(), expected_queryset, ordered=False)

    def test_get_metrics_with_activities_plan_activity(self):
        project = Project.objects.create(text="Activities plan")
        area = Area.objects.create(text="Area")
        area.project.add(project)
        area.save()
        Activity.objects.create(text="Other")
        activity = Activity.objects.create(text="Activity 2", area=area)
        Metric.objects.create(activity=activity, text="Metric 1")

        self.client.login(username=self.username, password=self.password)
        url = reverse("report:get_metrics")
        response = self.client.get(url, {"activity": activity.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["objects"][0]["project"], "Activities plan")
        self.assertEqual(response.json()["objects"][0]["metrics"][0]["activity_id"], activity.id)

    def test_get_metrics_with_activity_not_from_the_activities_plan_and_metric_associated_to_project(self):
        activities_plan = Project.objects.create(text="Activities plan")
        project = Project.objects.create(text="Project")
        other_area = Area.objects.create(text="Other area")
        other_area.project.add(project)
        other_area.save()
        other_activity = Activity.objects.create(text="Other")
        metric=Metric.objects.create(activity=other_activity, text="Metric 1")
        metric.project.add(project)
        metric.save()

        area = Area.objects.create(text="Area")
        area.project.add(activities_plan)
        area.save()
        activity = Activity.objects.create(text="Activity", area=area)
        Metric.objects.create(activity=activity, text="Metric 2")

        self.client.login(username=self.username, password=self.password)
        url = reverse("report:get_metrics")
        response = self.client.get(url, {"activity": other_activity.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["objects"][0]["project"], "Project")
        self.assertEqual(response.json()["objects"][0]["metrics"][0]["activity_id"], other_activity.id)
        self.assertNotEqual(response.json()["objects"][0]["project"], "Activities plan")
        self.assertNotEqual(response.json()["objects"][0]["metrics"][0]["activity_id"], activity.id)

    def test_get_metrics_with_activity_not_from_the_activities_plan_and_metric_not_associated_to_project(self):
        activities_plan = Project.objects.create(text="Activities plan")
        project = Project.objects.create(text="Project")
        other_area = Area.objects.create(text="Other area")
        other_area.project.add(project)
        other_area.save()
        other_activity = Activity.objects.create(text="Other")
        Metric.objects.create(activity=other_activity, text="Metric 1")

        area = Area.objects.create(text="Area")
        area.project.add(activities_plan)
        area.save()
        activity = Activity.objects.create(text="Activity", area=area)
        Metric.objects.create(activity=activity, text="Metric 2")

        self.client.login(username=self.username, password=self.password)
        url = reverse("report:get_metrics")
        response = self.client.get(url, {"activity": other_activity.id})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["objects"])

    def test_get_metrics_based_on_fundings_associated(self):
        Project.objects.create(text="Activities plan")
        project_1 = Project.objects.create(text="Project 1")
        project_2 = Project.objects.create(text="Project 2")
        funding_1 = Funding.objects.create(name="Funding 1", project=project_1)
        Funding.objects.create(name="Funding 2", project=project_2)
        activity_1 = Activity.objects.create(text="Activity 1")
        activity_2 = Activity.objects.create(text="Activity 2")
        metric_1 = Metric.objects.create(activity=activity_1, text="Metric 1")
        metric_1.project.add(project_1)
        metric_1.save()
        metric_2 = Metric.objects.create(activity=activity_2, text="Metric 2")
        metric_2.project.add(project_2)
        metric_2.save()

        self.client.login(username=self.username, password=self.password)
        url = reverse("report:get_metrics")
        response = self.client.get(url, {"fundings[]": [funding_1.id]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["objects"][0]["project"], "Project 1")
        self.assertEqual(response.json()["objects"][0]["metrics"][0]["activity_id"], activity_1.id)
        self.assertNotEqual(response.json()["objects"][0]["project"], "Project 2")
        self.assertNotEqual(response.json()["objects"][0]["metrics"][0]["activity_id"], activity_2.id)

    def test_get_metrics_of_report_instance(self):
        Project.objects.create(text="Activities plan")
        Project.objects.create(text="Project 1")
        Activity.objects.create(text="Other Activity")
        activity = Activity.objects.create(text="Activity")

        area_responsible = TeamArea.objects.create(text="Area")
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        StrategicLearningQuestion.objects.create(text="Strategic Learning Question",
                                                                                   learning_area=learning_area)
        metric_1 = Metric.objects.create(text="Metric 1", activity=activity)

        report_1 = Report.objects.create(description="Report 1",
                                         created_by=self.user_profile,
                                         modified_by=self.user_profile,
                                         initial_date=datetime.now().date().strftime("%Y-%m-%d"),
                                         learning="Learnings!" * 51,
                                         activity_associated=activity,
                                         area_responsible=area_responsible,
                                         links="Links")

        report_1.metrics_related.add(metric_1)
        report_1.save()

        self.client.login(username=self.username, password=self.password)
        url = reverse("report:get_metrics")
        response = self.client.get(url, {"instance": [report_1.id]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["objects"][0]["project"], "Other metrics")
        self.assertEqual(response.json()["objects"][0]["metrics"][0]["activity_id"], activity.id)

    def test_get_metrics_of_report_instance_with_other_metrics(self):
        Project.objects.create(text="Activities plan")
        project_1 = Project.objects.create(text="Project 1")
        other_activity = Activity.objects.create(text="Other Activity")
        area = Area.objects.create(text="Area")
        area.project.add(project_1)
        area.save()
        activity = Activity.objects.create(text="Activity", area=area)

        area_responsible = TeamArea.objects.create(text="Area")
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        StrategicLearningQuestion.objects.create(text="Strategic Learning Question", learning_area=learning_area)
        metric_1 = Metric.objects.create(text="Metric 1", activity=activity)
        metric_2 = Metric.objects.create(text="Metric 2", activity=other_activity)

        report_1 = Report.objects.create(description="Report 1",
                                         created_by=self.user_profile,
                                         modified_by=self.user_profile,
                                         initial_date=datetime.now().date().strftime("%Y-%m-%d"),
                                         learning="Learnings!" * 51,
                                         activity_associated=activity,
                                         area_responsible=area_responsible,
                                         links="Links")

        report_1.metrics_related.add(metric_1)
        report_1.metrics_related.add(metric_2)
        report_1.save()

        self.client.login(username=self.username, password=self.password)
        url = reverse("report:get_metrics")
        response = self.client.get(url, {"instance": [report_1.id], "activity": activity.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["objects"][0]["project"], "Project 1")
        self.assertEqual(response.json()["objects"][0]["metrics"][0]["activity_id"], activity.id)

    def test_get_metrics_without_activities(self):
        activity = Activity.objects.create(text="Activity")
        project = Project.objects.create(text="Project")
        metric = Metric.objects.create(activity=activity, text="Metric")
        metric.project.add(project)
        metric.save()

        self.client.login(username=self.username, password=self.password)
        url = reverse("report:get_metrics")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["objects"], None)

    def test_get_metrics_of_projects(self):
        activity = Activity.objects.create(text="Activity")
        project = Project.objects.create(text="Project")
        metric = Metric.objects.create(activity=activity, text="Metric")
        metric.project.add(project)
        metric.save()

        self.client.login(username=self.username, password=self.password)
        url = reverse("report:get_metrics")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["objects"], None)


class ReportViewViewTest(TestCase):
    def setUp(self):
        self.username = "testuser"
        self.password = "testpass"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.user_profile = UserProfile.objects.filter(user=self.user).first()
        self.change_permission = Permission.objects.get(codename="change_report")
        self.view_permission = Permission.objects.get(codename="view_report")
        self.user.user_permissions.add(self.view_permission)
        self.user.user_permissions.add(self.change_permission)

        self.activity_associated = Activity.objects.create(text="Activity")
        self.area_responsible = TeamArea.objects.create(text="Area")
        self.strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        self.directions_related = Direction.objects.create(text="Direction", strategic_axis=self.strategic_axis)
        self.learning_area = LearningArea.objects.create(text="Learning area")
        self.learning_questions_related = StrategicLearningQuestion.objects.create(text="Strategic Learning Question", learning_area=self.learning_area)
        self.metrics_related = Metric.objects.create(text="Metric", activity=self.activity_associated)

        self.report_1 = Report.objects.create(description="Report 1",
                                              created_by=self.user_profile,
                                              modified_by=self.user_profile,
                                              initial_date=datetime.now().date().strftime("%Y-%m-%d"),
                                              learning="Learnings!" * 51,
                                              activity_associated=self.activity_associated,
                                              area_responsible=self.area_responsible,
                                              links="Links")
        self.report_2 = Report.objects.create(description="Report 2",
                                              created_by=self.user_profile,
                                              modified_by=self.user_profile,
                                              initial_date=datetime.now().date().strftime("%Y-%m-%d"),
                                              learning="Learnings!" * 51,
                                              activity_associated=self.activity_associated,
                                              area_responsible=self.area_responsible,
                                              links="Links")

    def test_list_reports_is_only_possible_for_users_with_permissions(self):
        self.user.user_permissions.remove(self.view_permission)
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("report:list_reports"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={reverse('report:list_reports')}")

    def test_list_reports_show_list_of_reports(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("report:list_reports"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'report/list_reports.html')
        self.assertQuerySetEqual(response.context['dataset'], Report.objects.order_by('-created_at'))

    def test_detail_report_is_only_possible_for_users_with_permissions(self):
        self.user.user_permissions.remove(self.view_permission)
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("report:detail_report", kwargs={"report_id": self.report_1.id}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={reverse('report:detail_report', kwargs={'report_id': self.report_1.id})}")

    def test_detail_report_show_report(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("report:detail_report", kwargs={"report_id": self.report_1.id}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'report/detail_report.html')
        self.assertEqual(response.context['data'], self.report_1)

    def test_update_report_is_only_possible_for_users_with_permissions(self):
        self.user.user_permissions.remove(self.change_permission)
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(reverse('report:update_report', kwargs={'report_id': self.report_1.id}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={reverse('report:update_report', kwargs={'report_id': self.report_1.id})}")

    def test_update_locked_report_is_possible_for_users_with_permissions(self):
        change_locked_report = Permission.objects.get(codename="can_edit_locked_report")
        self.user.user_permissions.add(change_locked_report)
        self.report_1.locked = True
        self.report_1.save()

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('report:update_report', kwargs={'report_id': self.report_1.id}))

        self.assertEqual(response.status_code, 200)

    def test_update_locked_report_is_not_possible_for_users_without_permissions(self):
        self.report_1.locked = True
        self.report_1.save()

        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('report:update_report', kwargs={'report_id': self.report_1.id}))

        self.assertEqual(response.status_code, 302)


    def test_update_report_get_view(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("report:update_report", kwargs={"report_id": self.report_1.id}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'report/update_report.html')

    def test_update_report_post_with_valid_parameters(self):
        Project.objects.create(text="Wikimedia Community Fund", main_funding=True)
        self.client.login(username=self.username, password=self.password)
        url = reverse("report:update_report", kwargs={"report_id": self.report_1.id})
        data = {
            "activity_associated": self.report_1.activity_associated.id,
            "area_responsible": self.report_1.area_responsible.id,
            "initial_date": self.report_1.initial_date,
            "end_date": self.report_1.end_date,
            "description": "Updated Test Report",
            "participants": 2,
            "resources": 23,
            "feedbacks": 12,
            "learning": "Learnings!!"*49,
            "links": self.report_1.links,
            "editors_string": "new editor 1\r\nnew editor 2",
            "organizers_string": "new organizer 1\r\nnew organizer 2",
            "directions_related": [self.directions_related.id],
            "learning_questions_related": [self.learning_questions_related.id],
            "metrics_related": [self.metrics_related.id],
            "donors": 0,
            "submissions": 0
        }
        operation_data = {
            "Operation-TOTAL_FORMS": 1,
            "Operation-INITIAL_FORMS": 0,
            "Operation-MIN_NUM_FORMS": 0,
            "Operation-MAX_NUM_FORMS": 1000,
            "Operation-0-metric": self.metrics_related.id,
            "Operation-0-number_of_people_reached_through_social_media": 1,
            "Operation-0-number_of_new_followers": 2,
            "Operation-0-number_of_mentions": 3,
            "Operation-0-number_of_community_communications": 0,
            "Operation-0-number_of_events": 4,
            "Operation-0-number_of_resources": 5,
            "Operation-0-number_of_partnerships_activated": 6,
            "Operation-0-number_of_new_partnerships": 0
        }
        data.update(operation_data)

        response = self.client.post(url, data=data)
        self.report_1.refresh_from_db()
        self.assertRedirects(response, reverse("report:detail_report", kwargs={"report_id": self.report_1.id}))
        self.assertEqual(self.report_1.description, "Updated Test Report")
        self.assertEqual(self.report_1.editors.count(), 2)
        self.assertEqual(self.report_1.organizers.count(), 2)


class ReportExportViewTest(TestCase):
    def setUp(self):
        self.username = "testuser"
        self.password = "testpass"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.user_profile = UserProfile.objects.filter(user=self.user).first()
        self.view_permission = Permission.objects.get(codename="view_report")
        self.user.user_permissions.add(self.view_permission)

        self.activity_associated = Activity.objects.create(text="Activity")
        self.area_responsible = TeamArea.objects.create(text="Area")

        self.report_1 = Report.objects.create(description="Report 1",
                                              created_by=self.user_profile,
                                              modified_by=self.user_profile,
                                              initial_date=datetime.now().date(),
                                              learning="Learnings!" * 51,
                                              activity_associated=self.activity_associated,
                                              area_responsible=self.area_responsible,
                                              links="Links")
        self.report_2 = Report.objects.create(description="Report 2",
                                              created_by=self.user_profile,
                                              modified_by=self.user_profile,
                                              initial_date=datetime.now().date(),
                                              learning="Learnings!" * 51,
                                              activity_associated=self.activity_associated,
                                              area_responsible=self.area_responsible,
                                              links="Links")
        self.report_1.save()
        self.report_2.save()

        self.project = Project.objects.create(text="Project")
        self.funding_associated = Funding.objects.create(name="Funding", project=self.project, value=12)
        self.editors = Editor.objects.create(username="Editor")
        self.organizers = Organizer.objects.create(name="Organizer")
        self.partners_activated = Partner.objects.create(name="Partner")
        self.technologies_used = Technology.objects.create(name="Technology")
        self.strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        self.directions_related = Direction.objects.create(text="Direction", strategic_axis=self.strategic_axis)
        self.learning_area = LearningArea.objects.create(text="Learning area")
        self.learning_questions_related = StrategicLearningQuestion.objects.create(text="Strategic Learning Question",
                                                                                   learning_area=self.learning_area)
        self.metrics_related = Metric.objects.create(text="Metric", activity=self.activity_associated)

    def test_export_report_is_only_possible_for_users_with_permissions(self):
        self.user.user_permissions.remove(self.view_permission)
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("report:export_report", kwargs={"report_id": self.report_1.id}))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={reverse('report:export_report', kwargs={'report_id': self.report_1.id})}")

    def test_export_report_generates_a_zip_file(self):
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(reverse("report:export_report", kwargs={"report_id": self.report_1.id}))
        self.assertEqual(response.status_code, 200)
        content_type = response.headers['Content-Type']
        self.assertEqual(content_type, 'application/x-zip-compressed')

    @patch('report.views.add_csv_file')
    @patch('report.views.add_excel_file')
    def test_export_report_generates_a_zip_file_with_a_specific_structure(self, mock_add_excel_file, mock_add_csv_file):
        self.client.login(username=self.username, password=self.password)
        mock_add_csv_file.return_value = BytesIO(b'test csv data')
        mock_add_excel_file.return_value = BytesIO(b'test excel data')
        response = self.client.get(reverse("report:export_report", kwargs={"report_id": self.report_1.id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/x-zip-compressed')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=Report 1 - {}.zip'.format(datetime.today().strftime('%Y-%m-%d')))
        buffer = BytesIO(response.content)
        with zipfile.ZipFile(buffer) as zip_file:
            expected_files = [
                'csv/Report 1 - {}.csv'.format(datetime.today().strftime('%Y-%m-%d')),
                'csv/Operation report 1 - {}.csv'.format(datetime.today().strftime('%Y-%m-%d')),
                'csv/Metrics 1 - {}.csv'.format(datetime.today().strftime('%Y-%m-%d')),
                'csv/Users 1 - {}.csv'.format(datetime.today().strftime('%Y-%m-%d')),
                'csv/Areas 1 - {}.csv'.format(datetime.today().strftime('%Y-%m-%d')),
                'csv/Directions 1 - {}.csv'.format(datetime.today().strftime('%Y-%m-%d')),
                'csv/Editors 1 - {}.csv'.format(datetime.today().strftime('%Y-%m-%d')),
                'csv/Fundings 1 - {}.csv'.format(datetime.today().strftime('%Y-%m-%d')),
                'csv/Learning questions 1 - {}.csv'.format(datetime.today().strftime('%Y-%m-%d')),
                'csv/Organizers 1 - {}.csv'.format(datetime.today().strftime('%Y-%m-%d')),
                'csv/Partners 1 - {}.csv'.format(datetime.today().strftime('%Y-%m-%d')),
                'csv/Technologies 1 - {}.csv'.format(datetime.today().strftime('%Y-%m-%d')),
                'Export 1 - {}.xlsx'.format(datetime.today().strftime('%Y-%m-%d')),
            ]
            self.assertEqual(sorted(zip_file.namelist()), sorted(expected_files))
            self.assertEqual(zip_file.read(expected_files[0]), b'test csv data')
            self.assertEqual(zip_file.read(expected_files[-1]), b'test excel data')

    @patch('report.views.add_csv_file')
    @patch('report.views.add_excel_file')
    def test_export_report_generates_a_zip_file_with_a_specific_structure_without_report_id(self, mock_add_excel_file, mock_add_csv_file):
        self.client.login(username=self.username, password=self.password)
        mock_add_csv_file.return_value = BytesIO(b'test csv data')
        mock_add_excel_file.return_value = BytesIO(b'test excel data')
        response = self.client.get(reverse("report:export_all_reports"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/x-zip-compressed')
        postfix = datetime.today().strftime('%Y-%m-%d')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename=SARA - Reports - {}.zip'.format(postfix))
        buffer = BytesIO(response.content)
        with zipfile.ZipFile(buffer) as zip_file:
            expected_files = [
                'csv/Report - {}.csv'.format(postfix),
                'csv/Operation report - {}.csv'.format(postfix),
                'csv/Metrics - {}.csv'.format(postfix),
                'csv/Users - {}.csv'.format(postfix),
                'csv/Areas - {}.csv'.format(postfix),
                'csv/Directions - {}.csv'.format(postfix),
                'csv/Editors - {}.csv'.format(postfix),
                'csv/Fundings - {}.csv'.format(postfix),
                'csv/Learning questions - {}.csv'.format(postfix),
                'csv/Organizers - {}.csv'.format(postfix),
                'csv/Partners - {}.csv'.format(postfix),
                'csv/Technologies - {}.csv'.format(postfix),
                'Export - {}.xlsx'.format(postfix),
            ]
            self.assertEqual(sorted(zip_file.namelist()), sorted(expected_files))
            self.assertEqual(zip_file.read(expected_files[0]), b'test csv data')
            self.assertEqual(zip_file.read(expected_files[-1]), b'test excel data')

    @patch('report.views.add_csv_file')
    @patch('report.views.add_excel_file')
    def test_export_report_generates_a_zip_file_with_a_specific_structure_with_year(self, mock_add_excel_file,
                                                                                    mock_add_csv_file):
        self.client.login(username=self.username, password=self.password)
        mock_add_csv_file.return_value = BytesIO(b'test csv data')
        mock_add_excel_file.return_value = BytesIO(b'test excel data')
        response = self.client.get(reverse("report:export_year_reports", kwargs={"year": datetime.now().year}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/x-zip-compressed')
        postfix = datetime.today().strftime('%Y-%m-%d')
        self.assertEqual(response['Content-Disposition'],
                         'attachment; filename=SARA - Reports - {}.zip'.format(postfix))
        buffer = BytesIO(response.content)
        with zipfile.ZipFile(buffer) as zip_file:
            expected_files = [
                'csv/Report - {}.csv'.format(postfix),
                'csv/Operation report - {}.csv'.format(postfix),
                'csv/Metrics - {}.csv'.format(postfix),
                'csv/Users - {}.csv'.format(postfix),
                'csv/Areas - {}.csv'.format(postfix),
                'csv/Directions - {}.csv'.format(postfix),
                'csv/Editors - {}.csv'.format(postfix),
                'csv/Fundings - {}.csv'.format(postfix),
                'csv/Learning questions - {}.csv'.format(postfix),
                'csv/Organizers - {}.csv'.format(postfix),
                'csv/Partners - {}.csv'.format(postfix),
                'csv/Technologies - {}.csv'.format(postfix),
                'Export - {}.xlsx'.format(postfix),
            ]
            self.assertEqual(sorted(zip_file.namelist()), sorted(expected_files))
            self.assertEqual(zip_file.read(expected_files[0]), b'test csv data')
            self.assertEqual(zip_file.read(expected_files[-1]), b'test excel data')

    def test_export_report_instance(self):
        expected_header = [_('ID'), _('Created by'), _('Created at'), _('Modified by'), _('Modified at'),
                           _('Activity associated'), _('Partial report?'), _('Name of the activity'),
                           _('Reference Text'), _('Area responsible'), _('Area activated'), _('Initial date'),
                           _('End date'), _('Description'), _('Funding associated'), _('Links'),
                           _('Are there private links?'), _('Public communication'), _('Number of participants'),
                           _('Number of feedbacks'), _('Editors'), _('# Editors'), _('Organizers'), _('# Organizers'),
                           _('Partnerships activated'), _('# Partnerships activated'), _('Technologies used'),
                           _('# Donors'), _('# Submissions'), _('# Wikipedia created'), _('# Wikipedia edited'),
                           _('# Commons created'), _('# Commons edited'), _('# Wikidata created'),
                           _('# Wikidata edited'), _('# Wikiversity created'), _('# Wikiversity edited'),
                           _('# Wikibooks created'), _('# Wikibooks edited'), _('# Wikisource created'),
                           _('# Wikisource edited'), _('# Wikinews created'), _('# Wikinews edited'),
                           _('# Wikiquote created'), _('# Wikiquote edited'), _('# Wiktionary created'),
                           _('# Wiktionary edited'), _('# Wikivoyage created'), _('# Wikivoyage edited'),
                           _('# Wikispecies created'), _('# Wikispecies edited'), _('# Metawiki created'),
                           _('# Metawiki edited'), _('# MediaWiki created'), _('# MediaWiki edited'),
                           _('Directions related'), _('Learning'), _('Learning questions related'),
                           _('Metrics related')]

        area_activated = AreaActivated.objects.create(text="Area activated")
        self.report_1.area_activated.add(area_activated)
        self.report_1.funding_associated.add(self.funding_associated)
        self.report_1.editors.add(self.editors)
        self.report_1.organizers.add(self.organizers)
        self.report_1.partners_activated.add(self.partners_activated)
        self.report_1.technologies_used.add(self.technologies_used)
        self.report_1.directions_related.add(self.directions_related)
        self.report_1.learning_questions_related.add(self.learning_questions_related)
        self.report_1.metrics_related.add(self.metrics_related)
        self.report_1.save()

        expected_row = [self.report_1.id,
                        self.report_1.created_by.id,
                        pd.to_datetime(self.report_1.created_at).tz_localize(None),
                        self.report_1.modified_by.id,
                        pd.to_datetime(self.report_1.modified_at).tz_localize(None),
                        self.report_1.activity_associated.id,
                        self.report_1.partial_report,
                        self.report_1.activity_associated.text,
                        self.report_1.reference_text,
                        self.report_1.area_responsible.id,
                        "; ".join(map(str, self.report_1.area_activated.values_list("id", flat=True))),
                        self.report_1.initial_date,
                        self.report_1.end_date,
                        self.report_1.description,
                        "; ".join(map(str, self.report_1.funding_associated.values_list("id", flat=True))),
                        self.report_1.links,
                        self.report_1.private_links,
                        self.report_1.public_communication,
                        self.report_1.participants,
                        self.report_1.feedbacks,
                        "; ".join(map(str, self.report_1.editors.values_list("id", flat=True))),
                        len(list(map(str, self.report_1.editors.values_list("id", flat=True)))),
                        "; ".join(map(str, self.report_1.organizers.values_list("id", flat=True))),
                        len(list(map(str, self.report_1.organizers.values_list("id", flat=True)))),
                        "; ".join(map(str, self.report_1.partners_activated.values_list("id", flat=True))),
                        len(list(map(str, self.report_1.partners_activated.values_list("id", flat=True)))),
                        "; ".join(map(str, self.report_1.technologies_used.values_list("id", flat=True))),
                        self.report_1.donors,
                        self.report_1.submissions,
                        self.report_1.wikipedia_created,
                        self.report_1.wikipedia_edited,
                        self.report_1.commons_created,
                        self.report_1.commons_edited,
                        self.report_1.wikidata_created,
                        self.report_1.wikidata_edited,
                        self.report_1.wikiversity_created,
                        self.report_1.wikiversity_edited,
                        self.report_1.wikibooks_created,
                        self.report_1.wikibooks_edited,
                        self.report_1.wikisource_created,
                        self.report_1.wikisource_edited,
                        self.report_1.wikinews_created,
                        self.report_1.wikinews_edited,
                        self.report_1.wikiquote_created,
                        self.report_1.wikiquote_edited,
                        self.report_1.wiktionary_created,
                        self.report_1.wiktionary_edited,
                        self.report_1.wikivoyage_created,
                        self.report_1.wikivoyage_edited,
                        self.report_1.wikispecies_created,
                        self.report_1.wikispecies_edited,
                        self.report_1.metawiki_created,
                        self.report_1.metawiki_edited,
                        self.report_1.mediawiki_created,
                        self.report_1.mediawiki_edited,
                        "; ".join(map(str, self.report_1.directions_related.values_list("id", flat=True))),
                        self.report_1.learning,
                        "; ".join(map(str, self.report_1.learning_questions_related.values_list("id", flat=True))),
                        "; ".join(map(str, self.report_1.metrics_related.values_list("id", flat=True)))]

        result = export_report_instance(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_report_instance_without_report_id_returns_all_reports(self):
        expected_header = [_('ID'), _('Created by'), _('Created at'), _('Modified by'), _('Modified at'),
                           _('Activity associated'), _('Partial report?'), _('Name of the activity'),
                           _('Reference Text'), _('Area responsible'), _('Area activated'), _('Initial date'),
                           _('End date'), _('Description'), _('Funding associated'), _('Links'),
                           _('Are there private links?'), _('Public communication'), _('Number of participants'),
                           _('Number of feedbacks'), _('Editors'), _('# Editors'), _('Organizers'), _('# Organizers'),
                           _('Partnerships activated'), _('# Partnerships activated'), _('Technologies used'),
                           _('# Donors'), _('# Submissions'), _('# Wikipedia created'), _('# Wikipedia edited'),
                           _('# Commons created'), _('# Commons edited'), _('# Wikidata created'),
                           _('# Wikidata edited'), _('# Wikiversity created'), _('# Wikiversity edited'),
                           _('# Wikibooks created'), _('# Wikibooks edited'), _('# Wikisource created'),
                           _('# Wikisource edited'), _('# Wikinews created'), _('# Wikinews edited'),
                           _('# Wikiquote created'), _('# Wikiquote edited'), _('# Wiktionary created'),
                           _('# Wiktionary edited'), _('# Wikivoyage created'), _('# Wikivoyage edited'),
                           _('# Wikispecies created'), _('# Wikispecies edited'), _('# Metawiki created'),
                           _('# Metawiki edited'), _('# MediaWiki created'), _('# MediaWiki edited'),
                           _('Directions related'), _('Learning'), _('Learning questions related'),
                           _('Metrics related')]

        area_activated = [""]
        funding_associated = [""]
        editors = [""]
        organizers = [""]
        partners_activated = [""]
        technologies_used = [""]
        directions_related = [""]
        learning_questions_related = [""]
        metrics_related = [""]

        if self.report_1.area_activated:
            area_activated = self.report_1.area_activated.values_list("id", flat=True)
        if self.report_1.funding_associated:
            funding_associated = self.report_1.funding_associated.values_list("id", flat=True)
        if self.report_1.editors:
            editors = self.report_1.editors.values_list("username", flat=True)
        if self.report_1.organizers:
            organizers = self.report_1.organizers.values_list("name", flat=True)
        if self.report_1.partners_activated:
            partners_activated = self.report_1.partners_activated.values_list("name", flat=True)
        if self.report_1.technologies_used:
            technologies_used = self.report_1.technologies_used.values_list("name", flat=True)
        if self.report_1.directions_related:
            directions_related = self.report_1.directions_related.values_list("id", flat=True)
        if self.report_1.learning_questions_related:
            learning_questions_related = self.report_1.learning_questions_related.values_list("id", flat=True)
        if self.report_1.metrics_related:
            metrics_related = self.report_1.metrics_related.values_list("id", flat=True)

        expected_row_1 = [self.report_1.id,
                          self.report_1.created_by.id,
                          pd.to_datetime(self.report_1.created_at).tz_localize(None),
                          self.report_1.modified_by.id,
                          pd.to_datetime(self.report_1.modified_at).tz_localize(None),
                          self.report_1.activity_associated.id,
                          self.report_1.partial_report,
                          self.report_1.activity_associated.text,
                          self.report_1.reference_text,
                          self.report_1.area_responsible.id,
                          "; ".join(map(str, area_activated)),
                          self.report_1.initial_date,
                          self.report_1.end_date,
                          self.report_1.description,
                          "; ".join(map(str, funding_associated)),
                          self.report_1.links,
                          self.report_1.private_links,
                          self.report_1.public_communication,
                          self.report_1.participants,
                          self.report_1.feedbacks,
                          "; ".join(editors),
                          len(editors),
                          "; ".join(organizers),
                          len(organizers),
                          "; ".join(partners_activated),
                          len(partners_activated),
                          "; ".join(technologies_used),
                          self.report_1.donors,
                          self.report_1.submissions,
                          self.report_1.wikipedia_created,
                          self.report_1.wikipedia_edited,
                          self.report_1.commons_created,
                          self.report_1.commons_edited,
                          self.report_1.wikidata_created,
                          self.report_1.wikidata_edited,
                          self.report_1.wikiversity_created,
                          self.report_1.wikiversity_edited,
                          self.report_1.wikibooks_created,
                          self.report_1.wikibooks_edited,
                          self.report_1.wikisource_created,
                          self.report_1.wikisource_edited,
                          self.report_1.wikinews_created,
                          self.report_1.wikinews_edited,
                          self.report_1.wikiquote_created,
                          self.report_1.wikiquote_edited,
                          self.report_1.wiktionary_created,
                          self.report_1.wiktionary_edited,
                          self.report_1.wikivoyage_created,
                          self.report_1.wikivoyage_edited,
                          self.report_1.wikispecies_created,
                          self.report_1.wikispecies_edited,
                          self.report_1.metawiki_created,
                          self.report_1.metawiki_edited,
                          self.report_1.mediawiki_created,
                          self.report_1.mediawiki_edited,
                          "; ".join(map(str, directions_related)),
                          self.report_1.learning,
                          "; ".join(map(str, learning_questions_related)),
                          "; ".join(map(str, metrics_related))]

        if self.report_2.area_activated:
            area_activated = self.report_2.area_activated.values_list("id", flat=True)
        if self.report_2.funding_associated:
            funding_associated = self.report_2.funding_associated.values_list("id", flat=True)
        if self.report_2.editors:
            editors = self.report_2.editors.values_list("username", flat=True)
        if self.report_2.organizers:
            organizers = self.report_2.organizers.values_list("name", flat=True)
        if self.report_2.partners_activated:
            partners_activated = self.report_2.partners_activated.values_list("name", flat=True)
        if self.report_2.technologies_used:
            technologies_used = self.report_2.technologies_used.values_list("name", flat=True)
        if self.report_2.directions_related:
            directions_related = self.report_2.directions_related.values_list("id", flat=True)
        if self.report_2.learning_questions_related:
            learning_questions_related = self.report_2.learning_questions_related.values_list("id", flat=True)

        expected_row_2 = [self.report_2.id,
                          self.report_2.created_by.id,
                          pd.to_datetime(self.report_2.created_at).tz_localize(None),
                          self.report_2.modified_by.id,
                          pd.to_datetime(self.report_2.modified_at).tz_localize(None),
                          self.report_2.activity_associated.id,
                          self.report_2.partial_report,
                          self.report_2.activity_associated.text,
                          self.report_2.reference_text,
                          self.report_2.area_responsible.id,
                          "; ".join(map(str, area_activated)),
                          self.report_2.initial_date,
                          self.report_2.end_date,
                          self.report_2.description,
                          "; ".join(map(str, funding_associated)),
                          self.report_2.links,
                          self.report_2.private_links,
                          self.report_2.public_communication,
                          self.report_2.participants,
                          self.report_2.feedbacks,
                          "; ".join(editors),
                          len(editors),
                          "; ".join(organizers),
                          len(organizers),
                          "; ".join(partners_activated),
                          len(partners_activated),
                          "; ".join(technologies_used),
                          self.report_2.donors,
                          self.report_2.submissions,
                          self.report_2.wikipedia_created,
                          self.report_2.wikipedia_edited,
                          self.report_2.commons_created,
                          self.report_2.commons_edited,
                          self.report_2.wikidata_created,
                          self.report_2.wikidata_edited,
                          self.report_2.wikiversity_created,
                          self.report_2.wikiversity_edited,
                          self.report_2.wikibooks_created,
                          self.report_2.wikibooks_edited,
                          self.report_2.wikisource_created,
                          self.report_2.wikisource_edited,
                          self.report_2.wikinews_created,
                          self.report_2.wikinews_edited,
                          self.report_2.wikiquote_created,
                          self.report_2.wikiquote_edited,
                          self.report_2.wiktionary_created,
                          self.report_2.wiktionary_edited,
                          self.report_2.wikivoyage_created,
                          self.report_2.wikivoyage_edited,
                          self.report_2.wikispecies_created,
                          self.report_2.wikispecies_edited,
                          self.report_2.metawiki_created,
                          self.report_2.metawiki_edited,
                          self.report_2.mediawiki_created,
                          self.report_2.mediawiki_edited,
                          "; ".join(map(str, directions_related)),
                          self.report_2.learning,
                          "; ".join(map(str, learning_questions_related))]

        expected_rows = [expected_row_1, expected_row_2]
        expected_df = pd.DataFrame(expected_rows, columns=expected_header)
        result = export_report_instance()
        self.assertTrue(result[result.isin(expected_df)].equals(expected_df))

    def test_export_report_instance_without_many_to_many_relations(self):
        expected_header = [_('ID'), _('Created by'), _('Created at'), _('Modified by'), _('Modified at'),
                           _('Activity associated'), _('Partial report?'), _('Name of the activity'),
                           _('Reference Text'), _('Area responsible'), _('Area activated'), _('Initial date'),
                           _('End date'), _('Description'), _('Funding associated'), _('Links'),
                           _('Are there private links?'), _('Public communication'), _('Number of participants'),
                           _('Number of feedbacks'), _('Editors'), _('# Editors'), _('Organizers'), _('# Organizers'),
                           _('Partnerships activated'), _('# Partnerships activated'), _('Technologies used'),
                           _('# Donors'), _('# Submissions'), _('# Wikipedia created'), _('# Wikipedia edited'),
                           _('# Commons created'), _('# Commons edited'), _('# Wikidata created'),
                           _('# Wikidata edited'), _('# Wikiversity created'), _('# Wikiversity edited'),
                           _('# Wikibooks created'), _('# Wikibooks edited'), _('# Wikisource created'),
                           _('# Wikisource edited'), _('# Wikinews created'), _('# Wikinews edited'),
                           _('# Wikiquote created'), _('# Wikiquote edited'), _('# Wiktionary created'),
                           _('# Wiktionary edited'), _('# Wikivoyage created'), _('# Wikivoyage edited'),
                           _('# Wikispecies created'), _('# Wikispecies edited'), _('# Metawiki created'),
                           _('# Metawiki edited'), _('# MediaWiki created'), _('# MediaWiki edited'),
                           _('Directions related'), _('Learning'), _('Learning questions related'),
                           _('Metrics related')]

        expected_row = [self.report_1.id,
                        self.report_1.created_by.id,
                        pd.to_datetime(self.report_1.created_at).tz_localize(None),
                        self.report_1.modified_by.id,
                        pd.to_datetime(self.report_1.modified_at).tz_localize(None),
                        self.report_1.activity_associated.id,
                        self.report_1.partial_report,
                        self.report_1.activity_associated.text,
                        self.report_1.reference_text,
                        self.report_1.area_responsible.id,
                        "",
                        self.report_1.initial_date,
                        self.report_1.end_date,
                        self.report_1.description,
                        "",
                        self.report_1.links,
                        self.report_1.private_links,
                        self.report_1.public_communication,
                        self.report_1.participants,
                        self.report_1.feedbacks,
                        "",
                        0,
                        "",
                        0,
                        "",
                        0,
                        "",
                        self.report_1.donors,
                        self.report_1.submissions,
                        self.report_1.wikipedia_created,
                        self.report_1.wikipedia_edited,
                        self.report_1.commons_created,
                        self.report_1.commons_edited,
                        self.report_1.wikidata_created,
                        self.report_1.wikidata_edited,
                        self.report_1.wikiversity_created,
                        self.report_1.wikiversity_edited,
                        self.report_1.wikibooks_created,
                        self.report_1.wikibooks_edited,
                        self.report_1.wikisource_created,
                        self.report_1.wikisource_edited,
                        self.report_1.wikinews_created,
                        self.report_1.wikinews_edited,
                        self.report_1.wikiquote_created,
                        self.report_1.wikiquote_edited,
                        self.report_1.wiktionary_created,
                        self.report_1.wiktionary_edited,
                        self.report_1.wikivoyage_created,
                        self.report_1.wikivoyage_edited,
                        self.report_1.wikispecies_created,
                        self.report_1.wikispecies_edited,
                        self.report_1.metawiki_created,
                        self.report_1.metawiki_edited,
                        self.report_1.mediawiki_created,
                        self.report_1.mediawiki_edited,
                        "",
                        self.report_1.learning,
                        "",
                        ""]

        result = export_report_instance(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_metrics(self):
        expected_header = [_('ID'), _('Metric'), _('Activity ID'), _('Activity'), _('Activity code'),
                           _('Number of editors'), _('Number of participants'), _('Number of partnerships activated'),
                           _('Number of feedbacks'), _('Number of events'), _('Other type? Which?'), _('Observation'),
                           _('# Wikipedia created'), _('# Wikipedia edited'), _('# Commons created'),
                           _('# Commons edited'), _('# Wikidata created'), _('# Wikidata edited'),
                           _('# Wikiversity created'), _('# Wikiversity edited'), _('# Wikibooks created'),
                           _('# Wikibooks edited'), _('# Wikisource created'), _('# Wikisource edited'),
                           _('# Wikinews created'), _('# Wikinews edited'), _('# Wikiquote created'),
                           _('# Wikiquote edited'), _('# Wiktionary created'), _('# Wiktionary edited'),
                           _('# Wikivoyage created'), _('# Wikivoyage edited'), _('# Wikispecies created'),
                           _('# Wikispecies edited'), _('# Metawiki created'), _('# Metawiki edited'),
                           _('# MediaWiki created'), _('# MediaWiki edited')]

        expected_row = [self.metrics_related.id,
                        self.metrics_related.text,
                        self.metrics_related.activity_id,
                        self.metrics_related.activity.text,
                        self.metrics_related.activity.code,
                        self.metrics_related.number_of_editors,
                        self.metrics_related.number_of_participants,
                        self.metrics_related.number_of_partnerships_activated,
                        self.metrics_related.number_of_feedbacks,
                        self.metrics_related.number_of_events,
                        self.metrics_related.other_type,
                        self.metrics_related.observation,
                        self.metrics_related.wikipedia_created,
                        self.metrics_related.wikipedia_edited,
                        self.metrics_related.commons_created,
                        self.metrics_related.commons_edited,
                        self.metrics_related.wikidata_created,
                        self.metrics_related.wikidata_edited,
                        self.metrics_related.wikiversity_created,
                        self.metrics_related.wikiversity_edited,
                        self.metrics_related.wikibooks_created,
                        self.metrics_related.wikibooks_edited,
                        self.metrics_related.wikisource_created,
                        self.metrics_related.wikisource_edited,
                        self.metrics_related.wikinews_created,
                        self.metrics_related.wikinews_edited,
                        self.metrics_related.wikiquote_created,
                        self.metrics_related.wikiquote_edited,
                        self.metrics_related.wiktionary_created,
                        self.metrics_related.wiktionary_edited,
                        self.metrics_related.wikivoyage_created,
                        self.metrics_related.wikivoyage_edited,
                        self.metrics_related.wikispecies_created,
                        self.metrics_related.wikispecies_edited,
                        self.metrics_related.metawiki_created,
                        self.metrics_related.metawiki_edited,
                        self.metrics_related.mediawiki_created,
                        self.metrics_related.mediawiki_edited]

        result = export_metrics(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_metrics_without_report_id_returns_metrics_from_all_reports(self):
        expected_header = [_('ID'), _('Metric'), _('Activity ID'), _('Activity'), _('Activity code'),
                           _('Number of editors'), _('Number of participants'), _('Number of partnerships activated'),
                           _('Number of feedbacks'), _('Number of events'), _('Other type? Which?'), _('Observation'),
                           _('# Wikipedia created'), _('# Wikipedia edited'), _('# Commons created'),
                           _('# Commons edited'), _('# Wikidata created'), _('# Wikidata edited'),
                           _('# Wikiversity created'), _('# Wikiversity edited'), _('# Wikibooks created'),
                           _('# Wikibooks edited'), _('# Wikisource created'), _('# Wikisource edited'),
                           _('# Wikinews created'), _('# Wikinews edited'), _('# Wikiquote created'),
                           _('# Wikiquote edited'), _('# Wiktionary created'), _('# Wiktionary edited'),
                           _('# Wikivoyage created'), _('# Wikivoyage edited'), _('# Wikispecies created'),
                           _('# Wikispecies edited'), _('# Metawiki created'), _('# Metawiki edited'),
                           _('# MediaWiki created'), _('# MediaWiki edited')]

        metric_2 = Metric.objects.create(text="Metric 2", activity=self.activity_associated)
        expected_row_1 = [self.metrics_related.id, self.metrics_related.text, self.metrics_related.activity_id, self.metrics_related.activity.text, self.metrics_related.activity.code, self.metrics_related.number_of_editors, self.metrics_related.number_of_participants, self.metrics_related.number_of_partnerships_activated, self.metrics_related.number_of_feedbacks, self.metrics_related.number_of_events, self.metrics_related.other_type, self.metrics_related.observation, self.metrics_related.wikipedia_created, self.metrics_related.wikipedia_edited, self.metrics_related.commons_created, self.metrics_related.commons_edited, self.metrics_related.wikidata_created, self.metrics_related.wikidata_edited, self.metrics_related.wikiversity_created, self.metrics_related.wikiversity_edited, self.metrics_related.wikibooks_created, self.metrics_related.wikibooks_edited, self.metrics_related.wikisource_created, self.metrics_related.wikisource_edited, self.metrics_related.wikinews_created, self.metrics_related.wikinews_edited, self.metrics_related.wikiquote_created, self.metrics_related.wikiquote_edited, self.metrics_related.wiktionary_created, self.metrics_related.wiktionary_edited, self.metrics_related.wikivoyage_created, self.metrics_related.wikivoyage_edited, self.metrics_related.wikispecies_created, self.metrics_related.wikispecies_edited, self.metrics_related.metawiki_created, self.metrics_related.metawiki_edited, self.metrics_related.mediawiki_created, self.metrics_related.mediawiki_edited]
        expected_row_2 = [metric_2.id, metric_2.text, metric_2.activity_id, metric_2.activity.text, metric_2.activity.code, metric_2.number_of_editors, metric_2.number_of_participants, metric_2.number_of_partnerships_activated, metric_2.number_of_feedbacks, metric_2.number_of_events, metric_2.other_type, metric_2.observation, metric_2.wikipedia_created, metric_2.wikipedia_edited, metric_2.commons_created, metric_2.commons_edited, metric_2.wikidata_created, metric_2.wikidata_edited, metric_2.wikiversity_created, metric_2.wikiversity_edited, metric_2.wikibooks_created, metric_2.wikibooks_edited, metric_2.wikisource_created, metric_2.wikisource_edited, metric_2.wikinews_created, metric_2.wikinews_edited, metric_2.wikiquote_created, metric_2.wikiquote_edited, metric_2.wiktionary_created, metric_2.wiktionary_edited, metric_2.wikivoyage_created, metric_2.wikivoyage_edited, metric_2.wikispecies_created, metric_2.wikispecies_edited, metric_2.metawiki_created, metric_2.metawiki_edited, metric_2.mediawiki_created, metric_2.mediawiki_edited]

        expected_rows = [expected_row_1, expected_row_2]
        expected_df = pd.DataFrame(expected_rows, columns=expected_header)
        result = export_metrics()
        self.assertTrue(result[result.isin(expected_df)].equals(expected_df))

    def test_export_user_profile(self):
        expected_header = [_('ID'), _('First name'), _('Last Name'), _('Username on Wiki (WMB)'), _('Username on Wiki'),
                           _('Photograph'), _('Position'), _('Twitter'), _('Facebook'), _('Instagram'), _('Email'),
                           _('Wikidata item'), _('LinkedIn'), _('Lattes'), _('Orcid'), _('Google_scholar')]

        user_profile = self.report_1.created_by
        expected_row = [user_profile.id,
                        user_profile.user.first_name or "",
                        user_profile.user.last_name or "",
                        user_profile.professional_wiki_handle or "",
                        user_profile.personal_wiki_handle or "",
                        user_profile.photograph or "",
                        user_profile.position or "",
                        user_profile.twitter or "",
                        user_profile.facebook or "",
                        user_profile.instagram or "",
                        user_profile.user.email or "",
                        user_profile.wikidata_item or "",
                        user_profile.linkedin or "",
                        user_profile.lattes or "",
                        user_profile.orcid or "",
                        user_profile.google_scholar or ""]

        result = export_user_profile(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_user_profile_without_report_id_returns_all_user_profiles(self):
        expected_header = [_('ID'), _('First name'), _('Last Name'), _('Username on Wiki (WMB)'), _('Username on Wiki'),
                           _('Photograph'), _('Position'), _('Twitter'), _('Facebook'), _('Instagram'), _('Email'),
                           _('Wikidata item'), _('LinkedIn'), _('Lattes'), _('Orcid'), _('Google_scholar')]

        user_profile_1 = self.report_1.created_by

        username = "testuser2"
        password = "testpass2"
        user_2 = User.objects.create_user(username=username, password=password)
        user_profile_2 = UserProfile.objects.filter(user=user_2).first()
        self.report_2.created_by = user_profile_2
        self.report_2.save()

        expected_row_1 = [user_profile_1.id, user_profile_1.user.first_name or "", user_profile_1.user.last_name or "", user_profile_1.professional_wiki_handle or "", user_profile_1.personal_wiki_handle or "", user_profile_1.photograph or "", user_profile_1.position or "", user_profile_1.twitter or "", user_profile_1.facebook or "", user_profile_1.instagram or "", user_profile_1.user.email or "", user_profile_1.wikidata_item or "", user_profile_1.linkedin or "", user_profile_1.lattes or "", user_profile_1.orcid or "", user_profile_1.google_scholar or ""]
        expected_row_2 = [user_profile_2.id, user_profile_2.user.first_name or "", user_profile_2.user.last_name or "", user_profile_2.professional_wiki_handle or "", user_profile_2.personal_wiki_handle or "", user_profile_2.photograph or "", user_profile_2.position or "", user_profile_2.twitter or "", user_profile_2.facebook or "", user_profile_2.instagram or "", user_profile_2.user.email or "", user_profile_2.wikidata_item or "", user_profile_2.linkedin or "", user_profile_2.lattes or "", user_profile_2.orcid or "", user_profile_2.google_scholar or ""]
        expected_rows = [expected_row_1, expected_row_2]
        expected_df = pd.DataFrame(expected_rows, columns=expected_header).reset_index(drop=True)
        result = export_user_profile().reset_index(drop=True)
        self.assertTrue(result[result.isin(expected_df)].equals(expected_df))

    def test_export_area_activated(self):
        expected_header = [_('ID'), _('Area activated'), _('Contact')]

        area_activated = AreaActivated.objects.create(text="Area activated")
        self.report_1.area_activated.add(area_activated)
        expected_row_1 = [self.area_responsible.id, self.area_responsible.text, AreaActivated.objects.get(text=self.area_responsible.text).contact]
        expected_row_2 = [area_activated.id, area_activated.text, area_activated.contact]

        expected_rows = [expected_row_1, expected_row_2]
        expected_df = pd.DataFrame(expected_rows, columns=expected_header)
        result = export_area_activated(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_df)].equals(expected_df))

    def test_export_area_activated_without_report_id_returns_areas_activated_from_all_reports(self):
        expected_header = [_('ID'), _('Area activated'), _('Contact')]

        area_activated_1 = AreaActivated.objects.create(text="Area activated")
        self.report_1.area_activated.add(area_activated_1)

        area_activated_2 = AreaActivated.objects.create(text="Area activated")
        self.report_2.area_activated.add(area_activated_2)

        expected_row_0 = [self.area_responsible.id, self.area_responsible.text, AreaActivated.objects.get(text=self.area_responsible.text).contact]
        expected_row_1 = [area_activated_1.id, area_activated_1.text, area_activated_1.contact]
        expected_row_2 = [area_activated_2.id, area_activated_2.text, area_activated_2.contact]

        expected_rows = [expected_row_0, expected_row_1, expected_row_2]
        expected_df = pd.DataFrame(expected_rows, columns=expected_header)
        result = export_area_activated()
        self.assertTrue(result.equals(expected_df))

    def test_export_directions_related(self):
        expected_header = [_('ID'), _('Direction related'), _('Strategic axis ID'), _('Strategic axis text')]

        strategic_axis = StrategicAxis.objects.create(text="Strategic axis")
        directions_related = Direction.objects.create(text="Area activated", strategic_axis=strategic_axis)

        self.report_1.directions_related.add(directions_related)
        expected_row = [directions_related.id,
                        directions_related.text,
                        directions_related.strategic_axis_id,
                        directions_related.strategic_axis.text]

        result = export_directions_related(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_directions_related_without_report_id_returns_directions_related_from_all_reports(self):
        expected_header = [_('ID'), _('Direction related'), _('Strategic axis ID'), _('Strategic axis text')]

        strategic_axis = StrategicAxis.objects.create(text="Strategic axis")
        directions_related_1 = Direction.objects.create(text="Area activated", strategic_axis=strategic_axis)
        directions_related_2 = Direction.objects.create(text="Area activated 2", strategic_axis=strategic_axis)

        self.report_1.directions_related.add(directions_related_1)
        self.report_2.directions_related.add(directions_related_2)
        expected_row_1 = [directions_related_1.id, directions_related_1.text, directions_related_1.strategic_axis_id, directions_related_1.strategic_axis.text]
        expected_row_2 = [directions_related_2.id, directions_related_2.text, directions_related_2.strategic_axis_id, directions_related_2.strategic_axis.text]

        expected_rows = [expected_row_1, expected_row_2]
        expected_df = pd.DataFrame(expected_rows, columns=expected_header)
        result = export_directions_related()
        self.assertTrue(result[result.isin(expected_df)].equals(expected_df))

    def test_export_editors(self):
        expected_header = [_('ID'), _('Username'), _('Number of reports including this editor')]

        editor = Editor.objects.create(username="Editor")
        self.report_1.editors.add(editor)
        expected_row = [editor.id,
                        editor.username,
                        editor.editors.count()]

        result = export_editors(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_editors_without_report_id_returns_editos_from_all_reports(self):
        expected_header = [_('ID'), _('Username'), _('Number of reports including this editor')]

        editor_1 = Editor.objects.create(username="Editor 1")
        editor_2 = Editor.objects.create(username="Editor 2")
        self.report_1.editors.add(editor_1)
        self.report_2.editors.add(editor_2)
        expected_row_1 = [editor_1.id, editor_1.username, editor_1.editors.count()]
        expected_row_2 = [editor_2.id, editor_2.username, editor_2.editors.count()]

        expected_rows = [expected_row_1, expected_row_2]
        expected_df = pd.DataFrame(expected_rows, columns=expected_header)
        result = export_editors()
        self.assertTrue(result[result.isin(expected_df)].equals(expected_df))

    def test_export_learning_questions_related(self):
        expected_header = [_('ID'), _('Learning question'), _('Learning area ID'), _('Learning area')]

        learning_area = LearningArea.objects.create(text="Learning area")
        learning_questions_related = StrategicLearningQuestion.objects.create(text="Strategic learning question", learning_area=learning_area)
        self.report_1.learning_questions_related.add(learning_questions_related)
        expected_row = [learning_questions_related.id,
                        learning_questions_related.text,
                        learning_questions_related.learning_area_id,
                        learning_questions_related.learning_area.text]

        result = export_learning_questions_related(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_learning_questions_related_without_report_id_returns_learning_questions_from_all_reports(self):
        expected_header = [_('ID'), _('Learning question'), _('Learning area ID'), _('Learning area')]

        learning_area = LearningArea.objects.create(text="Learning area")
        learning_questions_related_1 = StrategicLearningQuestion.objects.create(text="Strategic learning question 1", learning_area=learning_area)
        learning_questions_related_2 = StrategicLearningQuestion.objects.create(text="Strategic learning question 2", learning_area=learning_area)
        self.report_1.learning_questions_related.add(learning_questions_related_1)
        self.report_2.learning_questions_related.add(learning_questions_related_2)

        expected_row_1 = [learning_questions_related_1.id, learning_questions_related_1.text, learning_questions_related_1.learning_area_id, learning_questions_related_1.learning_area.text]
        expected_row_2 = [learning_questions_related_2.id, learning_questions_related_2.text, learning_questions_related_2.learning_area_id, learning_questions_related_2.learning_area.text]
        expected_rows = [expected_row_1, expected_row_2]

        expected_df = pd.DataFrame(expected_rows, columns=expected_header)
        result = export_learning_questions_related()
        self.assertTrue(result[result.isin(expected_df)].equals(expected_df))

    def test_export_organizers(self):
        expected_header = [_('ID'), _("Organizer's name"), _("Organizer's institution ID"), _("Organizer institution's name"), _('Number of reports including this organizer')]

        partner = Partner.objects.create(name="Partner")
        organizer = Organizer.objects.create(name="Organizer")
        organizer.institution.add(partner)
        self.report_1.organizers.add(organizer)
        expected_row = [organizer.id,
                        organizer.name,
                        ";".join(map(str, organizer.institution.values_list("id", flat=True))),
                        ";".join(map(str, organizer.institution.values_list("name", flat=True))),
                        organizer.organizers.count()]

        result = export_organizers(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_organizers_without_report_id_returns_organizers_from_all_reports(self):
        expected_header = [_('ID'), _("Organizer's name"), _("Organizer's institution ID"), _("Organizer institution's name"), _('Number of reports including this organizer')]

        partner = Partner.objects.create(name="Partner")
        organizer_1 = Organizer.objects.create(name="Organizer")
        organizer_1.institution.add(partner)
        organizer_2 = Organizer.objects.create(name="Organizer")
        organizer_2.institution.add(partner)
        self.report_1.organizers.add(organizer_1)
        self.report_2.organizers.add(organizer_2)
        expected_row_1 = [organizer_1.id, organizer_1.name, ";".join(map(str, organizer_1.institution.values_list("id", flat=True))), ";".join(map(str, organizer_1.institution.values_list("name", flat=True))), organizer_1.organizers.count()]
        expected_row_2 = [organizer_2.id, organizer_2.name, ";".join(map(str, organizer_2.institution.values_list("id", flat=True))), ";".join(map(str, organizer_2.institution.values_list("name", flat=True))), organizer_2.organizers.count()]
        expected_rows = [expected_row_1, expected_row_2]

        expected_df = pd.DataFrame(expected_rows, columns=expected_header)
        result = export_organizers()
        self.assertTrue(result[result.isin(expected_df)].equals(expected_df))

    def test_partners_activated(self):
        expected_header = [_('ID'), _("Partners"), _("Partner's website"), _('Number of reports including this partner')]

        partner = Partner.objects.create(name="Partner")
        self.report_1.partners_activated.add(partner)
        expected_row = [partner.id, partner.name, partner.website, partner.partners.count()]

        result = export_partners_activated(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_partners_activated_without_report_id_returns_partners_from_all_reports(self):
        expected_header = [_('ID'), _("Partners"), _("Partner's website"), _('Number of reports including this partner')]

        partner_1 = Partner.objects.create(name="Partner 1")
        partner_2 = Partner.objects.create(name="Partner 2")
        self.report_1.partners_activated.add(partner_1)
        self.report_2.partners_activated.add(partner_2)
        expected_row_1 = [partner_1.id, partner_1.name, partner_1.website, partner_1.partners.count()]
        expected_row_2 = [partner_2.id, partner_2.name, partner_2.website, partner_2.partners.count()]
        expected_rows = [expected_row_1, expected_row_2]

        expected_df = pd.DataFrame(expected_rows, columns=expected_header)
        result = export_partners_activated()
        self.assertTrue(result[result.isin(expected_df)].equals(expected_df))

    def test_export_technologies_used(self):
        expected_header = [_('ID'), _("Technology"), _('Number of reports including this technology')]

        technology_used = Technology.objects.create(name="Technology")
        self.report_1.technologies_used.add(technology_used)
        expected_row = [technology_used.id, technology_used.name, technology_used.tecnologies.count()]

        result = export_technologies_used(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_technologies_used_without_report_id_returns_technologies_from_all_reports(self):
        expected_header = [_('ID'), _("Technology"), _('Number of reports including this technology')]

        technology_used_1 = Technology.objects.create(name="Technology 1")
        technology_used_2 = Technology.objects.create(name="Technology 2")
        self.report_1.technologies_used.add(technology_used_1)
        self.report_2.technologies_used.add(technology_used_2)
        expected_row_1 = [technology_used_1.id, technology_used_1.name, technology_used_1.tecnologies.count()]
        expected_row_2 = [technology_used_2.id, technology_used_2.name, technology_used_2.tecnologies.count()]
        expected_rows = [expected_row_1, expected_row_2]

        expected_df = pd.DataFrame(expected_rows, columns=expected_header)
        result = export_technologies_used()
        self.assertTrue(result[result.isin(expected_df)].equals(expected_df))

    def test_export_operation_reports(self):
        expected_header = [_('ID'), _('Report ID'), _('Metric ID'), _('Metric'), _('Number of people reached through social media'),
              _('Number of new followers'), _('Number of mentions'), _('Number of community communications'),
              _('Number of events'), _('Number of resources'), _('Number of partnerships activated'),
              _('Number of new partnerships')]

        operation_report = OperationReport.objects.create(metric=self.metrics_related,
                                                          report=self.report_1,
                                                          number_of_events=1,
                                                          number_of_mentions=2,
                                                          number_of_resources=3,
                                                          number_of_people_reached_through_social_media=4,
                                                          number_of_new_followers=5,
                                                          number_of_community_communications=6,
                                                          number_of_new_partnerships=7,
                                                          number_of_partnerships_activated=8)
        expected_row = [operation_report.id,
                        operation_report.report.id,
                        operation_report.metric.id,
                        operation_report.metric.text,
                        operation_report.number_of_people_reached_through_social_media,
                        operation_report.number_of_new_followers,
                        operation_report.number_of_mentions,
                        operation_report.number_of_community_communications,
                        operation_report.number_of_events,
                        operation_report.number_of_resources,
                        operation_report.number_of_partnerships_activated,
                        operation_report.number_of_new_partnerships]

        result = export_operation_report(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_operation_report_without_report_id_returns_operation_reports_from_all_reports(self):
        expected_header = [_('ID'), _('Report ID'), _('Metric ID'), _('Metric'),
                           _('Number of people reached through social media'),
                           _('Number of new followers'), _('Number of mentions'),
                           _('Number of community communications'),
                           _('Number of events'), _('Number of resources'), _('Number of partnerships activated'),
                           _('Number of new partnerships')]

        operation_report_1 = OperationReport.objects.create(metric=self.metrics_related,
                                                            report=self.report_1,
                                                            number_of_events=1,
                                                            number_of_mentions=2,
                                                            number_of_resources=3,
                                                            number_of_people_reached_through_social_media=4,
                                                            number_of_new_followers=5,
                                                            number_of_community_communications=6,
                                                            number_of_new_partnerships=7,
                                                            number_of_partnerships_activated=8)
        operation_report_2 = OperationReport.objects.create(metric=self.metrics_related,
                                                            report=self.report_2,
                                                            number_of_events=1,
                                                            number_of_mentions=2,
                                                            number_of_resources=3,
                                                            number_of_people_reached_through_social_media=4,
                                                            number_of_new_followers=5,
                                                            number_of_community_communications=6,
                                                            number_of_new_partnerships=7,
                                                            number_of_partnerships_activated=8)
        expected_row_1 = [operation_report_1.id,
                          operation_report_1.report.id,
                          operation_report_1.metric.id,
                          operation_report_1.metric.text,
                          operation_report_1.number_of_people_reached_through_social_media,
                          operation_report_1.number_of_new_followers,
                          operation_report_1.number_of_mentions,
                          operation_report_1.number_of_community_communications,
                          operation_report_1.number_of_events,
                          operation_report_1.number_of_resources,
                          operation_report_1.number_of_partnerships_activated,
                          operation_report_1.number_of_new_partnerships]
        expected_row_2 = [operation_report_2.id,
                          operation_report_2.report.id,
                          operation_report_2.metric.id,
                          operation_report_2.metric.text,
                          operation_report_2.number_of_people_reached_through_social_media,
                          operation_report_2.number_of_new_followers,
                          operation_report_2.number_of_mentions,
                          operation_report_2.number_of_community_communications,
                          operation_report_2.number_of_events,
                          operation_report_2.number_of_resources,
                          operation_report_2.number_of_partnerships_activated,
                          operation_report_2.number_of_new_partnerships]

        expected_rows = [expected_row_1, expected_row_2]
        expected_df = pd.DataFrame(expected_rows, columns=expected_header)
        result = export_operation_report()
        self.assertTrue(result[result.isin(expected_df)].equals(expected_df))

    def test_export_fundings_with_ordinary_project(self):
        expected_header = [_('ID'), _('Funding'), _('Value'), _('Project ID'), _('Project'), _('Active?'), _('Type of project')]

        self.report_1.funding_associated.add(self.funding_associated)
        self.report_1.save()

        expected_row = [self.funding_associated.id,
                        self.funding_associated.name,
                        float(self.funding_associated.value),
                        self.funding_associated.project.id,
                        self.funding_associated.project.text,
                        self.funding_associated.project.active_status,
                        _("Ordinary")]

        result = export_funding(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_fundings_with_poa_project(self):
        expected_header = [_('ID'), _('Funding'), _('Value'), _('Project ID'), _('Project'), _('Active?'), _('Type of project')]
        poa_project = Project.objects.create(text="POA", current_poa=True)
        funding = Funding.objects.create(name="Funding", project=poa_project, value=24)
        self.report_1.funding_associated.add(funding)
        self.report_1.save()

        expected_row = [funding.id,
                        funding.name,
                        float(funding.value),
                        funding.project.id,
                        funding.project.text,
                        funding.project.active_status,
                        _("Current Plan of Activities")]

        result = export_funding(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_fundings_with_main_funding_project(self):
        expected_header = [_('ID'), _('Funding'), _('Value'), _('Project ID'), _('Project'), _('Active?'), _('Type of project')]
        main_project = Project.objects.create(text="Main", main_funding=True)
        funding = Funding.objects.create(name="Funding", project=main_project, value=24)
        self.report_1.funding_associated.add(funding)
        self.report_1.save()

        expected_row = [funding.id,
                        funding.name,
                        float(funding.value),
                        funding.project.id,
                        funding.project.text,
                        funding.project.active_status,
                        _("Main funding")]

        result = export_funding(report_id=self.report_1.id)

        self.assertTrue(result[result.isin(expected_row)].equals(pd.DataFrame([expected_row], columns=expected_header)))

    def test_export_fundings_without_report_id_returns_fundings_from_all_reports(self):
        expected_header = [_('ID'), _('Funding'), _('Value'), _('Project ID'), _('Project'), _('Active?'), _('Type of project')]
        main_project = Project.objects.create(text="Main", main_funding=True)
        funding_2 = Funding.objects.create(name="Funding", project=main_project, value=48)
        self.report_1.funding_associated.add(self.funding_associated)
        self.report_1.save()
        self.report_2.funding_associated.add(funding_2)
        self.report_2.save()
        expected_row_1 = [self.funding_associated.id,
                          self.funding_associated.name,
                          float(self.funding_associated.value),
                          self.funding_associated.project.id,
                          self.funding_associated.project.text,
                          self.funding_associated.project.active_status,
                          _("Ordinary")]
        expected_row_2 = [funding_2.id,
                          funding_2.name,
                          float(funding_2.value),
                          funding_2.project.id,
                          funding_2.project.text,
                          funding_2.project.active_status,
                          _("Main funding")]

        expected_rows = [expected_row_1, expected_row_2]
        expected_df = pd.DataFrame(expected_rows, columns=expected_header)
        result = export_funding()
        self.assertTrue(result[result.isin(expected_df)].equals(expected_df))

    def test_export_with_no_reports_redirects_to_list_of_reports(self):
        self.client.login(username=self.username, password=self.password)
        self.report_1.delete()
        self.report_2.delete()

        url = reverse("report:export_report", kwargs={"report_id": 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response,f"{reverse('report:list_reports')}")


class ReportFormTest(TestCase):
    def setUp(self):
        self.username = "testuser"
        self.password = "testpass"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.user_profile = UserProfile.objects.filter(user=self.user).first()

    def test_clean_organizers_empty_string(self):
        form_data = {"organizers_string": ""}
        form = NewReportForm(data=form_data, user=self.user)
        cleaned_data = form.clean_organizers()
        self.assertFalse(cleaned_data)

    def test_clean_organizers_single_organizer(self):
        form_data = {"organizers_string": "Organizer 1;"}
        form = NewReportForm(data=form_data, user=self.user)
        cleaned_data = form.clean_organizers()
        self.assertEqual(len(cleaned_data), 1)
        self.assertEqual(cleaned_data[0].name, "Organizer 1")
        self.assertEqual(len(cleaned_data[0].institution.all()), 0)

    def test_clean_organizers_multiple_organizers(self):
        form_data = {"organizers_string": "Organizer 1;\r\nOrganizer 2;"}
        form = NewReportForm(data=form_data, user=self.user)
        cleaned_data = form.clean_organizers()
        self.assertEqual(len(cleaned_data), 2)
        self.assertEqual(cleaned_data[0].name, "Organizer 1")
        self.assertEqual(cleaned_data[1].name, "Organizer 2")
        self.assertEqual(len(cleaned_data[0].institution.all()), 0)
        self.assertEqual(len(cleaned_data[1].institution.all()), 0)

    def test_clean_organizers_with_already_created_organizer(self):
        Organizer.objects.create(name="Organizer 1")
        form_data = {"organizers_string": "Organizer 1;\r\nOrganizer 2;"}
        form = NewReportForm(data=form_data, user=self.user)
        cleaned_data = form.clean_organizers()
        self.assertEqual(len(cleaned_data), 2)
        self.assertEqual(cleaned_data[0].name, "Organizer 1")
        self.assertEqual(cleaned_data[1].name, "Organizer 2")
        self.assertEqual(len(cleaned_data[0].institution.all()), 0)
        self.assertEqual(len(cleaned_data[1].institution.all()), 0)

    def test_clean_organizers_single_institution(self):
        form_data = {"organizers_string": "Organizer 1;Institution 1;"}
        form = NewReportForm(data=form_data, user=self.user)
        cleaned_data = form.clean_organizers()
        self.assertEqual(len(cleaned_data), 1)
        self.assertEqual(cleaned_data[0].name, "Organizer 1")
        self.assertEqual(len(cleaned_data[0].institution.all()), 1)
        self.assertEqual(cleaned_data[0].institution.all()[0].name, "Institution 1")

    def test_clean_organizers_multiple_institutions(self):
        form_data = {"organizers_string": "Organizer 1;Institution 1;Institution 2;Institution 3;"}
        form = NewReportForm(data=form_data, user=self.user)
        cleaned_data = form.clean_organizers()
        self.assertEqual(len(cleaned_data), 1)
        self.assertEqual(cleaned_data[0].name, "Organizer 1")
        self.assertEqual(len(cleaned_data[0].institution.all()), 3)
        self.assertEqual(cleaned_data[0].institution.all()[0].name, "Institution 1")
        self.assertEqual(cleaned_data[0].institution.all()[1].name, "Institution 2")
        self.assertEqual(cleaned_data[0].institution.all()[2].name, "Institution 3")

    def test_clean_organizers_multiple_institutions_empty_partner_names(self):
        form_data = {"organizers_string": "Organizer 1;Institution 1;Institution 2;;Institution 3;;"}
        form = NewReportForm(data=form_data, user=self.user)
        cleaned_data = form.clean_organizers()
        self.assertEqual(len(cleaned_data), 1)
        self.assertEqual(cleaned_data[0].name, "Organizer 1")
        self.assertEqual(len(cleaned_data[0].institution.all()), 3)
        self.assertEqual(cleaned_data[0].institution.all()[0].name, "Institution 1")

    def test_clean_editors_with_empty_string(self):
        form_data = {"editors_string": ""}
        form = NewReportForm(data=form_data, user=self.user)
        cleaned_data = form.clean_editors()
        self.assertFalse(cleaned_data)

    def test_clean_editors_with_retained_editor(self):
        editor = Editor.objects.create(username="Editor", retained=0)
        form_data = {"editors_string": "Editor"}
        form = NewReportForm(data=form_data, user=self.user)
        cleaned_data = form.clean_editors()
        self.assertTrue(cleaned_data[0].username, editor.username)
        self.assertTrue(cleaned_data[0].retained, 1)

    def test_get_or_create_editors_empty_string(self):
        editors_string = ""
        editors = get_or_create_editors(editors_string)
        self.assertFalse(editors)

    def test_get_or_create_editors_single_editor(self):
        editors_string = "Editor 1"
        editors = get_or_create_editors(editors_string)
        self.assertEqual(len(editors), 1)
        self.assertEqual(editors[0].username, "Editor 1")

    def test_get_or_create_editors_multiple_editors(self):
        editors_string = "Editor 1\r\nEditor 2\r\nEditor 3"
        editors = get_or_create_editors(editors_string)
        self.assertEqual(len(editors), 3)
        self.assertEqual(editors[0].username, "Editor 1")
        self.assertEqual(editors[1].username, "Editor 2")
        self.assertEqual(editors[2].username, "Editor 3")

    def test_get_or_create_editors_duplicate_editors(self):
        editors_string = "Editor 1\r\nEditor 2\r\nEditor 3\r\nEditor 1"
        editors = get_or_create_editors(editors_string)
        self.assertEqual(len(editors), 3)
        self.assertEqual(editors[0].username, "Editor 1")
        self.assertEqual(editors[1].username, "Editor 2")
        self.assertEqual(editors[2].username, "Editor 3")

    def test_activities_associated_as_choices(self):
        strategic_axis = StrategicAxis.objects.create(text="Strategic axis")
        project_1 = Project.objects.create(text="Project")
        area_1 = Area.objects.create(text="Area 1")
        area_1.project.add(project_1)
        area_1.save()
        area_2 = Area.objects.create(text="Area 2")
        area_2.project.add(project_1)
        area_2.save()

        Activity.objects.create(text="Activity 1", code="Code 1", area=area_1)
        Activity.objects.create(text="Activity 2", code="Code 2", area=area_1)
        Activity.objects.create(text="Activity 3", code="Code 3", area=area_2)

        expected_result = (("Area 1", 0, ((1, "Activity 1 (Code 1)"), (2, "Activity 2 (Code 2)"))),("Area 2", 0, ((3, "Activity 3 (Code 3)"),)))
        result = activities_associated_as_choices()
        self.assertEqual(expected_result, result)

    def test_learning_areas_as_choices(self):
        learning_area_1 = LearningArea.objects.create(text="Learning area 1")
        learning_area_2 = LearningArea.objects.create(text="Learning area 2")
        StrategicLearningQuestion.objects.create(text="SLQ 1", learning_area=learning_area_1)
        StrategicLearningQuestion.objects.create(text="SLQ 2", learning_area=learning_area_1)
        StrategicLearningQuestion.objects.create(text="SLQ 3", learning_area=learning_area_2)

        expected_result = [["Learning area 1", [[1, "SLQ 1"], [2, "SLQ 2"]]],["Learning area 2", [[3, "SLQ 3"]]]]
        result = learning_areas_as_choices()
        self.assertEqual(expected_result, result)
