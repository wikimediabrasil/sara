from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db.models import RestrictedError
from django.db.utils import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from users.models import User, UserProfile

from .models import Bug, Observation


class BugModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username="username",
            email="email@email.com",
            first_name="First Name",
            last_name="Last Name",
        )

        self.title = "Test Bug"
        self.description = "Test Description"

        self.reporter = UserProfile.objects.filter(user=self.user).first()
        self.bug = Bug.objects.create(
            title=self.title,
            description=self.description,
            reporter=self.reporter,
        )

    def test_str_method_returns_bug_title(self):
        bug = Bug.objects.create(
            title=self.title,
            description=self.description,
            reporter=self.reporter,
        )
        self.assertEqual(str(bug), f"{Bug.BugType.ERROR.label}: {self.title}")

    def test_create_bug_without_description_fails(self):
        with self.assertRaises(ValidationError):
            bug = Bug.objects.create(title=self.title, reporter=self.reporter)
            bug.full_clean()

    def test_create_bug_without_title_fails(self):
        with self.assertRaises(ValidationError):
            bug = Bug.objects.create(
                description=self.description, reporter=self.reporter
            )
            bug.full_clean()

    def test_create_bug_without_reporter_fails(self):
        with self.assertRaises(IntegrityError):
            Bug.objects.create(title=self.title, description=self.description)

    def test_create_bug_with_minimal_requirements_succeeds(self):
        bug = Bug.objects.create(
            title=self.title, description=self.description, reporter=self.reporter
        )
        bug.full_clean()
        self.assertTrue(Bug.objects.filter(pk=bug.pk).exists())

    def test_trying_to_delete_a_user_with_bugs_associated_fails(self):
        with self.assertRaises(RestrictedError):
            self.user.delete()

    def test_str_method_returns_observation_title_of_bug(self):
        obs = Observation.objects.create(bug_report=self.bug, observation="Observation")
        self.assertEqual(
            str(obs), _("Observation for bug nº %(bug_id)s") % {"bug_id": self.bug.pk}
        )


