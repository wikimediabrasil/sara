import re
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, date
from django.test import TestCase, RequestFactory
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db.models import Q
from django.contrib.auth.models import Permission
from django.utils.translation import activate, gettext_lazy as _

from report.models import Report, Editor, OperationReport, Direction, StrategicLearningQuestion
from users.models import User, UserProfile, TeamArea
from strategy.models import StrategicAxis, LearningArea
from metrics.models import Area, Metric, Activity, Project

from metrics.views import get_metrics_and_aggregate_per_project, build_wiki_ref_for_reports, \
    show_metrics_for_specific_project, get_results_for_timespan
from metrics.templatetags.metricstags import categorize, perc, bool_yesno, is_yesno, bool_yesnopartial
from metrics.utils import render_to_pdf
from metrics.link_utils import process_all_references, unwikify_link, replace_with_links, dewikify_url, build_wiki_ref


class AreaModelTests(TestCase):
    def setUp(self):
        self.axis = StrategicAxis.objects.create(text="Strategic Axis")
        self.area = Area.objects.create(text="Area")

    def test_area_str_method_returns_area_text(self):
        self.assertEqual(str(self.area), 'Area')

    def test_area_text_cannot_be_empty(self):
        with self.assertRaises(ValidationError):
            empty_area = Area(text="")
            empty_area.full_clean()


class ActivityModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(text="Area")
        self.activity = Activity.objects.create(text="Activity", code="A1", area=self.area)

    def test_activity_str_returns_text(self):
        self.assertEqual(str(self.activity), "Activity")

    def test_activity_related_name_on_area_returns_activities(self):
        self.assertIn(self.activity, self.area.activities.all())

    def test_activity_text_cannot_be_empty(self):
        with self.assertRaises(ValidationError):
            empty_activity = Activity(text="", area=self.area)
            empty_activity.full_clean()


class ProjectModelTests(TestCase):
    def setUp(self):
        self.text = "text"
        self.status = True
        self.project = Project.objects.create(text=self.text, active_status=self.status)

    def test_project_str_returns_text(self):
        self.assertEqual(str(self.project), self.text)

    def test_project_text_cant_be_empty(self):
        with self.assertRaises(ValidationError):
            empty_project = Project(text="")
            empty_project.full_clean()


class MetricModelTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(text="Area")
        self.activity = Activity.objects.create(text="Activity", area=self.area)
        self.metric = Metric.objects.create(text="Metric", activity=self.activity)

    def test_metric_str_returns_metrics_text(self):
        self.assertEqual(str(self.metric), "Metric")

    def test_metric_instance_can_have_empty_text(self):
        with self.assertRaises(ValidationError):
            metric = Metric.objects.create(text="", activity=self.activity)
            metric.full_clean()

    def test_metric_instance_must_have_a_non_empty_text(self):
        with self.assertRaises(ValidationError):
            metric = Metric.objects.create(activity=self.activity)
            metric.full_clean()

    def test_metric_instance_must_have_an_activity_associated(self):
        with self.assertRaises(IntegrityError):
            Metric.objects.create(text="Metric2")

    def test_metric_instance_with_required_parameters_is_created(self):
        metric = Metric.objects.create(text="Metric3", activity=self.activity)
        metric.full_clean()


