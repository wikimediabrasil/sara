from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.utils.formats import date_format

User = get_user_model()


class   TeamArea(models.Model):
    text = models.CharField(_("Name"), max_length=420, help_text=_("Human-readable name of the team area"))
    code = models.CharField(_("Code"),
                            max_length=50,
                            unique=True,
                            help_text=_("Short identifier of a CSS class of the team area"))
    project = models.ManyToManyField("metrics.Project",
                                     blank=True,
                                     related_name="team_areas",
                                     verbose_name=_("Projects"),
                                     help_text=_("The projects this team area belongs to"))

    class Meta:
        verbose_name = _("Team area")
        verbose_name_plural = _("Team areas")
        ordering = ['text']

    def __str__(self):
        return self.text


class Position(models.Model):
    text = models.CharField(_("Name"), max_length=420, help_text=_("Human-readable name of the position"))
    type = models.ForeignKey(Group,
                             on_delete=models.PROTECT,
                             verbose_name=_("Permission group"),
                             help_text=_("The permission group this position belongs to"))
    area_associated = models.ForeignKey(TeamArea,
                                        on_delete=models.PROTECT,
                                        related_name="positions",
                                        verbose_name=_("Team Area"),
                                        help_text=_("The team area this position belongs to"))

    class Meta:
        verbose_name = _("Position")
        verbose_name_plural = _("Positions")
        ordering = ['text']
        unique_together = (("area_associated", "text"),)

    def __str__(self):
        return self.text


class UserProfile(models.Model):
    class GenderChoices(models.TextChoices):
        MALE = "male", _("Male")
        FEMALE = "female", _("Female")
        NON_BINARY = "non_binary", _("Non Binary")
        OTHER = "other", _("Other")
        NOT_DECLARED = "not_declared", _("Not declared")

    user = models.OneToOneField(User,
                                on_delete=models.CASCADE,
                                related_name="profile",
                                verbose_name=_("User"),
                                help_text=_("The user which this profile's about"))
    gender = models.CharField(_("Gender"),
                              max_length=20,
                              choices=GenderChoices.choices,
                              blank=True,
                              default=GenderChoices.NOT_DECLARED)
    professional_wiki_handle = models.CharField(_("Professional username"), max_length=50, blank=True, default="")
    personal_wiki_handle = models.CharField(_("Personal username"), max_length=50, blank=True, default="")
    photograph = models.CharField(_("Photograph filename"),
                                  max_length=420,
                                  blank=True,
                                  default="")

    twitter = models.CharField(_("Twitter"), max_length=100, blank=True, default="", help_text=_("Twitter handle"))
    facebook = models.CharField(_("Facebook"), max_length=100, blank=True, default="", help_text=_("Facebook handle"))
    instagram = models.CharField(_("Instagram"), max_length=100, blank=True, default="", help_text=_("Instagram handle"))

    wikidata_item = models.CharField(_("Wikidata item"), max_length=100, blank=True, default="", help_text=_("Wikidata QID"))
    linkedin = models.CharField(_("LinkedIn"), max_length=100, blank=True, default="", help_text=_("LinkedIn handle"))
    lattes = models.CharField(_("Lattes"), max_length=100, blank=True, default="", help_text=_("Lattes ID"))
    orcid = models.CharField(_("ORCID"), max_length=100, blank=True, default="", help_text=_("ORCID ID"))
    google_scholar = models.CharField(_("Google Scholar"), max_length=100, blank=True, default="", help_text=_("Google Scholar ID"))

    class Meta:
        verbose_name = _("User profile")
        verbose_name_plural = _("User profiles")

    def __str__(self):
        return self.professional_wiki_handle or self.user.first_name or self.user.username

    @property
    def current_position(self):
        return (
            self.position_history
            .order_by(
                models.Case(
                    models.When(end_date__isnull=True, then=0),
                    default=1,
                    output_field=models.IntegerField(),
                ),
                "-start_date",
            )
            .first()
        )


class UserPosition(models.Model):
    user_profile = models.ForeignKey(UserProfile,
                                     on_delete=models.CASCADE,
                                     related_name="position_history",
                                     verbose_name=_("User profile"),
                                     help_text=_("The user which this position belongs to during that period")
                                     )
    position = models.ForeignKey(Position,
                                 on_delete=models.PROTECT,
                                 related_name="user_assignments",
                                 verbose_name=_("Position"),
                                 help_text=_("The position this user had during that period")
                                 )
    start_date = models.DateField(verbose_name=_("Start date"), help_text=_("The start date for this user's position"))
    end_date = models.DateField(verbose_name=_("End date"),
                                null=True,
                                blank=True,
                                help_text=_("The end date for this user's position. Leave empty if this is the current position"),
                                )

    class Meta:
        verbose_name = _("User position")
        verbose_name_plural = _("User positions")
        ordering = ["-start_date", "-end_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__isnull=True) | models.Q(end_date__gte=models.F("start_date")),
                name="end_date_after_start_date",
            ),
            models.UniqueConstraint(
                fields=["user_profile"],
                condition=models.Q(end_date__isnull=True),
                name="one_current_position_per_user",
            ),
        ]
        indexes = [
            models.Index(fields=["user_profile", "end_date"]),
            models.Index(fields=["position", "end_date"]),
            models.Index(fields=["start_date"]),
        ]

    def period_display(self):
        start = date_format(self.start_date, format="DATE_FORMAT")

        if self.end_date:
            end = date_format(self.end_date, format="DATE_FORMAT")
            return _("from %(start)s to %(end)s") % {
                "start": start,
                "end": end,
            }

        return _("since %(start)s") % {
            "start": start,
        }

    def __str__(self):
        if self.end_date:
            return _("%(user_profile)s – %(position)s (%(start_date)s → %(end_date)s)") % {
                "user_profile": str(self.user_profile),
                "position": str(self.position),
                "start_date": self.start_date,
                "end_date": self.end_date}
        return _("%(user_profile)s – %(position)s (since %(start_date)s)") % {
            "user_profile": str(self.user_profile),
            "position": str(self.position),
            "start_date": self.start_date
        }


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Creation and association of a user profile to the user upon first login.
    """
    if created:
        UserProfile.objects.create(user=instance)
