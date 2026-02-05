from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext as _

from users.models import TeamArea


# CALENDAR OF EVENTS
class Event(models.Model):
    """
    Represents an event in the agenda of the team.

    Attributes:
        - name: Title of the event
        - initial_date: Date of the beginning of the event
        - end_date: Date of the ending of the event
        - area_responsible: Area responsible for the event

    Meta:
        - verbose_name: A human-readable name for the model (singular).
        - verbose_name_plural: A human-readable name for the model (plural).

    Methods:
        - __str__: Returns a string representation of the event, including the name and date range.
        - clean: Validates that the event has an initial date earlier of the end date.
    """

    name = models.CharField(
        _("Name"), max_length=420, help_text=_("Title of the event")
    )
    initial_date = models.DateField(
        _("Initial date"), help_text="Date of the beginning of the event"
    )
    end_date = models.DateField(
        _("End date"), help_text="Date of the ending of the event"
    )
    area_responsible = models.ForeignKey(
        TeamArea,
        on_delete=models.RESTRICT,
        related_name="events",
        verbose_name=_("Area responsible"),
        help_text="Area responsible for the event",
    )

    class Meta:
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        ordering = ["initial_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F("initial_date")),
                name="event_end_date_after_start_date",
            ),
        ]

    def __str__(self):
        if self.end_date == self.initial_date:
            return self.name + " (" + self.initial_date.strftime("%d/%b") + ")"
        else:
            return (
                self.name
                + " ("
                + self.initial_date.strftime("%d/%b")
                + " - "
                + self.end_date.strftime("%d/%b")
                + ")"
            )

    def clean(self):
        if self.end_date < self.initial_date:
            raise ValidationError({"end_date": _("End date must be after start date.")})
