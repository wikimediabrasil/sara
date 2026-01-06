import datetime
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db.models import RestrictedError, ProtectedError
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.admin import User
from django.test.client import RequestFactory
from django.contrib.admin.sites import AdminSite
from django.utils.translation import gettext as _

from users.models import TeamArea, Position, UserProfile
from users.admin import AccountUserAdmin, UserProfileInline
from users.views import login_oauth, logout_oauth
from users.pipeline import associate_by_wiki_handle, get_username
from agenda.models import Event


class TeamAreaModelTests(TestCase):
    def setUp(self):
        self.text = "Team Area"
        self.code = "team_area"
        self.team_area = TeamArea.objects.create(text=self.text, code=self.code)

    def test_str_method(self):
        self.assertEqual(str(self.team_area), self.text)

    def test_clean_method(self):
        team_area2 = TeamArea.objects.create(text="Team Area 2", code="team_area_2")
        team_area2.full_clean()

        with self.assertRaises(ValidationError):
            team_area2.text = ""
            team_area2.full_clean()

        with self.assertRaises(ValidationError):
            team_area2.text = self.text
            team_area2.code = ""
            team_area2.full_clean()

    def test_trying_to_delete_team_area_that_are_responsible_for_events_fails(self):
        Event.objects.create(
            name="Test Event",
            initial_date=datetime.date(2023, 3, 24),
            end_date=datetime.date(2023, 3, 31),
            area_responsible=self.team_area,
        )

        with self.assertRaises(RestrictedError):
            self.team_area.delete()

    def test_trying_to_delete_team_area_that_are_not_responsible_for_events_succeeds(self):
        team_area2 = TeamArea.objects.create(text="Team Area 2", code="team_area_2")

        Event.objects.create(
            name="Test Event",
            initial_date=datetime.date(2023, 3, 24),
            end_date=datetime.date(2023, 3, 31),
            area_responsible=self.team_area,
        )

        team_area2.delete()
        self.assertEqual(TeamArea.objects.count(), 1)


