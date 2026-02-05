"""
Forms for bug tracking.


This module defines ModelForms used to create and update Bug reports
and their related Observations.


Design goals:
- Explicit separation between creation and update responsibilities.
- Prevent accidental edits to immutable fields.
- Keep forms thin; business rules live in models.
"""

from django import forms

from .models import Bug, Observation


class BugForm(forms.ModelForm):
    """
    Form used to create a new Bug.


    The bug status is intentionally excluded and should be set
    automatically by the system.
    """

    class Meta:
        model = Bug
        exclude = ["status", "reporter"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class BugUpdateForm(forms.ModelForm):
    """
    Form used to update an existing Bug.


    Core descriptive fields are read-only to preserve the original
    report context. Status updates are allowed.
    """

    class Meta:
        model = Bug
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("title", "description", "bug_type", "reporter"):
            if field in self.fields:
                self.fields[field].disabled = True


class ObservationForm(forms.ModelForm):
    """
    Form used to create or edit an Observation.


    The related Bug is injected by the view and therefore not exposed
    to the user.
    """

    class Meta:
        model = Observation
        exclude = ["bug_report"]
        widgets = {
            "observation": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
