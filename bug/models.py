from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models import UserProfile


class Bug(models.Model):
    """
    Represents a bug report, feature request, or improvement.


    A Bug is created by a reporter and progresses through a defined
    workflow (status) until completion or cancellation.
    """

    class Status(models.TextChoices):
        """Lifecycle states of a bug."""

        TODO = "0", _("To do")
        EVAL = "1", _("In evaluation")
        PROG = "2", _("In progress")
        TEST = "3", _("Testing")
        DONE = "4", _("Done")
        CANC = "5", _("Canceled")

    class BugType(models.TextChoices):
        """High-level classification of the report."""

        ERROR = "1", _("Error")
        IMPROVEMENT = "2", _("Improvement request")
        NEWFEATURE = "3", _("New feature request")
        CLARIFICATION = "4", _("Question or clarification")

    title = models.CharField(
        _("Title"),
        max_length=140,
        help_text=_("Short, descriptive summary of the issue."),
    )
    description = models.TextField(
        _("Description"),
        max_length=500,
        help_text=_("Detailed explanation of the problem or request."),
    )
    bug_type = models.CharField(
        _("Type"),
        max_length=1,
        choices=BugType.choices,
        default=BugType.ERROR,
        help_text=_("Category of the reported issue."),
    )
    status = models.CharField(
        _("Status"),
        max_length=1,
        choices=Status.choices,
        default=Status.EVAL,
        help_text=_("Status of the reported issue."),
    )
    report_date = models.DateField(
        _("Date of report"),
        auto_now_add=True,
        editable=False,
        help_text=_("Timestamp when the bug was created."),
    )
    reporter = models.ForeignKey(
        UserProfile,
        on_delete=models.RESTRICT,
        related_name="reporter",
        editable=False,
        help_text=_("User who reported the bug."),
    )
    update_date = models.DateField(
        _("Update date"), auto_now=True, help_text=_("Date when the bug was updated.")
    )

    class Meta:
        ordering = ["-report_date", "status"]
        verbose_name = _("Bug")
        verbose_name_plural = _("Bugs")

    def __str__(self) -> str:
        return f"{self.get_bug_type_display()}: {self.title}"


class Observation(models.Model):
    """
    Final observation or response associated with a bug.


    Intended to store conclusions, resolutions, or official answers.
    Each Bug may have at most one Observation.
    """

    bug_report = models.OneToOneField(
        Bug,
        on_delete=models.CASCADE,
        related_name="observation",
        help_text=_("Observation associated with a bug."),
    )
    observation = models.TextField(
        _("Observation"),
        max_length=500,
        help_text=_("Resolution notes of final response"),
    )
    answer_date = models.DateTimeField(
        _("Date of answer"),
        auto_now_add=True,
        help_text=_("Date of answer of the observation"),
    )

    class Meta:
        verbose_name = _("Observation")
        verbose_name_plural = _("Observations")

    def __str__(self):
        return _("Observation for bug nº %(bug_id)s") % {"bug_id": self.bug_report_id}