class MetricViewsTests(TestCase):
    def setUp(self):
        self.username = "testuser"
        self.password = "testpass"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.view_metrics_permission = Permission.objects.get(codename="view_metric")
        self.change_metrics_permission = Permission.objects.get(codename="change_metric")
        self.user.user_permissions.add(self.view_metrics_permission)
        self.user.user_permissions.add(self.change_metrics_permission)

    def test_index_view(self):
        self.index_url = reverse("metrics:index")
        response = self.client.get(self.index_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/home.html")

    def test_about_view(self):
        self.index_url = reverse("metrics:about")
        response = self.client.get(self.index_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/about.html")

    def test_show_activities_plan_view(self):
        url = reverse("metrics:show_activities")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://meta.wikimedia.org/wiki/Wikimedia_Brasil/Plan_of_Activities")

    def test_show_metrics_per_project(self):
        self.client.login(username=self.username, password=self.password)
        Project.objects.create(text="Project", current_poa=True)
        url = reverse("metrics:per_project")

        response = self.client.get(url)
        self.assertIn("dataset", str(response.context))

    def test_show_detailed_metrics_per_project_fails_if_user_doesnt_have_permission(self):
        self.client.login(username=self.username, password=self.password)
        Project.objects.create(text="Project", current_poa=True)
        url = reverse("metrics:detailed_per_project")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={url}")

    def test_show_detailed_metrics_per_project_succeeds_if_user_have_permission(self):
        permission = Permission.objects.get(codename="delete_logentry")
        self.user.user_permissions.add(permission)
        self.client.login(username=self.username, password=self.password)
        Project.objects.create(text="Project", current_poa=True)
        url = reverse("metrics:detailed_per_project")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/list_metrics_per_project.html")

    def test_show_plan_of_activities_and_its_operational_metrics_if_they_exist(self):
        self.client.login(username=self.username, password=self.password)
        project = Project.objects.create(text="Plan of activities", current_poa=True)
        area = Area.objects.create(text="Area")
        area.project.add(project)
        area.save()
        activity = Activity.objects.create(text="Activity", area=area)
        metric_1 = Metric.objects.create(text="Metric 1", text_en="Metric 1", boolean_type=True, activity=activity)
        metric_1.project.add(project)
        metric_1.save()
        metric_2 = Metric.objects.create(text="Metric 2", text_en="Metric 2", is_operation=True, activity=activity)
        metric_2.project.add(project)
        metric_2.save()

        url = reverse("metrics:per_project")
        response = self.client.get(url)
        self.assertIn("poa_dataset", str(response.context))
        self.assertEqual(response.context["poa_dataset"][1]["project_metrics"][0]["activity_metrics"][1]["title"], str(metric_1))
        self.assertEqual(response.context["poa_dataset"][1]["project_metrics"][1]["activity_metrics"][2]["title"], str(metric_2))

    def test_update_metrics(self):
        self.client.login(username=self.username, password=self.password)
        Project.objects.create(text="Plan of Activities", current_poa=True)

        area = Area.objects.create(text="Area")
        activity = Activity.objects.create(text="Activity", area=area)
        project_1 = Project.objects.create(text="Wikimedia Community Fund", main_funding=True)

        metric = Metric.objects.create(text="Metric 1", activity=activity, number_of_editors=10)
        metric.project.add(project_1)

        team_area = TeamArea.objects.create(text="Area")
        activity_1 = Activity.objects.create(text="Activity 1")
        metric_2 = Metric.objects.create(text="Metric 2", activity=activity_1, number_of_editors=9)

        report_1 = Report.objects.create(
            created_by=self.user_profile,
            modified_by=self.user_profile,
            activity_associated=activity_1,
            area_responsible=team_area,
            initial_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=1),
            description="Report 1",
            links="https://testlink.com",
            learning="Learning" * 60,
        )
        report_1.metrics_related.add(metric_2)
        report_1.save()

        url = reverse("metrics:update_metrics")
        response = self.client.get(url, follow=True)

        self.assertRedirects(response, reverse('metrics:per_project'))

    def test_do_not_show_reports_associated_to_a_metric_to_users_without_permission(self):
        self.user.user_permissions.remove(self.view_metrics_permission)
        self.client.login(username=self.username, password=self.password)

        area = Area.objects.create(text="Area")
        activity = Activity.objects.create(text="Activity", area=area)
        metric = Metric.objects.create(text="Metric 1", activity=activity, number_of_editors=10)

        url = reverse("metrics:metrics_reports", args=[metric.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={url}")

    def test_show_reports_associated_to_a_metric_only_to_users_with_permission(self):
        self.client.login(username=self.username, password=self.password)

        area = Area.objects.create(text="Area")
        activity = Activity.objects.create(text="Activity", area=area)
        metric = Metric.objects.create(text="Metric 1", activity=activity, number_of_editors=10)
        team_area = TeamArea.objects.create(text="Area")
        report_1 = Report.objects.create(
            created_by=self.user_profile,
            modified_by=self.user_profile,
            activity_associated=activity,
            area_responsible=team_area,
            initial_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=1),
            description="Report 1",
            links="https://testlink.com",
            learning="Learning" * 60,
        )
        report_1.metrics_related.add(metric)
        report_1.save()

        url = reverse("metrics:metrics_reports", args=[metric.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "metrics/list_metrics_reports.html")

    def test_redirects_to_list_of_metrics_per_project_if_metric_id_does_not_exist(self):
        self.client.login(username=self.username, password=self.password)

        project = Project.objects.create(text="Plan of Activities", current_poa=True)
        area = Area.objects.create(text="Area")
        area.project.add(project)
        area.save()
        activity = Activity.objects.create(text="Activity", area=area)
        metric = Metric.objects.create(text="Metric 1", activity=activity, number_of_editors=10)
        metric.project.add(project)
        metric.save()
        team_area = TeamArea.objects.create(text="Area")
        report_1 = Report.objects.create(
            created_by=self.user_profile,
            modified_by=self.user_profile,
            activity_associated=activity,
            area_responsible=team_area,
            initial_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=1),
            description="Report 1",
            links="https://testlink.com",
            learning="Learning" * 60,
        )
        report_1.metrics_related.add(metric)
        report_1.save()

        url = reverse("metrics:metrics_reports", args=[123456789])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('metrics:per_project')}")


class ShowMetricsForProjectTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="admin", password="pass")
        self.user.user_permissions.add(Permission.objects.get(codename="view_metric"))
        self.project = Project.objects.create(text="Test Project", current_poa=True)

    @patch("metrics.views.get_metrics_and_aggregate_per_project")
    def test_metrics_view_with_current_poa_and_data(self, mock_get_metrics):
        operational_data = { self.project.id: {"project_metrics": [1, 2]} }
        bool_data = { self.project.id: {"project_metrics": [3]} }

        def side_effect(*args, **kwargs):
            if "Occurrence" in args:
                return bool_data
            else:
                return operational_data

        mock_get_metrics.side_effect = side_effect

        request = self.factory.get("/fake-url/")
        request.user = self.user

        activate("en")

        response = show_metrics_for_specific_project(request, self.project.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Project", response.content)
        # Ensure metrics are combined
        self.assertIn(b"1", response.content)
        self.assertIn(b"3", response.content)

    @patch("metrics.views.get_metrics_and_aggregate_per_project")
    def test_metrics_view_with_current_poa_but_no_data(self, mock_get_metrics):
        mock_get_metrics.return_value = {}

        request = self.factory.get("/fake-url/")
        request.user = self.user

        response = show_metrics_for_specific_project(request, self.project.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Project", response.content)

    @patch("metrics.views.get_metrics_and_aggregate_per_project")
    def test_metrics_view_without_current_poa(self, mock_get_metrics):
        project = Project.objects.create(text="Old Project", current_poa=False)
        mock_get_metrics.return_value = {project.id: {"project_metrics": [42]}}

        operational_data = { project.id: {"project_metrics": [1, 2]} }
        bool_data = { project.id: {"project_metrics": [3]} }

        def side_effect(*args, **kwargs):
            if "Occurrence" in args:
                return bool_data
            else:
                return operational_data

        mock_get_metrics.side_effect = side_effect

        request = self.factory.get("/fake-url/")
        request.user = self.user

        activate("en")

        response = show_metrics_for_specific_project(request, project.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Old Project", response.content)
        self.assertIn(b"1", response.content)
        self.assertIn(b"3", response.content)

        mock_get_metrics.side_effect = side_effect("Occurrence")

        request_2 = self.factory.get("/fake-url/")
        request_2.user = self.user

        response = show_metrics_for_specific_project(request_2, project.id)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Old Project", response.content)
        self.assertIn(b"1", response.content)
        self.assertIn(b"3", response.content)

    def test_view_requires_permission(self):
        request = self.factory.get("/fake-url/")
        request.user = User.objects.create_user("user2", "test@example.com", "pass")
        response = self.client.get(reverse("metrics:specific_project", args=[self.project.id]))
        self.assertEqual(response.status_code, 302)


class PreparePDFViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.permission = Permission.objects.get(codename='view_metric')
        self.user.user_permissions.add(self.permission)
        self.client.login(username='testuser', password='password')
        self.project = Project.objects.create(text='Main Project', main_funding=True)

    @patch('metrics.views.get_results_for_timespan')
    @patch('metrics.views.process_all_references')
    def test_prepare_pdf_view_success(self, mock_process_refs, mock_get_results):
        mock_get_results.return_value = [
            {"metric": "Test Metric", "done": [1, 2, 3, 4, 10, "sara-123 sara-456", 20]}
        ]
        mock_process_refs.return_value = ["Reference 1", "Reference 2"]
        response = self.client.get(reverse('metrics:wmf_report'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'metrics/wmf_report.html')
        self.assertIn('metrics', response.context)

    def test_prepare_pdf_view_no_permission(self):
        self.user.user_permissions.remove(self.permission)
        response = self.client.get(reverse('metrics:wmf_report'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={reverse('metrics:wmf_report')}")

    @patch("metrics.utils.get_template")
    @patch("metrics.utils.pisa.pisaDocument")
    def test_pdf_generation_error(self, mock_pisa_doc, mock_get_template):
        # Setup: mock template rendering
        mock_template = MagicMock()
        mock_template.render.return_value = "<html><body>Error Test</body></html>"
        mock_get_template.return_value = mock_template
        mock_pdf = MagicMock()
        mock_pdf.err = True
        mock_pisa_doc.return_value = mock_pdf
        response = render_to_pdf("fake_template.html", {"key": "value"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b"Invalid PDF")
        self.assertEqual(response["Content-Type"], "text/plain")


class MetricFunctionsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.team_area = TeamArea.objects.create(text="Area")
        self.area = Area.objects.create(text="Area")
        self.activity_1 = Activity.objects.create(text="Activity 1")
        self.activity_2 = Activity.objects.create(text="Activity 2")
        self.metric_1 = Metric.objects.create(text="Metric 1", activity=self.activity_1)
        self.metric_2 = Metric.objects.create(text="Metric 2", activity=self.activity_1)
        self.metric_3 = Metric.objects.create(text="Metric 3", activity=self.activity_2)

        self.report_1 = Report.objects.create(
            created_by=self.user_profile,
            modified_by=self.user_profile,
            activity_associated=self.activity_1,
            area_responsible=self.team_area,
            initial_date=datetime.now().date(),
            end_date=datetime.now().date() + timedelta(days=1),
            description="Report 1",
            links="https://testlink.com",
            learning="Learning" * 60,
        )

        self.report_2 = Report.objects.create(
            created_by=self.user_profile,
            modified_by=self.user_profile,
            activity_associated=self.activity_1,
            area_responsible=self.team_area,
            initial_date=datetime.now().date() + timedelta(days=1),
            end_date=datetime.now().date() + timedelta(days=2),
            description="Report 2",
            links="https://testlink.com",
            learning="Learning" * 60,
        )

        self.report_3 = Report.objects.create(
            created_by=self.user_profile,
            modified_by=self.user_profile,
            activity_associated=self.activity_1,
            area_responsible=self.team_area,
            initial_date=datetime.now().date() + timedelta(days=1),
            end_date=datetime.now().date() + timedelta(days=2),
            description="Report 3",
            links="https://testlink.com",
            learning="Learning" * 60,
        )

        self.editor_1 = Editor.objects.create(username="Editor 1")
        self.editor_2 = Editor.objects.create(username="Editor 2")
        self.editor_3 = Editor.objects.create(username="Editor 3")

    def test_get_metrics_and_aggregate_per_project_with_data_and_metric_unclear_when_id_ge_1(self):
        project = Project.objects.create(text="Project")
        self.metric_3.project.add(project)
        self.metric_3.save()
        area = Area.objects.create(text="Area")
        area.project.add(project)
        area.save()
        self.activity_2.area = area
        self.activity_2.save()

        self.report_2.activity_associated = self.activity_2
        self.report_2.save()
        aggregated_metrics = get_metrics_and_aggregate_per_project()
        self.assertEqual(list(aggregated_metrics.keys())[0], project.id)
        self.assertEqual(aggregated_metrics[1]["project"], project.text)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_id"], self.activity_2.id)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity"], self.activity_2.text)
        self.assertEqual(list(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"].keys())[0], self.metric_3.id)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][3]["title"], self.metric_3.text)
        self.assertEqual(list(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][3]["metrics"].keys())[0], "Other metric")
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][3]["metrics"]["Other metric"]["goal"], "-")
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][3]["metrics"]["Other metric"]["done"], "-")

    def test_get_metrics_and_aggregate_per_project_with_data_and_metric_unclear(self):
        project = Project.objects.create(text="Project")
        self.metric_2.project.add(project)
        self.metric_2.save()
        area = Area.objects.create(text="Area")
        area.project.add(project)
        area.save()
        self.activity_1.area = area
        self.activity_1.save()
        aggregated_metrics = get_metrics_and_aggregate_per_project()
        self.assertEqual(list(aggregated_metrics.keys())[0], project.id)
        self.assertEqual(aggregated_metrics[1]["project"], project.text)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_id"], self.activity_1.id)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity"], self.activity_1.text)
        self.assertEqual(list(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"].keys())[0], self.metric_2.id)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][2]["title"], self.metric_2.text)
        self.assertEqual(list(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][2]["metrics"].keys())[0], "Other metric")
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][2]["metrics"]["Other metric"]["goal"], "-")
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][2]["metrics"]["Other metric"]["done"], "-")

    def test_get_metrics_and_aggregate_per_project_with_goal_but_none_done(self):
        project = Project.objects.create(text="Project")
        self.metric_2.project.add(project)
        self.metric_2.wikipedia_created = 500
        self.metric_2.save()
        area = Area.objects.create(text="Area")
        area.project.add(project)
        area.save()
        self.activity_1.area = area
        self.activity_1.save()
        aggregated_metrics = get_metrics_and_aggregate_per_project()
        self.assertEqual(list(aggregated_metrics.keys())[0], project.id)
        self.assertEqual(aggregated_metrics[1]["project"], project.text)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_id"], self.activity_1.id)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity"], self.activity_1.text)
        self.assertEqual(list(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"].keys())[0], self.metric_2.id)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][2]["title"], self.metric_2.text)
        self.assertEqual(list(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][2]["metrics"].keys())[0], "Wikipedia")
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][2]["metrics"]["Wikipedia"]["goal"], 500)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][2]["metrics"]["Wikipedia"]["done"], 0)

    def test_get_metrics_and_aggregate_per_project_with_goal_and_some_done(self):
        project = Project.objects.create(text="Project")
        self.metric_2.project.add(project)
        self.metric_2.wikipedia_created = 500
        self.metric_2.save()
        area = Area.objects.create(text="Area")
        area.project.add(project)
        area.save()
        self.activity_1.area = area
        self.activity_1.save()

        self.report_3.metrics_related.add(self.metric_2.id)
        self.report_3.wikipedia_edited = 200
        self.report_3.save()
        aggregated_metrics = get_metrics_and_aggregate_per_project()
        self.assertEqual(list(aggregated_metrics.keys())[0], project.id)
        self.assertEqual(aggregated_metrics[1]["project"], project.text)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_id"], self.activity_1.id)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity"], self.activity_1.text)
        self.assertEqual(list(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"].keys())[0], self.metric_2.id)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][2]["title"], self.metric_2.text)
        self.assertEqual(list(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][2]["metrics"].keys())[0], "Wikipedia")
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][2]["metrics"]["Wikipedia"]["goal"], 500)
        self.assertEqual(aggregated_metrics[1]["project_metrics"][0]["activity_metrics"][2]["metrics"]["Wikipedia"]["done"], 200)

    def test_get_metrics_and_aggregate_per_project_without_data(self):
        aggregated_metrics = get_metrics_and_aggregate_per_project()
        self.assertEqual(aggregated_metrics, {})

    def test_get_references_for_report_with_external_reference_formats_it(self):
        self.report_1.metrics_related.add(self.metric_1)
        self.report_1.save()

        response = build_wiki_ref_for_reports(self.metric_1)
        self.assertEqual(response, "<ref name=\"sara-"+str(self.report_1.id)+"\">[https://testlink.com]</ref>")

    def test_get_references_for_report_with_internal_references_formats_it(self):
        links = "https://pt.wikipedia.org/wiki/Página_inicial"
        self.report_1.metrics_related.add(self.metric_1)
        self.report_1.links = links
        self.report_1.reference_text = ""
        self.report_1.save()

        response = build_wiki_ref_for_reports(self.metric_1)
        self.assertEqual(response, "<ref name=\"sara-"+str(self.report_1.id)+"\">[[w:pt:Página_inicial|Página inicial]]</ref>")

    def test_get_references_for_report_with_reference_text_field(self):
        self.report_1.metrics_related.add(self.metric_1)
        reference_text = "Formatted reference"
        self.report_1.reference_text = reference_text
        self.report_1.save()

        response = build_wiki_ref_for_reports(self.metric_1)
        self.assertEqual(response, reference_text)

    def test_get_results_for_timespan_with_metrics_goals(self):
        self.report_1.metrics_related.add(self.metric_1)
        self.report_1.save()
        main_project = Project.objects.create(text="Main Project")
        self.metric_1.project.add(main_project)
        self.metric_1.wikipedia_created = 10
        self.metric_1.save()

        timespan_array = [
            (datetime.now().date() - timedelta(days=10), datetime.now().date() + timedelta(days=10)),
            (datetime.now().date() - timedelta(days=10), datetime.now().date() - timedelta(days=5))
        ]

        response = get_results_for_timespan(timespan_array, metric_query=Q(project=main_project), with_goal=True)
        self.assertEqual([{"activity": self.metric_1.activity.text, "metric": self.metric_1.text, "done": ["-", "-", "", 10]}], response)

    def test_get_results_for_timespan_without_metrics_goals(self):
        self.report_1.metrics_related.add(self.metric_1)
        self.report_1.save()
        main_project = Project.objects.create(text="Main Project")
        self.metric_1.project.add(main_project)
        self.metric_1.save()

        timespan_array = [
            (datetime.now().date() - timedelta(days=10), datetime.now().date() + timedelta(days=10)),
            (datetime.now().date() - timedelta(days=10), datetime.now().date() - timedelta(days=5))
        ]

        response = get_results_for_timespan(timespan_array, metric_query=Q(project=main_project), with_goal=True)
        self.assertEqual([{"activity": self.metric_1.activity.text, "metric": self.metric_1.text, "done": ["", "?"]}], response)

    def test_get_results_for_timespan_in_English(self):
        self.report_1.metrics_related.add(self.metric_1)
        self.report_1.save()
        main_project = Project.objects.create(text="Main Project")
        self.metric_1.project.add(main_project)
        self.metric_1.wikipedia_created = 10
        self.metric_1.save()

        timespan_array = [
            (datetime.now().date() - timedelta(days=10), datetime.now().date() + timedelta(days=10)),
            (datetime.now().date() - timedelta(days=10), datetime.now().date() - timedelta(days=5))
        ]

        response = get_results_for_timespan(timespan_array, metric_query=Q(project=main_project), with_goal=True, lang="en")
        self.assertEqual([{"activity": self.metric_1.activity.text, "metric": self.metric_1.text_en, "done": ["-", "-", "", 10]}], response)


