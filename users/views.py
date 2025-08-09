from django.db import transaction
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.utils.translation import gettext as _
from .forms import UserProfileForm, UserForm, NewUserForm
from .models import User


@login_required
@transaction.atomic
def update_profile(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    user_form = UserForm(instance=user)
    user_profile_form = UserProfileForm(request.POST or None, instance=user.userprofile)
    position = user.userprofile.position
    if request.method == "POST":
        if user_profile_form.is_valid():
            user_profile_form.save()
            messages.success(request, _("Changes done successfully!"))
        else:
            messages.error(request, _("Something went wrong!"))

    context = {"userform": user_form, "userprofileform": user_profile_form, "position": position, "title": _("Profile %(user)s") % {"user": user_id}}
    return render(request, "users/profile.html", context)


@permission_required('auth.add_user')
def register(request):
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db()
            user.is_staff = True
            user.save()
            messages.success(request, _("Registration successful."))
            return redirect(reverse("user:profile", kwargs={"user_id": user.pk}))
        messages.error(request, _("Unsuccessful registration. Invalid information."))
    form = NewUserForm()
    context = {"register_form": form, "title": _("Add new user")}
    return render(request, "users/register.html", context)


def login_oauth(request):
    return redirect(reverse("users:social:begin", kwargs={"backend": "mediawiki"}))


def logout_oauth(request):
    logout(request)
    return redirect(reverse("metrics:index"))