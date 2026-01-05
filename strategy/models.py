from django.db import models
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError


class StrategicAxis(models.Model):
    """
    Represents a high-level strategic axis in the organization or project.

    Attributes:
        - text (str): The name or description of the strategic axis. Required.
        - intentionality (str): Optional explanation of the intentionality behind this axis.

    Meta:
        - verbose_name: Human-readable singular name ("Strategic axis").
        - verbose_name_plural: Human-readable plural name ("Strategic axes").

    Methods:
        - __str__: Returns the text of the strategic axis.
        - clean: Validates that the 'text' field is not empty.
    """
    text = models.CharField(_("Text"), max_length=420, help_text=_("Human-readable name of the Strategic axis."))
    intentionality = models.CharField(_("Intentionality"), max_length=420, null=True, blank=True, help_text=_("Explanation of the intentionality behind this axis."))

    class Meta:
        verbose_name = _("Strategic axis")
        verbose_name_plural = _("Strategic axes")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field!"))


class Direction(models.Model):
    text = models.CharField(_("Text"), max_length=420, help_text=_("Human-readable name of the direction."))
    strategic_axis = models.ForeignKey(StrategicAxis, on_delete=models.CASCADE, related_name='directions', verbose_name=_("Strategic axis"))

    class Meta:
        verbose_name = _("Direction")
        verbose_name_plural = _("Directions")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field!"))
