from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


# ======================================================================================================================
# STRATEGIC PROCESS
# ======================================================================================================================
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
    active = models.BooleanField(_("Active"), default=True, help_text=_("Whether this axis is from the active Strategy."))

    class Meta:
        verbose_name = _("Strategic axis")
        verbose_name_plural = _("Strategic axes")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field!"))


class Direction(models.Model):
    """
    Represents a direction in the organization or project.
    Attributes:
        - text (str): The name or description of the direction.

    Meta:
        - verbose_name: Human-readable singular name ("Direction").
        - verbose_name_plural: Human-readable plural name ("Directions").

    Methods:
        - __str__: Returns the text of the direction.
        - clean: Validates that the 'text' field is not empty.
    """
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


# ======================================================================================================================
# THEORY OF CHANGE
# ======================================================================================================================
class LearningArea(models.Model):
    """
    Represents a learning area of hte theory of change.

    Attributes:
        - text (str): The name or description of the learning area.

    Meta:
        - verbose_name: Human-readable singular name ("Learning area").
        - verbose_name_plural: Human-readable plural name ("Learning areas").

    Methods:
        - __str__: Returns the text of the direction.
        - clean: Validates that the 'text' field is not empty.
    """
    text = models.CharField(_("Text"), max_length=420, help_text=_("Human-readable name of the learning area."))
    active = models.BooleanField(_("Active"), default=True, help_text=_("Whether this learning area is from the active Strategy."))

    class Meta:
        verbose_name = _("Learning area")
        verbose_name_plural = _("Learning areas")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


class StrategicLearningQuestion(models.Model):
    """
    Represents a strategic learning question.

    Attributes:
        - text (str): The text of the learning question.

    Meta:
        - verbose_name: Human-readable singular name ("Strategic learning question").
        - verbose_name_plural: Human-readable plural name ("Strategic learning questions").

    Methods:
        - __str__: Returns the text of the direction.
        - clean: Validates that the 'text' field is not empty.
    """
    text = models.CharField(_("Text"), max_length=420, help_text=_("Human-readable name of the learning question."))
    learning_area = models.ForeignKey(LearningArea, on_delete=models.CASCADE, related_name='strategic_question', verbose_name=_("Learning area"))

    class Meta:
        verbose_name = _("Strategic learning question")
        verbose_name_plural = _("Strategic learning questions")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


class EvaluationObjective(models.Model):
    """
    Represents a evaluation objective.

    Attributes:
        - text (str): The name or description of the evaluation objective.

    Meta:
        - verbose_name: Human-readable singular name ("Evaluation objective").
        - verbose_name_plural: Human-readable plural name ("Evaluation objectives").

    Methods:
        - __str__: Returns the text of the direction.
        - clean: Validates that the 'text' field is not empty.
    """
    text = models.CharField(_("Text"), max_length=420, help_text=_("Human-readable name of the evaluation objective."))
    learning_area = models.ForeignKey(LearningArea, on_delete=models.CASCADE, null=True, related_name='evaluation_objective', verbose_name=_("Learning area"))

    class Meta:
        verbose_name = _("Evaluation objective")
        verbose_name_plural = _("Evaluation objectives")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))
