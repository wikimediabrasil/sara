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
from django.contrib.messages import get_messages
from django.db import IntegrityError, transaction

from users.models import TeamArea, Position, UserProfile, UserPosition
from users.admin import AccountUserAdmin, UserProfileInline
from users.views import login_oauth, logout_oauth, update_user_position
from users.pipeline import associate_by_wiki_handle, get_username
from users.forms import UserPositionForm
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


class UserPositionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test", password="123")
        self.profile = UserProfile.objects.get(user=self.user)

        self.group = Group.objects.create(name="Manager")
        self.area = TeamArea.objects.create(text="Area", code="area")

        self.position = Position.objects.create(
            text="Position",
            type=self.group,
            area_associated=self.area,
        )

    def test_create_current_position(self):
        up = UserPosition.objects.create(
            user_profile=self.profile,
            position=self.position,
            start_date=datetime.date(2024, 1, 1),
        )

        self.assertIsNone(up.end_date)
        self.assertEqual(self.profile.position_history.count(), 1)

    def test_end_date_before_start_date_raises_error(self):
        with self.assertRaises(IntegrityError):
            UserPosition.objects.create(
                user_profile=self.profile,
                position=self.position,
                start_date=datetime.date(2024, 5, 1),
                end_date=datetime.date(2024, 4, 1),
            )

    def test_only_one_current_position_per_user(self):
        UserPosition.objects.create(
            user_profile=self.profile,
            position=self.position,
            start_date=datetime.date(2023, 1, 1),
        )

        new_position = UserPosition(
            user_profile=self.profile,
            position=self.position,
            start_date=datetime.date(2024, 1, 1),
        )

        with self.assertRaises(ValidationError):
            new_position.full_clean()

    def test_multiple_past_positions_allowed(self):
        UserPosition.objects.create(
            user_profile=self.profile,
            position=self.position,
            start_date=datetime.date(2022, 1, 1),
            end_date=datetime.date(2022, 12, 31),
        )

        UserPosition.objects.create(
            user_profile=self.profile,
            position=self.position,
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2023, 12, 31),
        )

        self.assertEqual(self.profile.position_history.count(), 2)

    def test_period_display_with_end_date(self):
        up = UserPosition.objects.create(
            user_profile=self.profile,
            position=self.position,
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2023, 12, 31),
        )

        text = up.period_display()
        self.assertIn("from", text)
        self.assertIn("to", text)

    def test_period_display_without_end_date(self):
        up = UserPosition.objects.create(
            user_profile=self.profile,
            position=self.position,
            start_date=datetime.date(2024, 1, 1),
        )

        text = up.period_display()
        self.assertIn("since", text)

    def test_str_with_end_date(self):
        up = UserPosition.objects.create(
            user_profile=self.profile,
            position=self.position,
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2023, 12, 31),
        )

        s = str(up)
        self.assertIn("→", s)

    def test_str_without_end_date(self):
        up = UserPosition.objects.create(
            user_profile=self.profile,
            position=self.position,
            start_date=datetime.date(2024, 1, 1),
        )

        s = str(up)
        self.assertIn("since", s)

    def test_ordering_most_recent_first(self):
        older = UserPosition.objects.create(
            user_profile=self.profile,
            position=self.position,
            start_date=datetime.date(2022, 1, 1),
            end_date=datetime.date(2022, 12, 31),
        )

        newer = UserPosition.objects.create(
            user_profile=self.profile,
            position=self.position,
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2023, 12, 31),
        )

        positions = list(UserPosition.objects.all())
        self.assertEqual(positions[0], newer)


