from datetime import date

from django import forms
from django.contrib.auth.models import User

from .models import UserPosition, UserProfile

"""
Forms related to user creation and profile management.

Includes:
- Basic User name editing
- Full UserProfile editing
- Extended user creation with required personal data
"""


class UserForm(forms.ModelForm):
    """Edit basic User identity fields."""

    class Meta:
        model = User
        fields = ("first_name", "last_name")


class UserProfileForm(forms.ModelForm):
    """Form for managing organization-specific user profile data."""

    class Meta:
        model = UserProfile
        fields = "__all__"
        exclude = ["user"]
        required_css_class = "required"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["professional_wiki_handle"].required = True

    def save(self, commit=True):
        # Allow deferred save when profile is linked elsewhere
        user_profile = super(UserProfileForm, self).save(commit=False)
        if commit:
            user_profile.save()
        return user_profile


class UserPositionForm(forms.ModelForm):
    """Form for managing user position data."""

    class Meta:
        model = UserPosition
        fields = ["position", "start_date", "end_date"]
        widgets = {
            "start_date": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user_profile = kwargs.pop("user_profile", None)
        request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)

        # permissions
        if request_user and not request_user.is_superuser:
            for field in self.fields.values():
                field.disabled = True

        # default only when creating a NEW position
        if not self.instance.pk and not self.initial.get("start_date"):
            self.initial["start_date"] = date.today()

    def save(self, commit=True):
        user_position = super().save(commit=False)

        if self.user_profile:
            user_position.user_profile = self.user_profile

        if commit:
            user_position.save()

        return user_position
