from django.db import models
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from users.models import UserProfile, TeamArea


class Project(models.Model):
    text = models.CharField(max_length=420)
    active = models.BooleanField(default=True)
    current_poa = models.BooleanField(default=False)
    main_funding = models.BooleanField(default=False)
    counts_for_main_funding = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


class Area(models.Model):
    text = models.CharField(max_length=420)
    project = models.ManyToManyField(Project, related_name="project_activity", blank=True)
    poa_area = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Area")
        verbose_name_plural = _("Areas")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


class Objective(models.Model):
    text = models.CharField(max_length=420)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='objectives', null=True)

    class Meta:
        verbose_name = _("Objective")
        verbose_name_plural = _("Objectives")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


class Activity(models.Model):
    text = models.CharField(max_length=420)
    code = models.CharField(max_length=20, null=True)
    area = models.ForeignKey(Area, on_delete=models.RESTRICT, related_name='activities', null=True)
    is_main_activity = models.BooleanField(default=False)
    area_responsible = models.ForeignKey(TeamArea, on_delete=models.RESTRICT, related_name='activity_manager', null=True, blank=True)

    class Meta:
        verbose_name = _("Activity")
        verbose_name_plural = _("Activities")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


class Metric(models.Model):
    text = models.CharField(max_length=420)
    text_en = models.CharField(max_length=420, default="", blank=True)

    # Content metrics
    wikipedia_created = models.IntegerField(null=True, default=0)
    wikipedia_edited = models.IntegerField(null=True, default=0)
    commons_created = models.IntegerField(null=True, default=0)
    commons_edited = models.IntegerField(null=True, default=0)
    wikidata_created = models.IntegerField(null=True, default=0)
    wikidata_edited = models.IntegerField(null=True, default=0)
    wikiversity_created = models.IntegerField(null=True, default=0)
    wikiversity_edited = models.IntegerField(null=True, default=0)
    wikibooks_created = models.IntegerField(null=True, default=0)
    wikibooks_edited = models.IntegerField(null=True, default=0)
    wikisource_created = models.IntegerField(null=True, default=0)
    wikisource_edited = models.IntegerField(null=True, default=0)
    wikinews_created = models.IntegerField(null=True, default=0)
    wikinews_edited = models.IntegerField(null=True, default=0)
    wikiquote_created = models.IntegerField(null=True, default=0)
    wikiquote_edited = models.IntegerField(null=True, default=0)
    wiktionary_created = models.IntegerField(null=True, default=0)
    wiktionary_edited = models.IntegerField(null=True, default=0)
    wikivoyage_created = models.IntegerField(null=True, default=0)
    wikivoyage_edited = models.IntegerField(null=True, default=0)
    wikispecies_created = models.IntegerField(null=True, default=0)
    wikispecies_edited = models.IntegerField(null=True, default=0)
    metawiki_created = models.IntegerField(null=True, default=0)
    metawiki_edited = models.IntegerField(null=True, default=0)
    mediawiki_created = models.IntegerField(null=True, default=0)
    mediawiki_edited = models.IntegerField(null=True, default=0)

    # Community metrics
    number_of_editors = models.IntegerField(null=True, default=0)
    number_of_editors_retained = models.IntegerField(null=True, default=0)
    number_of_new_editors = models.IntegerField(null=True, default=0)
    number_of_participants = models.IntegerField(null=True, default=0)
    number_of_partnerships_activated = models.IntegerField(null=True, default=0)
    number_of_new_partnerships = models.IntegerField(null=True, default=0)
    number_of_organizers = models.IntegerField(null=True, default=0)
    number_of_organizers_retained = models.IntegerField(null=True, default=0)
    number_of_resources = models.IntegerField(null=True, default=0)
    number_of_feedbacks = models.IntegerField(null=True, default=0)
    number_of_events = models.IntegerField(null=True, default=0)

    # Communication metrics
    number_of_new_followers = models.IntegerField(null=True, default=0)
    number_of_mentions = models.IntegerField(null=True, default=0)
    number_of_community_communications = models.IntegerField(null=True, default=0)
    number_of_people_reached_through_social_media = models.IntegerField(null=True, default=0)

    # Financial metrics
    number_of_donors = models.IntegerField(null=True, default=0)
    number_of_submissions = models.IntegerField(null=True, default=0)

    # Other metrics
    boolean_type = models.BooleanField(default=False)
    other_type = models.CharField(null=True, blank=True, max_length=420)
    observation = models.CharField(null=True, blank=True, max_length=420)
    is_operation = models.BooleanField(default=False)

    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="metrics")
    project = models.ManyToManyField(Project, related_name="project_associated", blank=True)

    class Meta:
        verbose_name = _("Metric")
        verbose_name_plural = _("Metrics")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))
