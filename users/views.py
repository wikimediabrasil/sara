from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import (permission_required,
                                            user_passes_test)
from django.db import transaction
from django.db.models import Case, IntegerField, OuterRef, Subquery, When
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from report.views import get_localized_field

from .forms import UserForm, UserPositionForm, UserProfileForm
from .models import Position, User, UserPosition


@permission_required("auth.change_user")
@permission_required("users.change_userprofile")
@transaction.atomic
def update_profile(request, username):
    """
    Update a user's account and profile information.

    This view allows authorized users to edit both the built-in Django
    ``User`` model and the related ``UserProfile`` model in a single,
    atomic transaction.

    Permissions:
        - auth.change_user: required to modify the User model.
        - users.change_userprofile: required to modify the UserProfile model.

    Behavior:
        - Fetches the target user by ``username`` or returns 404 if not found.
        - Initializes forms for ``User`` and ``UserProfile`` using POST data
          when available.
        - On POST:
            - Validates both forms.
            - Saves changes if both are valid.
            - Displays a success message on success, or an error message
              otherwise.
        - Always renders the profile update template with the forms.

    Atomicity:
        - All database changes occur within a single transaction. If either
          save fails, no changes are committed.

    Args:
        request (HttpRequest): The current HTTP request.
        username (str): Username of the user whose profile will be updated.

    Context:
        user_form: Form bound to the User instance.
        profile_form: Form bound to the UserProfile instance.
        title: Localized page title including the username.

    Returns:
        HttpResponse: Rendered response for ``users/update_profile.html``.
    """
    user = get_object_or_404(User, username=username.replace("_", " "))
    request_user = request.user
    profile = user.profile

    current_position = (
        profile.position_history.filter(end_date__isnull=True)
        .order_by("-start_date")
        .first()
    )
    user_form = UserForm(request.POST or None, instance=user)
    user_profile_form = UserProfileForm(request.POST or None, instance=user.profile)
    user_position_form = UserPositionForm(
        request.POST or None, instance=current_position, request_user=request_user
    )

    if request.method == "POST":
        if (
            user_form.is_valid()
            and user_profile_form.is_valid()
            and user_position_form.is_valid()
        ):
            with transaction.atomic():
                user_form.save()
                user_profile_form.save()

                # Only superusers can change positions
                if request_user.is_superuser and user_position_form.cleaned_data.get(
                    "position"
                ):
                    update_user_position(
                        profile=profile,
                        position=user_position_form.cleaned_data["position"],
                        start_date=user_position_form.cleaned_data["start_date"],
                        end_date=user_position_form.cleaned_data["end_date"],
                    )

                messages.success(request, _("Changes done successfully!"))
        else:
            messages.error(request, _("Something went wrong!"))

    context = {
        "user_form": user_form,
        "profile_form": user_profile_form,
        "position_form": user_position_form,
        "title": username,
        "user": user,
    }

    return render(request, "users/update_profile.html", context)


def update_user_position(*, profile, position, start_date, end_date):
    current = profile.position_history.filter(end_date__isnull=True).first()

    if not current:
        UserPosition.objects.create(
            user_profile=profile,
            position=position,
            start_date=start_date,
            end_date=end_date,
        )
        return

    if current.position == position:
        current.start_date = start_date
        current.end_date = end_date
        current.save()
        return

    current.end_date = start_date
    current.save()

    UserPosition.objects.create(
        user_profile=profile,
        position=position,
        start_date=start_date,
        end_date=end_date,
    )


@permission_required("auth.view_user")
@permission_required("users.view_userprofile")
def detail_profile(request, username):
    """
    Display a user's profile details.

    This view renders a read-only profile page for a given user, enforcing
    view permissions on both the Django ``User`` model and the related
    ``UserProfile``.

    Permissions:
        - auth.view_user: required to view the User model.
        - users.view_userprofile: required to view the UserProfile model.

    Behavior:
        - Retrieves the user by ``username`` or returns 404 if not found.
        - Determines whether the requesting user can edit or delete the profile:
            - can_delete: user has ``users.delete_user`` permission.
            - can_edit: user can delete, or is viewing their own profile.
        - Renders the profile detail template with permission flags.

    Args:
        request (HttpRequest): The current HTTP request.
        username (str): Username of the profile to display.

    Context:
        user: The target User instance.
        title: Page title (username).
        can_edit: Whether the requester can edit the profile.
        can_delete: Whether the requester can delete the user.

    Returns:
        HttpResponse: Rendered response for ``users/detail_profile.html``.
    """
    user = get_object_or_404(User, username=username.replace("_", " "))
    request_user = request.user

    can_delete = request_user.has_perm("users.delete_user")
    can_edit = can_delete or request_user == user

    profile = user.profile

    current_or_last_position = (
        profile.position_history.annotate(
            is_finished=Case(
                When(end_date__isnull=True, then=0),
                default=1,
                output_field=IntegerField(),
            )
        )
        .order_by("is_finished", "-start_date")
        .first()
    )

    context = {
        "user": user,
        "profile": profile,
        "current_position": current_or_last_position,
        "title": username,
        "can_edit": can_edit,
        "can_delete": can_delete,
    }
    return render(request, "users/detail_profile.html", context)


@user_passes_test(lambda u: u.is_superuser)
def list_profiles(request):
    can_edit = request.user.is_superuser
    current_language = get_language()

    available_fields = [
        f.name for f in Position._meta.get_fields() if f.name.startswith("text")
    ]
    current_field = get_localized_field(current_language, available_fields)

    latest_position = UserPosition.objects.filter(
        user_profile=OuterRef("profile")
    ).order_by("-start_date")
    earliest_position = UserPosition.objects.filter(
        user_profile=OuterRef("profile")
    ).order_by("start_date")
    users_sorted = (
        User.objects.annotate(
            latest_end_date=Subquery(latest_position.values("end_date")[:1]),
            earliest_start_date=Subquery(earliest_position.values("start_date")[:1]),
            latest_position_text=Subquery(
                latest_position.values(f"position__{current_field}")[:1]
            ),
        )
        .filter(profile__position_history__isnull=False)
        .order_by(
            "-is_staff",
            "latest_end_date",
            "earliest_start_date",
            "latest_position_text",
            "username",
        )
    )

    active_users = users_sorted.filter(
        profile__position_history__end_date__isnull=True
    ).distinct()
    inactive_users = users_sorted.exclude(
        id__in=active_users.values_list("id", flat=True)
    ).distinct()

    context = {
        "active_users": active_users,
        "inactive_users": inactive_users,
        "can_edit": can_edit,
    }
    return render(request, "users/list_profiles.html", context)


def login_oauth(request):
    """
    Initiate OAuth login using the MediaWiki backend.

    This view redirects the user to the social-auth login flow configured
    for the ``mediawiki`` backend.

    Args:
        request (HttpRequest): The current HTTP request.

    Returns:
        HttpResponseRedirect: Redirect to the OAuth provider login URL.
    """
    return redirect(reverse("users:social:begin", kwargs={"backend": "mediawiki"}))


def logout_oauth(request):
    """
    Log out the current user and redirect to the metrics index page.

    This view clears the authenticated session using Django's ``logout``
    function and then redirects the user to the application's main
    metrics page.

    Args:
        request (HttpRequest): The current HTTP request.

    Returns:
        HttpResponseRedirect: Redirect to the ``metrics:index`` URL.
    """
    logout(request)
    return redirect(reverse("metrics:index"))