class ReferencesFunctionsTests(TestCase):
    def test_single_internal_link(self):
        input_string = '<ref name="sara-123">[[Main Page|Main Page]]</ref>'
        expected = ['<li id="sara-123">123. <a target="_blank" href="https://meta.wikimedia.org/wiki/Main_Page">Main Page</a></li>']
        result = process_all_references(input_string)
        self.assertEqual(result, expected)

    def test_single_internal_link_with_alias(self):
        input_string = '<ref name="sara-456">[[Main Page|Homepage]]</ref>'
        expected = ['<li id="sara-456">456. <a target="_blank" href="https://meta.wikimedia.org/wiki/Main_Page">Homepage</a></li>']
        result = process_all_references(input_string)
        self.assertEqual(result, expected)

    def test_single_external_link(self):
        input_string = '<ref name="sara-789">[https://example.org Example]</ref>'
        expected = ['<li id="sara-789">789. <a target="_blank" href="https://example.org">Example</a></li>']
        result = process_all_references(input_string)
        self.assertEqual(result, expected)

    def test_multiple_references(self):
        input_string = (
            '<ref name="sara-1">[[Link A]]</ref> '
            'text in between '
            '<ref name="sara-2">[https://example.org Example]</ref>'
        )
        result = process_all_references(input_string)
        self.assertEqual(len(result), 2)
        self.assertIn("sara-1", result[0])
        self.assertIn("sara-2", result[1])

    def test_reference_with_bulleted_list(self):
        input_string = '<ref name="sara-99">ABC {{bulleted list|item1|item2}}</ref>'
        result = process_all_references(input_string)
        self.assertEqual(len(result), 1)
        self.assertIn("<ul>", result[0])
        self.assertIn("<li>item1</li>", result[0])
        self.assertIn("<li>item2</li>", result[0])

    def test_invalid_reference_format(self):
        input_string = 'No ref tags here'
        result = process_all_references(input_string)
        self.assertEqual(result, [])

    def test_unwikify_link(self):
        input_ref = '<ref name="sara-101">Just text</ref>'
        updated_refs = []
        match = re.match(r'<ref name="sara-\d+">.*?</ref>', input_ref)
        result = unwikify_link(match, updated_refs)

        expected = '<li id="sara-101">101. Just text</li>'
        self.assertEqual(result, expected)
        self.assertEqual(updated_refs, [expected])

    def test_unwikify_reference_with_bulleted_list(self):
        input_ref = '<ref name="sara-202">Intro {{bulleted list|A|B|C}} end</ref>'
        updated_refs = []
        match = re.match(r'<ref name="sara-\d+">.*?</ref>', input_ref)
        result = unwikify_link(match, updated_refs)

        expected = (
            '<li id="sara-202">202. Intro <ul>\n'
            '<li>A</li>\n<li>B</li>\n<li>C</li>\n</ul> end</li>'
        )
        self.assertEqual(result, expected)
        self.assertEqual(updated_refs, [expected])

    def test_unwikify_invalid_format_reference(self):
        input_ref = '<ref>Malformed ref without sara-343 name</ref>'
        updated_refs = []
        match = re.match(r'<ref.*?</ref>', input_ref)
        result = unwikify_link(match, updated_refs)

        self.assertEqual(result, input_ref)
        self.assertEqual(updated_refs, [])

    def test_reference_with_extra_text(self):
        input_ref = '<ref name="sara-303">Text with {{bulleted list|Item 1|Item 2}} and more.</ref>'
        updated_refs = []
        match = re.match(r'<ref name="sara-\d+">.*?</ref>', input_ref)
        result = unwikify_link(match, updated_refs)

        expected = (
            '<li id="sara-303">303. Text with <ul>\n'
            '<li>Item 1</li>\n<li>Item 2</li>\n</ul> and more.</li>'
        )
        self.assertEqual(result, expected)

    def test_internal_link_simple(self):
        input_text = "See [[Main Page]] for details."
        expected = 'See <a target="_blank" href="https://meta.wikimedia.org/wiki/Main_Page">Main Page</a> for details.'
        self.assertEqual(replace_with_links(input_text), expected)

    def test_plain_url(self):
        input_text = "https://meta.wikimedia.org/wiki/Main_Page"
        expected = 'https://meta.wikimedia.org/wiki/Main_Page'
        self.assertEqual(replace_with_links(input_text), expected)

    def test_text_with_url(self):
        input_text = "text [with] links on it"
        expected = 'text <a target="_blank" href="with">with</a> links on it'
        self.assertEqual(replace_with_links(input_text), expected)

    def test_internal_link_with_label(self):
        input_text = "Visit [[Help:Editing|how to edit]]."
        expected = 'Visit <a target="_blank" href="https://meta.wikimedia.org/wiki/Help:Editing">how to edit</a>.'
        self.assertEqual(replace_with_links(input_text), expected)

    def test_external_link_with_label(self):
        input_text = "Go to [https://example.com Homepage]."
        expected = 'Go to <a target="_blank" href="https://example.com">Homepage</a>.'
        self.assertEqual(replace_with_links(input_text), expected)

    def test_external_link_without_label(self):
        input_text = "Go to [https://example.com]."
        expected = 'Go to <a target="_blank" href="https://example.com">https://example.com</a>.'
        self.assertEqual(replace_with_links(input_text), expected)

    def test_mixed_links(self):
        input_text = "See [[Main Page]] or [https://example.com External Site] or [[Special:Version|version info]]."
        expected = (
            'See <a target="_blank" href="https://meta.wikimedia.org/wiki/Main_Page">Main Page</a> or '
            '<a target="_blank" href="https://example.com">External Site</a> or '
            '<a target="_blank" href="https://meta.wikimedia.org/wiki/Special:Version">version info</a>.'
        )
        self.assertEqual(replace_with_links(input_text), expected)

    def test_no_links(self):
        input_text = "No links here."
        expected = "No links here."
        self.assertEqual(replace_with_links(input_text), expected)

    def test_edge_case_empty(self):
        self.assertEqual(replace_with_links(""), "")

    def test_link_with_spaces_and_encoding(self):
        input_text = "Check [[My Page Name|this page]]!"
        expected = 'Check <a target="_blank" href="https://meta.wikimedia.org/wiki/My_Page_Name">this page</a>!'
        self.assertEqual(replace_with_links(input_text), expected)

    def test_language_wiki_link(self):
        self.assertEqual(dewikify_url("w:en:Main_Page"),"https://en.wikipedia.org/wiki/Main Page")

    def test_commons_link(self):
        self.assertEqual(dewikify_url("c:Category:Birds"),"https://commons.wikimedia.org/wiki/Category:Birds")

    def test_wikidata_link(self):
        self.assertEqual(dewikify_url("d:Q42"),"https://www.wikidata.org/wiki/Q42")

    def test_meta_link_flag_true(self):
        self.assertEqual(dewikify_url("Sandbox", meta=True),"https://meta.wikimedia.org/wiki/Sandbox")

    def test_meta_link_flag_false(self):
        self.assertEqual(dewikify_url("Sandbox", meta=False),"Sandbox")

    def test_dash_as_link(self):
        self.assertEqual(dewikify_url("-", meta=False),"")

    def test_trailing_slash_is_removed(self):
        self.assertEqual(dewikify_url("w:en:Main_Page/"),"https://en.wikipedia.org/wiki/Main Page")

    def test_url_decoding(self):
        encoded = "w:en:Main_Page%2FSubpage"
        expected = "https://en.wikipedia.org/wiki/Main Page/Subpage"
        self.assertEqual(dewikify_url(encoded), expected)

    def test_build_wiki_ref(self):
        links = "https://sara-wmb.toolforge.org/calendar\r\nhttps://pt.wikipedia.org/wiki/Wikipedia:Pagina_inicial\r\nhttps://commons.wikimedia.org/wiki/Main_Page\r\nhttps://example.com"

        wiki_ref = build_wiki_ref(links, 1)
        self.assertEqual(wiki_ref, "<ref name=\"sara-1\">[[toolforge:sara-wmb/calendar|calendar]], [[w:pt:Wikipedia:Pagina_inicial|Wikipedia:Pagina inicial]], [[c:Main_Page|Main Page]], [https://example.com]</ref>")

    def test_build_wiki_ref_with_hifen_returns_empty_string(self):
        links = "-"

        wiki_ref = build_wiki_ref(links, 1)
        self.assertEqual(wiki_ref, "")