class PositionModelTest(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Group_name")
        self.text = "Position"
        self.area_associated = TeamArea.objects.create(text="Team Area", code="team_area")

        self.position = Position.objects.create(text=self.text,
                                                type=self.group,
                                                area_associated=self.area_associated)

    def test_str_method(self):
        self.assertEqual(str(self.position), self.text)

    def test_position_creation(self):
        self.assertEqual(self.position.text, "Position")
        self.assertEqual(self.position.type, self.group)
        self.assertEqual(self.position.area_associated, self.area_associated)

    def test_protect_on_group_delete(self):
        with self.assertRaises(ProtectedError):
            self.group.delete()

    def test_protect_on_area_delete(self):
        with self.assertRaises(ProtectedError):
            self.area_associated.delete()


class UserProfileModelTest(TestCase):
    def setUp(self):
        self.first_name = "First Name"
        self.user = User.objects.create(
            username="username",
            email="email@email.com",
            first_name=self.first_name,
            last_name="Last Name")
        self.user_profile = UserProfile.objects.filter(user=self.user).first()

    def test_str_method_returns_first_name_if_there_is_no_professional_wiki_handle(self):
        self.assertTrue(str(self.user_profile), self.first_name)

    def test_str_method_returns_professional_wiki_handle_if_present(self):
        professional_wiki_handle = "Professional Wiki handle"
        self.user_profile.professional_wiki_handle = professional_wiki_handle
        self.assertTrue(str(self.user_profile), professional_wiki_handle)


class UserProfileViewTest(TestCase):
    def setUp(self):
        self.username = "username"
        self.password = "password"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.user_profile = UserProfile.objects.filter(user=self.user).first()
        self.view_userprofile_permission = Permission.objects.get(codename="view_userprofile")
        self.view_user_permission = Permission.objects.get(codename="view_user")
        self.change_userprofile_permission = Permission.objects.get(codename="change_userprofile")
        self.change_user_permission = Permission.objects.get(codename="change_user")
        self.user.user_permissions.add(self.view_userprofile_permission)
        self.user.user_permissions.add(self.view_user_permission)
        self.user.user_permissions.add(self.change_userprofile_permission)
        self.user.user_permissions.add(self.change_user_permission)

    def test_user_profile_is_not_accessible_by_not_logged_in_users(self):
        response = self.client.get(reverse('users:view_profile', kwargs={"username": self.user.username}))
        self.assertEqual(response.url, f"{reverse('users:login')}?next={reverse('users:view_profile', kwargs={'username': self.user.username})}")

    def test_user_profile_is_not_accessible_by_logged_in_users_without_permission(self):
        self.user.user_permissions.remove(self.view_user_permission)
        self.user.user_permissions.remove(self.view_userprofile_permission)
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('users:view_profile', kwargs={"username": self.user.username}))
        self.assertEqual(response.url, f"{reverse('users:login')}?next={reverse('users:view_profile', kwargs={'username': self.user.username})}")

    def test_user_profile_is_accessible_by_logged_in_users_with_view_permission(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('users:view_profile', kwargs={"username": self.user.username}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/detail_profile.html')

    def test_user_profile_post(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('users:update_profile', kwargs={"username": self.user.username}))

        self.assertEqual(self.user_profile.professional_wiki_handle, "")
        self.assertEqual(response.status_code, 200)
        data = {"professional_wiki_handle": "Handle"}

        response = self.client.post(reverse('users:update_profile', kwargs={"username": self.user.username}), data=data)
        self.assertContains(response, _("Changes done successfully!"))

        user_profile = UserProfile.objects.get(user=self.user)
        self.assertIsNotNone(user_profile.professional_wiki_handle)

    def test_user_profile_post_with_invalid_parameters_fails(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('users:update_profile', kwargs={"username": self.user.username}))

        self.assertEqual(self.user_profile.professional_wiki_handle, "")
        self.assertEqual(response.status_code, 200)
        data = {"professional_wiki_handle": ""}

        response = self.client.post(reverse('users:update_profile', kwargs={"username": self.user.username}), data=data)
        self.assertContains(response, _("Something went wrong!"))

        user_profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(user_profile.professional_wiki_handle, "")


class AccountUserAdminTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username='superuser', password='password', email='admin@example.com')
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.account_user_admin = AccountUserAdmin(User, self.site)

    def test_add_view_sets_inlines_to_empty_list(self):
        url = reverse('admin:auth_user_add')
        request = self.factory.get(url)
        request.user = self.user
        response = self.account_user_admin.add_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.account_user_admin.inlines, [])

    def test_change_view_sets_inlines_to_user_profile_inline(self):
        user = User.objects.create_user(username='username', password='password')
        url = reverse('admin:auth_user_change', args=[user.pk])
        request = self.factory.get(url)
        request.user = self.user
        response = self.account_user_admin.change_view(request, object_id=str(user.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.account_user_admin.inlines, [UserProfileInline])


class OauthViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_login_oauth_redirect(self):
        request = self.factory.get("/fake-login/")
        response = login_oauth(request)
        expected_url = reverse("users:social:begin", kwargs={"backend": "mediawiki"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_url)

    @patch("users.views.logout")
    def test_logout_oauth_redirect_and_logout_called(self, mock_logout):
        request = self.factory.get("/fake-logout/")
        response = logout_oauth(request)

        mock_logout.assert_called_once_with(request)
        expected_url = reverse("metrics:index")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected_url)


class ListProfilesViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(username="admin", password="pass", email="admin@test.com")
        self.staff = User.objects.create_user(username="bob", password="pass", is_staff=True)
        self.user = User.objects.create_user(username="alice", password="pass")
        self.url = reverse("users:list_profiles")

    def test_denies_non_superuser(self):
        self.client.login(username="alice", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_allows_superuser(self):
        self.client.login(username="admin", password="pass")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_uses_correct_template(self):
        self.client.login(username="admin", password="pass")
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "users/list_profiles.html")

    def test_context_can_edit_true(self):
        self.client.login(username="admin", password="pass")
        response = self.client.get(self.url)
        self.assertTrue(response.context["can_edit"])


class AssociateByWikiHandleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="django_user", password="pass"
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            professional_wiki_handle="WikiHandle"
        )

    def test_returns_existing_authenticated_user(self):
        result = associate_by_wiki_handle(
            backend=None,
            uid="123",
            user=self.user,
        )
        self.assertEqual(result["user"], self.user)

    def test_matches_by_profile_wiki_handle_case_insensitive(self):
        result = associate_by_wiki_handle(
            backend=None,
            uid="123",
            details={"username": "wikihandle"},
        )
        self.assertEqual(result["user"], self.user)

    def test_fallback_matches_by_username(self):
        other = User.objects.create_user(
            username="WikiUser", password="pass"
        )
        result = associate_by_wiki_handle(
            backend=None,
            uid="123",
            details={"username": "WikiUser"},
        )
        self.assertEqual(result["user"], other)

    def test_no_match_returns_empty_dict(self):
        result = associate_by_wiki_handle(
            backend=None,
            uid="123",
            details={"username": "unknown"},
        )
        self.assertEqual(result, {})

    def test_missing_details_is_safe(self):
        result = associate_by_wiki_handle(
            backend=None,
            uid="123",
        )
        self.assertEqual(result, {})


class GetUsernameTests(TestCase):
    def test_existing_user_keeps_username(self):
        user = User.objects.create_user(username="keepme", password="pass")
        result = get_username(
            strategy=None,
            details={"username": "ignored"},
            user=user,
        )
        self.assertEqual(result, {"username": "keepme"})

    def test_new_user_uses_details_username(self):
        result = get_username(
            strategy=None,
            details={"username": "wikiname"},
            user=None,
        )
        self.assertEqual(result, {"username": "wikiname"})