class BugViewsTests(TestCase):
    def setUp(self):
        self.username = "test_user"
        self.password = "test_pass"
        self.user = User.objects.create_user(
            username=self.username, password=self.password
        )
        self.user_profile = UserProfile.objects.filter(user=self.user).first()
        self.title = "Title"
        self.description = "Description"
        self.bug_type = Bug.BugType.ERROR
        self.bug = Bug.objects.create(
            title=self.title,
            description=self.description,
            reporter=self.user_profile,
            bug_type=self.bug_type,
        )
        self.add_obs_permission = Permission.objects.get(codename="add_observation")
        self.change_obs_permission = Permission.objects.get(
            codename="change_observation"
        )
        self.add_bug_permission = Permission.objects.get(codename="add_bug")
        self.view_bug_permission = Permission.objects.get(codename="view_bug")
        self.change_bug_permission = Permission.objects.get(codename="change_bug")
        self.user.user_permissions.add(self.add_obs_permission)
        self.user.user_permissions.add(self.change_obs_permission)
        self.user.user_permissions.add(self.add_bug_permission)
        self.user.user_permissions.add(self.view_bug_permission)
        self.user.user_permissions.add(self.change_bug_permission)

    def test_add_bug_view_get_fails_if_user_doesnt_have_permission(self):
        self.user.user_permissions.remove(self.add_bug_permission)
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:create_bug")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, f"{reverse('users:login')}?next={reverse('bug:create_bug')}"
        )

    def test_add_bug_view_get(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:create_bug")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_add_bug_view_post(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:create_bug")
        data = {
            "title": "Title2",
            "description": "Description2",
            "bug_type": Bug.BugType.ERROR,
            "status": Bug.Status.EVAL,
        }
        response = self.client.post(url, data=data)

        bug = Bug.objects.get(
            title=data["title"],
            description=data["description"],
            bug_type=data["bug_type"],
            status=data["status"],
        )
        self.assertRedirects(
            response, reverse("bug:detail_bug", kwargs={"bug_id": bug.pk})
        )
        self.assertEqual(bug.reporter.user, self.user)

    def test_add_bug_view_post_fails_with_invalid_parameters_for_reporter(self):
        self.user.user_permissions.remove(self.add_obs_permission)
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:create_bug")
        data = {
            "title": "",
            "description": "Description2",
            "bug_type": Bug.BugType.ERROR,
            "status": Bug.Status.EVAL,
        }
        response = self.client.post(url, data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Something went wrong!")

    def test_list_bugs_view_fails_if_user_doesnt_have_permission(self):
        self.user.user_permissions.remove(self.view_bug_permission)
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:list_bugs")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, f"{reverse('users:login')}?next={reverse('bug:list_bugs')}"
        )

    def test_list_bugs_view(self):
        url = reverse("bug:list_bugs")
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.bug, response.context["dataset"])

    def test_detail_bug_view_fails_if_user_doesnt_have_permission(self):
        self.user.user_permissions.remove(self.view_bug_permission)
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:detail_bug", args=[self.bug.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f"{reverse('users:login')}?next={reverse('bug:detail_bug', args=[self.bug.id])}",
        )

    def test_detail_bug_view(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:detail_bug", args=[self.bug.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["data"], self.bug)

    def test_update_bug_view(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:edit_bug", args=[self.bug.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = {
            "title": "Testes",
            "status": Bug.Status.DONE,
            "description": "This is an updated test bug.",
            "bug_type": Bug.BugType.ERROR,
            "reporter": self.user,
        }

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(url, data=data)
        self.assertRedirects(response, reverse("bug:detail_bug", args=[self.bug.id]))

    def test_update_bug_view_when_user_is_not_developer(self):
        self.user.user_permissions.remove(self.add_obs_permission)
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:edit_bug", args=[self.bug.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = {
            "title": "Testes",
            "description": "This is an updated test bug.",
            "bug_type": Bug.BugType.ERROR,
            "reporter": self.user,
        }

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(url, data=data)
        self.assertRedirects(response, reverse("bug:detail_bug", args=[self.bug.id]))

    def test_update_bug_view_fails_with_invalid_parameters(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:edit_bug", args=[self.bug.id])

        data = {
            "status": -1,
        }

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Something went wrong!")

    def test_add_observation_only_is_accessible_to_users_with_the_right_permissions(
        self,
    ):
        self.user.user_permissions.remove(self.add_obs_permission)
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:add_obs", kwargs={"bug_id": self.bug.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f"{reverse('users:login')}?next={reverse('bug:add_obs', kwargs={'bug_id': self.bug.pk})}",
        )

    def test_add_observation_view_get(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:add_obs", args=[self.bug.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_add_observation_view_redirects_to_update_if_observation_already_exists(
        self,
    ):
        Observation.objects.create(bug_report=self.bug, observation="Observation")
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:add_obs", args=[self.bug.id])
        response = self.client.get(url)

        self.assertRedirects(response, reverse("bug:edit_obs", args=[self.bug.id]))

    def test_add_observation_view_post(self):
        url = reverse("bug:add_obs", args=[self.bug.id])
        data = {"observation": "Observation"}

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(url, data=data)
        self.assertRedirects(response, reverse("bug:detail_bug", args=[self.bug.id]))

    def test_add_observation_view_post_fails_with_invalid_parameters(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:add_obs", args=[self.bug.id])
        data = {"observation": ""}
        response = self.client.post(url, data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Something went wrong!")

    def test_update_observation_view_is_only_accessible_for_users_with_permission(self):
        self.user.user_permissions.remove(self.change_obs_permission)
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:edit_obs", args=[self.bug.id])
        Observation.objects.create(bug_report=self.bug, observation="Observation")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            f"{reverse('users:login')}?next={reverse('bug:edit_obs', args=[self.bug.id])}",
        )

    def test_update_observation_view(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:edit_obs", args=[self.bug.id])
        obs = Observation.objects.create(bug_report=self.bug, observation="Observation")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = {"observation": "Observation2"}

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(url, data=data)

        obs = Observation.objects.get(pk=obs.pk)
        self.assertEqual(obs.observation, data["observation"])
        self.assertRedirects(response, reverse("bug:detail_bug", args=[self.bug.id]))

    def test_update_observation_view_fails_with_invalid_parameters(self):
        self.client.login(username=self.username, password=self.password)
        url = reverse("bug:edit_obs", args=[self.bug.id])
        Observation.objects.create(bug_report=self.bug, observation="Observation")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = {"observation": ""}

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Something went wrong!")

    def test_export_bugs_get_view_is_only_accessible_for_users_with_the_right_permissions(
        self,
    ):
        self.user.user_permissions.remove(self.view_bug_permission)
        self.client.force_login(self.user)
        Bug.objects.create(
            title="Bug 1",
            description="Bug description 1",
            bug_type=Bug.BugType.ERROR,
            status=Bug.Status.TODO,
            reporter=self.user_profile,
        )
        Bug.objects.create(
            title="Bug 2",
            description="Bug description 2",
            bug_type=Bug.BugType.CLARIFICATION,
            status=Bug.Status.PROG,
            reporter=self.user_profile,
        )
        Bug.objects.create(
            title="Bug 3",
            description="Bug description 3",
            bug_type=Bug.BugType.IMPROVEMENT,
            status=Bug.Status.TEST,
            reporter=self.user_profile,
        )
        Bug.objects.create(
            title="Bug 4",
            description="Bug description 4",
            bug_type=Bug.BugType.NEWFEATURE,
            status=Bug.Status.DONE,
            reporter=self.user_profile,
        )

        url = reverse("bug:export_bugs")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url, f"{reverse('users:login')}?next={reverse('bug:export_bugs')}"
        )

    def test_export_bugs_get_view_returns_zip_file(self):
        self.client.login(username=self.username, password=self.password)
        Bug.objects.create(
            title="Bug 1",
            description="Bug description 1",
            bug_type=Bug.BugType.ERROR,
            status=Bug.Status.TODO,
            reporter=self.user_profile,
        )
        Bug.objects.create(
            title="Bug 2",
            description="Bug description 2",
            bug_type=Bug.BugType.CLARIFICATION,
            status=Bug.Status.PROG,
            reporter=self.user_profile,
        )
        Bug.objects.create(
            title="Bug 3",
            description="Bug description 3",
            bug_type=Bug.BugType.IMPROVEMENT,
            status=Bug.Status.TEST,
            reporter=self.user_profile,
        )
        Bug.objects.create(
            title="Bug 4",
            description="Bug description 4",
            bug_type=Bug.BugType.NEWFEATURE,
            status=Bug.Status.DONE,
            reporter=self.user_profile,
        )

        url = reverse("bug:export_bugs")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content_type = response.headers["Content-Type"]
        self.assertEqual(content_type, "application/x-zip-compressed")