class TagsTests(TestCase):
    def test_categorize_for_0(self):
        result = categorize(0, 100)
        self.assertEqual(result, 1)

    def test_categorize_for_1(self):
        result = categorize(1, 100)
        self.assertEqual(result, 1)

    def test_categorize_for_26(self):
        result = categorize(26, 100)
        self.assertEqual(result, 2)

    def test_categorize_for_51(self):
        result = categorize(51, 100)
        self.assertEqual(result, 3)

    def test_categorize_for_76(self):
        result = categorize(76, 100)
        self.assertEqual(result, 4)

    def test_categorize_for_99(self):
        result = categorize(99, 100)
        self.assertEqual(result, 4)

    def test_categorize_for_100(self):
        result = categorize(100, 100)
        self.assertEqual(result, 5)

    def test_categorize_for_more_than_100(self):
        result = categorize(150, 100)
        self.assertEqual(result, 5)

    def test_categorize_for_text(self):
        result = categorize("invalid", 100)
        self.assertEqual(result, "-")

    def test_perc_for_0(self):
        result = perc(0, 100)
        self.assertEqual(result, "0%")

    def test_perc_for_1(self):
        result = perc(1, 100)
        self.assertEqual(result, "1%")

    def test_perc_for_26(self):
        result = perc(26, 100)
        self.assertEqual(result, "26%")

    def test_perc_for_51(self):
        result = perc(51, 100)
        self.assertEqual(result, "51%")

    def test_perc_for_76(self):
        result = perc(76, 100)
        self.assertEqual(result, "76%")

    def test_perc_for_99(self):
        result = perc(99, 100)
        self.assertEqual(result, "99%")

    def test_perc_for_100(self):
        result = perc(100, 100)
        self.assertEqual(result, "100%")

    def test_perc_for_more_than_100(self):
        result = perc(150, 100)
        self.assertEqual(result, "150%")

    def test_perc_for_text(self):
        result = perc("invalid", 100)
        self.assertEqual(result, "-")

    def test_perc_bool(self):
        result = perc(False, 1)
        self.assertEqual(result, "-")

    def test_bool_yesno_returns_yes_if_true(self):
        result = bool_yesno(True)
        self.assertEqual(result, _("Yes"))

    def test_bool_yesno_returns_no_if_false(self):
        result = bool_yesno(False)
        self.assertEqual(result, _("No"))

    def test_bool_yesno_returns_value_if_not_boolean(self):
        result = bool_yesno("Test")
        self.assertEqual(result, _("Test"))

    def test_bool_yesno_returns_value_if_true(self):
        result = bool_yesnopartial(False, True)
        self.assertEqual(result, _("Yes"))

    def test_bool_is_yesno_returns_true_if_boolean(self):
        result = is_yesno(True)
        self.assertTrue(result)

    def test_bool_is_yesno_returns_false_if_not_boolean(self):
        result = is_yesno(2)
        self.assertFalse(result)

    def test_bool_is_yesno_returns_false_even_if_is_0_or_1(self):
        result = is_yesno(0)
        self.assertFalse(result)

        result = is_yesno(1)
        self.assertFalse(result)