class UserPositionFormSaveTest(TestCase):
    def setUp(self):
        self.username = "username"
        self.password = "password"
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.user_profile = UserProfile.objects.filter(user=self.user).first()
        self.group = Group.objects.create(name="Manager")
        self.area = TeamArea.objects.create(text="Area", code="area")
        self.position = Position.objects.create(
            text="Position",
            type=self.group,
            area_associated=self.area,
        )

        self.form_data = {
            "user_profile": self.user_profile.id,
            "position": self.position.id,
            "start_date": datetime.date(2024, 1, 1),
        }

    def test_save_with_commit_true_saves_object(self):
        form = UserPositionForm(data=self.form_data, user_profile=self.user_profile)
        self.assertTrue(form.is_valid())

        user_position = form.save(commit=True)

        self.assertIsNotNone(user_position.pk)
        self.assertEqual(UserPosition.objects.count(), 1)

    def test_save_with_commit_false_does_not_save_object(self):
        form = UserPositionForm(data=self.form_data)
        self.assertTrue(form.is_valid())

        user_position = form.save(commit=False)

        self.assertIsNone(user_position.pk)
        self.assertEqual(UserPosition.objects.count(), 0)


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
        self.area_responsible = TeamArea.objects.create(text="Area responsible", code="Ar code")

    def test_user_profile_when_the_user_has_no_position_has_no_instance(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('users:update_profile', kwargs={"username": self.user.username}))
        self.assertEqual(response.status_code, 200)
        position_form = response.context["position_form"]
        self.assertIsNotNone(position_form)
        self.assertIsNone(position_form.instance.pk)

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

    def test_user_profile_update_post_fails_if_no_position_is_given(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('users:update_profile', kwargs={"username": self.user.username}))

        self.assertEqual(self.user_profile.professional_wiki_handle, "")
        self.assertEqual(response.status_code, 200)
        data = {"professional_wiki_handle": "Handle"}

        response = self.client.post(reverse('users:update_profile', kwargs={"username": self.user.username}), data=data, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(_("Something went wrong!") == str(m) for m in messages))

    def test_user_profile_update_post_saves_profile_without_changing_position_details_if_user_is_not_superuser(self):
        self.client.login(username=self.username, password=self.password)

        self.assertEqual(self.user_profile.professional_wiki_handle, "")

        group = Group.objects.create(name="Manager")
        position = Position.objects.create(
            text="Position",
            type=group,
            area_associated=self.area_responsible,
        )

        user_position = UserPosition.objects.create(
            user_profile=self.user_profile,
            position=position,
            start_date=datetime.date(2023, 3, 24),
        )

        data = {
            "professional_wiki_handle": "Handle",

            "position": position.pk,
            "start_date": "2025-03-24",
        }

        response = self.client.post(
            reverse("users:update_profile", kwargs={"username": self.user.username}),
            data=data,
            follow=True,
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(_("Changes done successfully!") == str(m) for m in messages))

        self.user_profile.refresh_from_db()
        user_position.refresh_from_db()

        self.assertEqual(self.user_profile.professional_wiki_handle, "Handle")

        self.assertEqual(user_position.position, position)
        self.assertEqual(user_position.start_date, datetime.date(2023, 3, 24))

    def test_user_profile_update_post_changes_position_details_if_user_is_superuser(self):
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])

        self.client.login(username=self.username, password=self.password)

        group = Group.objects.create(name="Manager")
        position_1 = Position.objects.create(
            text="Old Position",
            type=group,
            area_associated=self.area_responsible,
        )
        position_2 = Position.objects.create(
            text="New Position",
            type=group,
            area_associated=self.area_responsible,
        )

        UserPosition.objects.create(
            user_profile=self.user_profile,
            position=position_1,
            start_date=datetime.date(2023, 3, 24),
        )

        data = {
            "professional_wiki_handle": "Handle",
            "position": position_2.pk,
            "start_date": "2025-03-24",
            "end_date": "",
        }

        response = self.client.post(
            reverse("users:update_profile", kwargs={"username": self.user.username}),
            data=data,
            follow=True,
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(_("Changes done successfully!") == str(m) for m in messages))

        self.user_profile.refresh_from_db()

        self.assertTrue(self.user_profile.position_history.filter(position=position_2).exists())

        current_position = self.user_profile.position_history.get(end_date__isnull=True)

        self.assertEqual(current_position.position, position_2)
        self.assertEqual(current_position.start_date, datetime.date(2025, 3, 24))
        self.assertIsNone(current_position.end_date)

    def test_user_profile_update_post_succeeds_if_position_is_given_and_user_requesting_is_superuser(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('users:update_profile', kwargs={"username": self.user.username}))

        self.assertEqual(self.user_profile.professional_wiki_handle, "")
        self.assertEqual(response.status_code, 200)
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(text="Position", type=group, area_associated=self.area_responsible)
        user_position = UserPosition.objects.create(user_profile=self.user_profile,
                                               position=position,
                                               start_date=datetime.date(2023, 3, 24))
        data = {"professional_wiki_handle": "Handle", "position": user_position}

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

    def test_update_user_position_creates_position_when_none_exists(self):
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(
            text="Position",
            type=group,
            area_associated=self.area_responsible,
        )

        update_user_position(
            profile=self.user_profile,
            position=position,
            start_date=datetime.date(2024, 1, 1),
            end_date=None,
        )

        positions = self.user_profile.position_history.all()

        self.assertEqual(positions.count(), 1)

        p = positions.first()
        self.assertEqual(p.position, position)
        self.assertEqual(p.start_date, datetime.date(2024, 1, 1))
        self.assertIsNone(p.end_date)

    def test_update_user_position_updates_dates_if_same_position(self):
        group = Group.objects.create(name="Manager")
        position = Position.objects.create(
            text="Position",
            type=group,
            area_associated=self.area_responsible,
        )

        UserPosition.objects.create(
            user_profile=self.user_profile,
            position=position,
            start_date=datetime.date(2023, 1, 1),
            end_date=None,
        )

        update_user_position(
            profile=self.user_profile,
            position=position,
            start_date=datetime.date(2024, 2, 1),
            end_date=datetime.date(2024, 12, 31),
        )

        positions = self.user_profile.position_history.all()

        self.assertEqual(positions.count(), 1)

        p = positions.first()
        self.assertEqual(p.start_date, datetime.date(2024, 2, 1))
        self.assertEqual(p.end_date, datetime.date(2024, 12, 31))

    def test_update_user_position_closes_old_and_creates_new(self):
        group = Group.objects.create(name="Manager")
        position_1 = Position.objects.create(
            text="Old",
            type=group,
            area_associated=self.area_responsible,
        )
        position_2 = Position.objects.create(
            text="New",
            type=group,
            area_associated=self.area_responsible,
        )

        old = UserPosition.objects.create(
            user_profile=self.user_profile,
            position=position_1,
            start_date=datetime.date(2023, 1, 1),
            end_date=None,
        )

        update_user_position(
            profile=self.user_profile,
            position=position_2,
            start_date=datetime.date(2024, 3, 1),
            end_date=None,
        )

        self.assertEqual(self.user_profile.position_history.count(), 2)

        old.refresh_from_db()
        self.assertEqual(old.end_date, datetime.date(2024, 3, 1))

        current = self.user_profile.position_history.get(end_date__isnull=True)
        self.assertEqual(current.position, position_2)
        self.assertEqual(current.start_date, datetime.date(2024, 3, 1))


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
        self.user = User.objects.create_user(username="django_user", password="pass")
        self.user.profile.professional_wiki_handle = "WikiHandle"
        self.user.profile.save()

    def test_returns_existing_authenticated_user(self):
        result = associate_by_wiki_handle(
            backend=None,
            uid="123",
            user=self.user,
        )

        self.assertEqual(result, {"user": self.user})

    def test_matches_by_profile_wiki_handle_case_insensitive(self):
        result = associate_by_wiki_handle(
            backend=None,
            uid="123",
            details={"username": "wikihandle"},
        )

        self.assertEqual(result, {"user": self.user})

    def test_fallback_matches_by_username(self):
        other = User.objects.create_user(
            username="WikiUser", password="pass"
        )

        result = associate_by_wiki_handle(
            backend=None,
            uid="123",
            details={"username": "WikiUser"},
        )

        self.assertEqual(result, {"user": other})

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