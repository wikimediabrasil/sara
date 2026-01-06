from django.db import transaction
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import permission_required, user_passes_test
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.utils.translation import gettext as _
from .forms import UserProfileForm, UserForm
from .models import User


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
    user = get_object_or_404(User, username=username)
    request_user = request.user
    user_form = UserForm(request.POST or None, instance=user)
    user_profile_form = UserProfileForm(request.POST or None, instance=user.profile, request_user=request_user)

    if request.method == "POST":
        if user_form.is_valid() and user_profile_form.is_valid():
            user_form.save()
            user_profile_form.save()
            messages.success(request, _("Changes done successfully!"))
        else:
            messages.error(request, _("Something went wrong!"))

    context = {"user_form": user_form, "profile_form": user_profile_form, "title": username}
    return render(request, "users/update_profile.html", context)


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
    user = get_object_or_404(User, username=username)
    request_user = request.user
    can_delete = request_user.has_perm("users.delete_user")
    can_edit = can_delete or request_user == user
    context = {"user": user, "title": username, "can_edit": can_edit, "can_delete": can_delete}
    return render(request, "users/detail_profile.html", context)


@user_passes_test(lambda u: u.is_superuser)
def list_profiles(request):
    can_edit = request.user.is_superuser
    users = User.objects.all()
    sorted_users = users.order_by("-is_staff", "username")
    context = {"users": sorted_users, "can_edit": can_edit}
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