class MetricsExportTests(TestCase):
    def setUp(self):
        self.username = "testuser"
        self.password = "testpass"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.view_metrics_permission = Permission.objects.get(codename="view_metric")
        self.change_metrics_permission = Permission.objects.get(codename="change_metric")
        self.user.user_permissions.add(self.view_metrics_permission)
        self.user.user_permissions.add(self.change_metrics_permission)
        self.poa_project = Project.objects.create(text="POA", current_poa=True)
        self.main_project = Project.objects.create(text="Main", main_funding=True)
        self.other_activity = Activity.objects.create(text="Other activity")
        self.activity = Activity.objects.create(text="Activity")

    def test_export_trimester_report_succeeds_if_user_has_permission(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("metrics:export_reports_per_trimester")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=UTF-8')
        self.assertIn('Content-Disposition', response)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="trimester_report.txt"')
        self.assertNotEqual(response.content, b'')
        expected_content = b"{| class='wikitable wmb_report_table'\n!Activity !! Metrics !! Q1 !! Q2 !! Q3 !! Q4 !! Total !! References\n|-\n|}\n"
        self.assertEqual(response.content.decode('utf-8'), expected_content.decode('utf-8'))

    def test_export_trimester_report_fails_if_user_is_not_authorized(self):
        self.user.user_permissions.remove(self.view_metrics_permission)
        self.client.login(username=self.username, password=self.password)

        url = reverse("metrics:export_reports_per_trimester")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={url}")

    def test_export_semester_report_succeeds_if_user_has_permission(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("metrics:export_reports_per_semester")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=UTF-8')
        self.assertIn('Content-Disposition', response)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="semester_report.txt"')
        self.assertNotEqual(response.content, b'')
        expected_content = b"{| class='wikitable wmb_report_table'\n!Activity !! Metrics !! S1 !! S2 !! Total !! References\n|-\n|}\n"
        self.assertEqual(response.content.decode('utf-8'), expected_content.decode('utf-8'))

    def test_export_semester_report_fails_if_user_is_not_authorized(self):
        self.user.user_permissions.remove(self.view_metrics_permission)
        self.client.login(username=self.username, password=self.password)

        url = reverse("metrics:export_reports_per_semester")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={url}")

    def test_export_yearly_report_succeeds_if_user_has_permission(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("metrics:export_reports_per_year")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=UTF-8')
        self.assertIn('Content-Disposition', response)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="year_report.txt"')
        self.assertNotEqual(response.content, b'')
        expected_content = b"{| class='wikitable wmb_report_table'\n!Activity !! Metrics !! Year !! Total !! References\n|-\n|}\n"
        self.assertEqual(response.content.decode('utf-8'), expected_content.decode('utf-8'))

    def test_export_yearly_report_fails_if_user_is_not_authorized(self):
        self.user.user_permissions.remove(self.view_metrics_permission)
        self.client.login(username=self.username, password=self.password)

        url = reverse("metrics:export_reports_per_year")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={url}")

    def test_export_trimester_report_exports_activities_results_with_hyphens_when_nothing_was_done(self):
        self.client.login(username=self.username, password=self.password)
        metric = Metric.objects.create(text="Metric", activity=self.activity, is_operation=True,
                                       number_of_events=5)
        metric.project.add(self.poa_project)
        metric.save()

        url = reverse("metrics:export_reports_per_trimester")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=UTF-8')
        self.assertIn('Content-Disposition', response)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="trimester_report.txt"')
        self.assertNotEqual(response.content, b'')
        expected_content = b"{| class='wikitable wmb_report_table'\n!Activity !! Metrics !! Q1 !! Q2 !! Q3 !! Q4 !! Total !! References\n|-\n| Activity || Metric || - || - || - || - || - || \n|-\n|}\n"
        self.assertEqual(response.content.decode('utf-8'), expected_content.decode('utf-8'))

    def test_export_trimester_report_exports_activities_results_with_number_when_something_was_done(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("metrics:export_reports_per_trimester")
        area_responsible = TeamArea.objects.create(text="Area")
        area_responsible.project.add(self.main_project)
        area_responsible.save()
        report = Report.objects.create(description="Report 1",
                                       created_by=self.user_profile,
                                       modified_by=self.user_profile,
                                       initial_date=date(datetime.today().year, 2, 28),
                                       learning="Learnings!" * 51,
                                       activity_associated=self.activity,
                                       area_responsible=area_responsible,
                                       links="Links")
        metric = Metric.objects.create(text="Metric", activity=self.activity, is_operation=True, number_of_events=5)
        metric.project.add(self.poa_project)
        metric.save()
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        directions_related = Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        learning_questions_related = StrategicLearningQuestion.objects.create(text="Strategic Learning Question", learning_area=learning_area)

        report.directions_related.add(directions_related)
        report.learning_questions_related.add(learning_questions_related)
        report.metrics_related.add(metric)
        report.save()

        operation_report = OperationReport.objects.create(metric=metric, report=report, number_of_events=3, number_of_resources=2)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=UTF-8')
        self.assertIn('Content-Disposition', response)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="trimester_report.txt"')
        self.assertNotEqual(response.content, b'')
        expected_content = b"{| class='wikitable wmb_report_table'\n!Activity !! Metrics !! Q1 !! Q2 !! Q3 !! Q4 !! Total !! References\n|-\n| " + bytes(self.activity.text, 'utf-8') + b" || " + bytes(metric.text, 'utf-8') + b" || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || - || - || - || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || <ref name=\"sara-" + bytes(str(report.id), 'utf-8') + b"\">[" + bytes(str(report.links), 'utf-8') + b"]</ref>\n|-\n|}\n"
        self.assertEqual(response.content.decode('utf-8'), expected_content.decode('utf-8'))

    def test_export_trimester_report_exports_activities_results_of_main_funding_project(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("metrics:export_reports_per_trimester")
        area_responsible = TeamArea.objects.create(text="Area")
        area_responsible.project.add(self.main_project)
        area_responsible.save()
        report = Report.objects.create(description="Report 1",
                                       created_by=self.user_profile,
                                       modified_by=self.user_profile,
                                       initial_date=date(datetime.today().year, 2, 28),
                                       learning="Learnings!" * 51,
                                       activity_associated=self.activity,
                                       area_responsible=area_responsible,
                                       links="Links")
        metric = Metric.objects.create(text="Metric", activity=self.other_activity, number_of_events=5, is_operation=True)
        metric.project.add(self.main_project)
        metric.save()
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        directions_related = Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        learning_questions_related = StrategicLearningQuestion.objects.create(text="Strategic Learning Question", learning_area=learning_area)

        report.directions_related.add(directions_related)
        report.learning_questions_related.add(learning_questions_related)
        report.metrics_related.add(metric)
        report.save()

        operation_report = OperationReport.objects.create(metric=metric, report=report, number_of_events=6, number_of_resources=2)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=UTF-8')
        self.assertIn('Content-Disposition', response)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="trimester_report.txt"')
        self.assertNotEqual(response.content, b'')
        expected_content = b"{| class='wikitable wmb_report_table'\n!Activity !! Metrics !! Q1 !! Q2 !! Q3 !! Q4 !! Total !! References\n|-\n| - || " + bytes(metric.text, 'utf-8') + b" || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || - || - || - || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || <ref name=\"sara-" + bytes(str(report.id), 'utf-8') + b"\">[" + bytes(str(report.links), 'utf-8') + b"]</ref>\n|-\n|}\n"
        self.assertEqual(response.content.decode('utf-8'), expected_content.decode('utf-8'))

    def test_export_trimester_report_by_area_succeeds_if_user_is_authenticated(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("metrics:export_reports_trimester_per_area")

        area_responsible = TeamArea.objects.create(text="Area", code="area")
        area_responsible.project.add(self.main_project)
        area_responsible.save()
        report = Report.objects.create(description="Report 1",
                                       created_by=self.user_profile,
                                       modified_by=self.user_profile,
                                       initial_date=date(datetime.today().year, 2, 28),
                                       learning="Learnings!" * 51,
                                       activity_associated=self.activity,
                                       area_responsible=area_responsible,
                                       links="Links")
        metric = Metric.objects.create(text="Metric", activity=self.activity, is_operation=True, number_of_events=5)
        metric.project.add(self.main_project)
        metric.save()
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        directions_related = Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        learning_questions_related = StrategicLearningQuestion.objects.create(text="Strategic Learning Question",
                                                                              learning_area=learning_area)

        report.directions_related.add(directions_related)
        report.learning_questions_related.add(learning_questions_related)
        report.metrics_related.add(metric)
        report.save()

        operation_report = OperationReport.objects.create(metric=metric, report=report, number_of_events=6, number_of_resources=2)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=UTF-8')
        self.assertIn('Content-Disposition', response)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="trimester_report.txt"')
        self.assertNotEqual(response.content, b'')
        expected_content = b"==" + bytes(area_responsible.text, 'utf-8') + b"==\n<div class='wmb_report_table_container bd-" + bytes(area_responsible.code, 'utf-8') + b"'>\n{| class='wikitable wmb_report_table'\n! colspan='8' class='bg-" + bytes(area_responsible.code, 'utf-8') + b" co-" + bytes(area_responsible.code, 'utf-8') + b"' | <h5 id='Metrics'>Operational and General metrics</h5>\n|-\n!Activity !! Metrics !! Q1 !! Q2 !! Q3 !! Q4 !! Total !! References\n|-\n| " + bytes(self.activity.text, 'utf-8') + b" || " + bytes(metric.text, 'utf-8') + b" || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || - || - || - || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || <ref name=\"sara-" + bytes(str(report.id), 'utf-8') + b"\">[" + bytes(str(report.links), 'utf-8') + b"]</ref>\n|-\n|}\n</div>\n"
        self.assertEqual(response.content.decode('utf-8'), expected_content.decode('utf-8'))

    def test_export_trimester_report_by_area_fails_if_user_is_unauthenticated(self):
        self.user.user_permissions.remove(self.view_metrics_permission)
        self.client.login(username=self.username, password=self.password)

        url = reverse("metrics:export_reports_per_trimester")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={url}")

    def test_export_semester_report_by_area_succeeds_if_user_is_authenticated(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("metrics:export_reports_per_semester_per_area")

        area_responsible = TeamArea.objects.create(text="Area", code="area")
        area_responsible.project.add(self.main_project)
        area_responsible.save()
        report = Report.objects.create(description="Report 1",
                                       created_by=self.user_profile,
                                       modified_by=self.user_profile,
                                       initial_date=date(datetime.today().year, 2, 28),
                                       learning="Learnings!" * 51,
                                       activity_associated=self.activity,
                                       area_responsible=area_responsible,
                                       links="Links")
        metric = Metric.objects.create(text="Metric", activity=self.activity, is_operation=True, number_of_events=5)
        metric.project.add(self.main_project)
        metric.save()
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        directions_related = Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        learning_questions_related = StrategicLearningQuestion.objects.create(text="Strategic Learning Question",
                                                                              learning_area=learning_area)

        report.directions_related.add(directions_related)
        report.learning_questions_related.add(learning_questions_related)
        report.metrics_related.add(metric)
        report.save()

        operation_report = OperationReport.objects.create(metric=metric, report=report, number_of_events=6, number_of_resources=2)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=UTF-8')
        self.assertIn('Content-Disposition', response)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="semester_report.txt"')
        self.assertNotEqual(response.content, b'')
        expected_content = b"==" + bytes(area_responsible.text, 'utf-8') + b"==\n<div class='wmb_report_table_container bd-" + bytes(area_responsible.code, 'utf-8') + b"'>\n{| class='wikitable wmb_report_table'\n! colspan='8' class='bg-" + bytes(area_responsible.code, 'utf-8') + b" co-" + bytes(area_responsible.code, 'utf-8') + b"' | <h5 id='Metrics'>Operational and General metrics</h5>\n|-\n!Activity !! Metrics !! S1 !! S2 !! Total !! References\n|-\n| " + bytes(self.activity.text, 'utf-8') + b" || " + bytes(metric.text, 'utf-8') + b" || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || - || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || <ref name=\"sara-" + bytes(str(report.id), 'utf-8') + b"\">[" + bytes(str(report.links), 'utf-8') + b"]</ref>\n|-\n|}\n</div>\n"
        self.assertEqual(response.content.decode('utf-8'), expected_content.decode('utf-8'))

    def test_export_semester_report_by_area_fails_if_user_is_unauthenticated(self):
        self.user.user_permissions.remove(self.view_metrics_permission)
        self.client.login(username=self.username, password=self.password)

        url = reverse("metrics:export_reports_per_semester_per_area")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={url}")

    def test_export_yearly_report_by_area_succeeds_if_user_is_authenticated(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("metrics:export_reports_per_year_per_area")

        area_responsible = TeamArea.objects.create(text="Area", code="area")
        area_responsible.project.add(self.main_project)
        area_responsible.save()
        report = Report.objects.create(description="Report 1",
                                       created_by=self.user_profile,
                                       modified_by=self.user_profile,
                                       initial_date=date(datetime.today().year, 2, 28),
                                       learning="Learnings!" * 51,
                                       activity_associated=self.activity,
                                       area_responsible=area_responsible,
                                       links="Links")
        metric = Metric.objects.create(text="Metric", activity=self.activity, is_operation=True, number_of_events=5)
        metric.project.add(self.main_project)
        metric.save()
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        directions_related = Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        learning_questions_related = StrategicLearningQuestion.objects.create(text="Strategic Learning Question",
                                                                              learning_area=learning_area)

        report.directions_related.add(directions_related)
        report.learning_questions_related.add(learning_questions_related)
        report.metrics_related.add(metric)
        report.save()

        operation_report = OperationReport.objects.create(metric=metric, report=report, number_of_events=6, number_of_resources=2)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=UTF-8')
        self.assertIn('Content-Disposition', response)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="year_report.txt"')
        self.assertNotEqual(response.content, b'')
        expected_content = b"==" + bytes(area_responsible.text, 'utf-8') + b"==\n<div class='wmb_report_table_container bd-" + bytes(area_responsible.code, 'utf-8') + b"'>\n{| class='wikitable wmb_report_table'\n! colspan='8' class='bg-" + bytes(area_responsible.code, 'utf-8') + b" co-" + bytes(area_responsible.code, 'utf-8') + b"' | <h5 id='Metrics'>Operational and General metrics</h5>\n|-\n!Activity !! Metrics !! Year !! Total !! References\n|-\n| " + bytes(self.activity.text, 'utf-8') + b" || " + bytes(metric.text, 'utf-8') + b" || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || <ref name=\"sara-" + bytes(str(report.id), 'utf-8') + b"\">[" + bytes(str(report.links), 'utf-8') + b"]</ref>\n|-\n|}\n</div>\n"
        self.assertEqual(response.content.decode('utf-8'), expected_content.decode('utf-8'))

    def test_export_yearly_report_by_area_fails_if_user_is_unauthenticated(self):
        self.user.user_permissions.remove(self.view_metrics_permission)
        self.client.login(username=self.username, password=self.password)

        url = reverse("metrics:export_reports_per_year_per_area")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={url}")

    def test_export_trimester_report_exports_wiki_links_as_wikitext(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("metrics:export_reports_per_trimester")
        area_responsible = TeamArea.objects.create(text="Area")
        area_responsible.project.add(self.main_project)
        area_responsible.save()
        report = Report.objects.create(description="Report 1",
                                       created_by=self.user_profile,
                                       modified_by=self.user_profile,
                                       initial_date=date(datetime.today().year, 2, 28),
                                       learning="Learnings!" * 51,
                                       activity_associated=self.activity,
                                       area_responsible=area_responsible,
                                       links="https://sara-wmb.toolforge.org/calendar\r\nhttps://pt.wikipedia.org/wiki/Wikipedia:Pagina_inicial\r\nhttps://commons.wikimedia.org/wiki/Main_Page\r\nhttps://example.com")
        metric = Metric.objects.create(text="Metric", activity=self.other_activity, number_of_events=5)
        metric.project.add(self.main_project)
        metric.save()
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        directions_related = Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        learning_questions_related = StrategicLearningQuestion.objects.create(text="Strategic Learning Question", learning_area=learning_area)

        report.directions_related.add(directions_related)
        report.learning_questions_related.add(learning_questions_related)
        report.metrics_related.add(metric)
        report.save()

        operation_report = OperationReport.objects.create(metric=metric, report=report, number_of_events=6, number_of_resources=2)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=UTF-8')
        self.assertIn('Content-Disposition', response)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="trimester_report.txt"')
        self.assertNotEqual(response.content, b'')
        expected_content = b"{| class='wikitable wmb_report_table'\n!Activity !! Metrics !! Q1 !! Q2 !! Q3 !! Q4 !! Total !! References\n|-\n| - || " + bytes(metric.text, 'utf-8') + b" || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || - || - || - || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || <ref name=\"sara-" + bytes(str(report.id), 'utf-8') + b"\">[[toolforge:sara-wmb/calendar|calendar]], [[w:pt:Wikipedia:Pagina_inicial|Wikipedia:Pagina inicial]], [[c:Main_Page|Main Page]], [https://example.com]</ref>\n|-\n|}\n"
        self.assertEqual(response.content.decode('utf-8'), expected_content.decode('utf-8'))

    def test_export_trimester_report_exports_wiki_links_as_wikitext_and_deals_with_duplicates(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("metrics:export_reports_per_trimester")
        area_responsible = TeamArea.objects.create(text="Area")
        area_responsible.project.add(self.main_project)
        area_responsible.save()
        report = Report.objects.create(description="Report 1",
                                       created_by=self.user_profile,
                                       modified_by=self.user_profile,
                                       initial_date=date(datetime.today().year, 2, 28),
                                       learning="Learnings!" * 51,
                                       activity_associated=self.activity,
                                       area_responsible=area_responsible,
                                       links="https://sara-wmb.toolforge.org/calendar\r\nhttps://pt.wikipedia.org/wiki/Wikipedia:Pagina_inicial\r\nhttps://commons.wikimedia.org/wiki/Main_Page\r\nhttps://example.com")
        report_2 = Report.objects.create(description="Report 2",
                                       created_by=self.user_profile,
                                       modified_by=self.user_profile,
                                       initial_date=date(datetime.today().year, 2, 28),
                                       learning="Learnings!" * 51,
                                       activity_associated=self.activity,
                                       area_responsible=area_responsible,
                                       links="https://pt.wikipedia.org/wiki/Wikipedia:Pagina_inicial")
        metric = Metric.objects.create(text="Metric", activity=self.other_activity, number_of_events=5)
        metric.project.add(self.main_project)
        metric.save()
        metric_2 = Metric.objects.create(text="Metric 2", activity=self.other_activity, number_of_events=10)
        metric_2.project.add(self.main_project)
        metric_2.save()
        strategic_axis = StrategicAxis.objects.create(text="Strategic Axis")
        directions_related = Direction.objects.create(text="Direction", strategic_axis=strategic_axis)
        learning_area = LearningArea.objects.create(text="Learning area")
        learning_questions_related = StrategicLearningQuestion.objects.create(text="Strategic Learning Question", learning_area=learning_area)

        report.directions_related.add(directions_related)
        report.learning_questions_related.add(learning_questions_related)
        report.metrics_related.add(metric)
        report.metrics_related.add(metric_2)
        report.save()
        report_2.directions_related.add(directions_related)
        report_2.learning_questions_related.add(learning_questions_related)
        report_2.metrics_related.add(metric_2)
        report_2.save()

        operation_report = OperationReport.objects.create(metric=metric, report=report, number_of_events=6, number_of_resources=2)
        operation_report_2 = OperationReport.objects.create(metric=metric_2, report=report_2, number_of_events=2, number_of_resources=6)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=UTF-8')
        self.assertIn('Content-Disposition', response)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="trimester_report.txt"')
        self.assertNotEqual(response.content, b'')
        expected_content = b"{| class='wikitable wmb_report_table'\n!Activity !! Metrics !! Q1 !! Q2 !! Q3 !! Q4 !! Total !! References\n|-\n| rowspan='2' | - || " + bytes(metric.text, 'utf-8') + b" || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || - || - || - || " + bytes(str(operation_report.number_of_events), 'utf-8') + b" || <ref name=\"sara-" + bytes(str(report.id), 'utf-8') + b"\">[[toolforge:sara-wmb/calendar|calendar]], [[w:pt:Wikipedia:Pagina_inicial|Wikipedia:Pagina inicial]], [[c:Main_Page|Main Page]], [https://example.com]</ref>\n|-\n| " + bytes(metric_2.text, 'utf-8') + b" || " + bytes(str(operation_report_2.number_of_events), 'utf-8') + b" || - || - || - || " + bytes(str(operation_report_2.number_of_events), 'utf-8') + b" || <ref name=\"sara-" + bytes(str(report.id), 'utf-8') + b"\"/><ref name=\"sara-" + bytes(str(report_2.id), 'utf-8') + b"\">[[w:pt:Wikipedia:Pagina_inicial|Wikipedia:Pagina inicial]]</ref>\n|-\n|}\n"
        self.assertEqual(response.content.decode('utf-8'), expected_content.decode('utf-8'))
