from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db.models import RestrictedError
from django.contrib.auth.models import Group
from django.contrib.auth.admin import User
from django.test.client import RequestFactory
from django.contrib.admin.sites import AdminSite
from django.utils.translation import gettext as _
from .models import TeamArea, Position, UserProfile
from .admin import AccountUserAdmin, UserProfileInline
from agenda.models import Event
import datetime
from django.contrib.auth.models import Permission


class TeamAreaModelTests(TestCase):
    def setUp(self):
        self.text = "Team Area"
        self.code = "team_area"
        self.color_code = "t1"
        self.team_area = TeamArea.objects.create(text=self.text, code=self.code)

    def test_str_method(self):
        self.assertEqual(str(self.team_area), self.text)

    def test_clean_method(self):
        team_area2 = TeamArea.objects.create(text="Team Area 2", code="team_area_2", color_code="t2")
        team_area2.full_clean()

        with self.assertRaises(ValidationError):
            team_area2.text = ""
            team_area2.full_clean()

        with self.assertRaises(ValidationError):
            team_area2.text = self.text
            team_area2.code = ""
            team_area2.full_clean()

        with self.assertRaises(ValidationError):
            team_area2.code = self.code
            team_area2.color_code = ""
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

    def test_deleting_team_area_deletes_position_as_well(self):
        self.assertEqual(Position.objects.count(), 1)
        self.area_associated.delete()
        self.assertEqual(Position.objects.count(), 0)

    def test_deleting_group_deletes_position_as_well(self):
        self.assertEqual(Position.objects.count(), 1)
        self.group.delete()
        self.assertEqual(Position.objects.count(), 0)


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

    def test_clean_method(self):
        with self.assertRaises(ValidationError):
            user = User.objects.create(username="username2",
                                       email="email2@email.com",
                                       first_name="First Name 2",
                                       last_name="Last Name 2")
            user_profile = UserProfile.objects.filter(user=user).first()
            user_profile.full_clean()


class UserProfileViewTest(TestCase):
    def setUp(self):
        self.username = "username"
        self.password = "password"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.user_profile = UserProfile.objects.filter(user=self.user).first()

    def test_user_profile_is_only_accessible_by_logged_users(self):
        response = self.client.get(reverse('user:profile', kwargs={"user_id": self.user.pk}))
        self.assertEqual(response.url, f"{reverse('users:login')}?next={reverse('user:profile', kwargs={'user_id': self.user.pk})}")

    def test_user_profile_view_get(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('user:profile', kwargs={"user_id": self.user.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile.html')

    def test_user_profile_view_post(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('user:profile', kwargs={"user_id": self.user.pk}))

        self.assertIsNone(self.user_profile.professional_wiki_handle)
        self.assertEqual(response.status_code, 200)
        data = {"professional_wiki_handle": "Handle"}

        response = self.client.post(reverse('user:profile', kwargs={"user_id": self.user.pk}), data=data)
        self.assertContains(response, _("Changes done successfully!"))

        user_profile = UserProfile.objects.get(user=self.user)
        self.assertIsNotNone(user_profile.professional_wiki_handle)

    def test_user_profile_view_post_with_invalid_parameters_fails(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('user:profile', kwargs={"user_id": self.user.pk}))

        self.assertIsNone(self.user_profile.professional_wiki_handle)
        self.assertEqual(response.status_code, 200)
        data = {"professional_wiki_handle": ""}

        response = self.client.post(reverse('user:profile', kwargs={"user_id": self.user.pk}), data=data)
        self.assertContains(response, _("Something went wrong!"))

        user_profile = UserProfile.objects.get(user=self.user)
        self.assertIsNone(user_profile.professional_wiki_handle)


class RegisterViewTest(TestCase):
    def setUp(self):
        self.username = "username"
        self.password = "password"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.permission = Permission.objects.get(codename="add_user")
        self.user.user_permissions.add(self.permission)

    def test_register_get_view_is_not_accessed_by_users_without_permission(self):
        self.user.user_permissions.remove(self.permission)
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("user:register"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{reverse('users:login')}?next={reverse('user:register')}")

    def test_register_get_view_is_accessed_by_users_with_permission(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse("user:register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/register.html")

    def test_register_post_view_succeeds_in_new_user_creation(self):
        self.client.login(username=self.username, password=self.password)
        data = {
            "username": "new_user",
            "email": "email@email.com",
            "first_name": "First Name",
            "last_name": "Last Name",
            "password1": "(<|&+86]:;C#QZ#I",
            "password2": "(<|&+86]:;C#QZ#I",
        }

        response = self.client.post(reverse("user:register"), data=data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username=data["username"])
        self.assertRedirects(response, reverse('user:profile', kwargs={"user_id":user.pk}))

    def test_register_post_view_fails_in_new_user_creation_with_invalid_parameters(self):
        self.client.login(username=self.username, password=self.password)
        data = {
            "username": "new_user",
            "email": "email@email.com",
            "first_name": "",
            "last_name": "Last Name",
            "password1": "(<|&+86]:;C#QZ#I",
            "password2": "(<|&+86]:;C#QZ#I",
        }

        response = self.client.post(reverse("user:register"), data=data)
        self.assertContains(response, _("Unsuccessful registration. Invalid information."))
        self.assertFalse(User.objects.filter(username=data["username"]).exists())


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