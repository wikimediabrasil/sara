from django import forms
from django.contrib.auth.models import User, Group
from .models import UserProfile
from django.contrib.auth.forms import UserCreationForm

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
        exclude = ['user']
        required_css_class = 'required'

    def __init__(self, *args, **kwargs):
        request_user = kwargs.pop("request_user", None)
        super().__init__(*args, **kwargs)

        # Only superusers can change another user's position
        if not (request_user and request_user.is_superuser):
            self.fields["position"].disabled = True

        self.fields['professional_wiki_handle'].required = True

    def save(self, commit=True):
        # Allow deferred save when profile is linked elsewhere
        user_profile = super(UserProfileForm, self).save(commit=False)
        if commit:
            user_profile.save()
        return user_profile
