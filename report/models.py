from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.dispatch import receiver
from django.db.models.signals import post_save

from metrics.link_utils import build_wikiref
from metrics.models import Activity, Project, Metric
from users.models import TeamArea, UserProfile
from strategy.models import StrategicAxis, Direction


class Funding(models.Model):
    name = models.CharField(max_length=420)
    project = models.ForeignKey(Project, related_name="project_related", on_delete=models.RESTRICT)
    value = models.FloatField(null=True, blank=True, default=0)

    class Meta:
        verbose_name = _("Funding")
        verbose_name_plural = _("Fundings")

    def __str__(self):
        return self.name


class Editor(models.Model):
    username = models.CharField(max_length=420)
    retained = models.BooleanField(default=False)
    retained_at = models.DateField(null=True, blank=True)
    account_creation_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Editor")
        verbose_name_plural = _("Editors")

    def __str__(self):
        return self.username


class Partner(models.Model):
    name = models.CharField(max_length=420)
    website = models.URLField(null=True, blank=True)

    class Meta:
        verbose_name = _("Partner")
        verbose_name_plural = _("Partners")

    def __str__(self):
        return self.name


class Organizer(models.Model):
    name = models.CharField(max_length=420)
    retained = models.BooleanField(default=False)
    institution = models.ManyToManyField(Partner, related_name="organizer_institution")

    class Meta:
        verbose_name = _("Organizer")
        verbose_name_plural = _("Organizers")

    def __str__(self):
        return self.name


class Technology(models.Model):
    name = models.CharField(max_length=420)

    class Meta:
        verbose_name = _("Technology")
        verbose_name_plural = _("Technologies")

    def __str__(self):
        return self.name


class AreaActivated (models.Model):
    text = models.TextField(_("Name of the area activated"), max_length=420)
    contact = models.TextField(max_length=420, null=True, blank=True)

    class Meta:
        verbose_name = _("Area activated")
        verbose_name_plural = _("Areas activated")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


@receiver(post_save, sender=TeamArea)
def save_team_area_as_area_activated(sender, instance, created, **kwargs):
    if created:
        contact = ""
        AreaActivated.objects.create(text=instance.text, contact=contact)


class LearningArea(models.Model):
    text = models.CharField(max_length=420)

    class Meta:
        verbose_name = _("Learning area")
        verbose_name_plural = _("Learning areas")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


class StrategicLearningQuestion(models.Model):
    text = models.CharField(max_length=420)
    learning_area = models.ForeignKey(LearningArea, on_delete=models.CASCADE, related_name='strategic_question')

    class Meta:
        verbose_name = _("Strategic learning question")
        verbose_name_plural = _("Strategic learning questions")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


class EvaluationObjective(models.Model):
    text = models.CharField(max_length=420)
    learning_area_of_objective = models.ForeignKey(LearningArea, on_delete=models.CASCADE, null=True,
                                                   related_name='evaluation_objective')

    class Meta:
        verbose_name = _("Evaluation objective")
        verbose_name_plural = _("Evaluation objectives")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


class Report(models.Model):
    created_by = models.ForeignKey(UserProfile, on_delete=models.RESTRICT, related_name="user_reporting")
    modified_by = models.ForeignKey(UserProfile, on_delete=models.RESTRICT, related_name="user_modifying")
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now_add=True)
    locked = models.BooleanField(default=False)
    reference_text = models.TextField(max_length=10000, blank=True, null=True, default="")

    # Administrative fields
    activity_associated = models.ForeignKey(Activity, on_delete=models.RESTRICT, related_name="report_activity", null=True, blank=True)
    partial_report = models.BooleanField(blank=True, default=False)
    activity_other = models.TextField(max_length=420, blank=True, default="")
    area_responsible = models.ForeignKey(TeamArea, on_delete=models.RESTRICT, related_name="responsible")
    area_activated = models.ManyToManyField(AreaActivated, related_name="area_activated", blank=True)
    initial_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(max_length=420)
    funding_associated = models.ManyToManyField(Funding, related_name="funding_associated", blank=True)
    links = models.TextField(max_length=10000, blank=False)
    private_links = models.BooleanField(blank=True, default=False)
    public_communication = models.TextField(max_length=10000, null=True, blank=True, default="")

    # Content metrics
    wikipedia_created = models.IntegerField(blank=True, default=0)
    wikipedia_edited = models.IntegerField(blank=True, default=0)
    commons_created = models.IntegerField(blank=True, default=0)
    commons_edited = models.IntegerField(blank=True, default=0)
    wikidata_created = models.IntegerField(blank=True, default=0)
    wikidata_edited = models.IntegerField(blank=True, default=0)
    wikiversity_created = models.IntegerField(blank=True, default=0)
    wikiversity_edited = models.IntegerField(blank=True, default=0)
    wikibooks_created = models.IntegerField(blank=True, default=0)
    wikibooks_edited = models.IntegerField(blank=True, default=0)
    wikisource_created = models.IntegerField(blank=True, default=0)
    wikisource_edited = models.IntegerField(blank=True, default=0)
    wikinews_created = models.IntegerField(blank=True, default=0)
    wikinews_edited = models.IntegerField(blank=True, default=0)
    wikiquote_created = models.IntegerField(blank=True, default=0)
    wikiquote_edited = models.IntegerField(blank=True, default=0)
    wiktionary_created = models.IntegerField(blank=True, default=0)
    wiktionary_edited = models.IntegerField(blank=True, default=0)
    wikivoyage_created = models.IntegerField(blank=True, default=0)
    wikivoyage_edited = models.IntegerField(blank=True, default=0)
    wikispecies_created = models.IntegerField(blank=True, default=0)
    wikispecies_edited = models.IntegerField(blank=True, default=0)
    metawiki_created = models.IntegerField(blank=True, default=0)
    metawiki_edited = models.IntegerField(blank=True, default=0)
    mediawiki_created = models.IntegerField(blank=True, default=0)
    mediawiki_edited = models.IntegerField(blank=True, default=0)

    # Community metrics
    editors = models.ManyToManyField(Editor, related_name="editors", blank=True)
    participants = models.IntegerField(blank=True, default=0)
    organizers = models.ManyToManyField(Organizer, related_name="organizers", blank=True)
    feedbacks = models.IntegerField(blank=True, default=0)

    # Operational metrics
    partners_activated = models.ManyToManyField(Partner, related_name="partners", blank=True)

    # Other metrics
    technologies_used = models.ManyToManyField(Technology, related_name="tecnologies", blank=True)

    # Strategy
    directions_related = models.ManyToManyField(Direction, related_name="direction_related", blank=True)
    learning = models.TextField(max_length=5000, null=True, blank=True, default="")

    # Theory of Change
    learning_questions_related = models.ManyToManyField(StrategicLearningQuestion, related_name="strategic_learning_question_related", blank=True)

    # Metrics associated
    metrics_related = models.ManyToManyField(Metric, related_name="metrics_related", blank=False)

    # Financial metrics
    donors = models.IntegerField(null=True, default=0)
    submissions = models.IntegerField(null=True, default=0)

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        permissions = [
            ("can_edit_locked_report", "Can edit locked report"),
        ]

    def save(self, *args, **kwargs):
        super(Report, self).save(*args, **kwargs)
        if not self.end_date:
            self.end_date = self.initial_date
        if not self.reference_text:
            self.reference_text = build_wikiref(self.links, self.pk)

    def __str__(self):
        return self.description


class OperationReport(models.Model):
    metric = models.ForeignKey(Metric, related_name="operation_metric", on_delete=models.RESTRICT)
    report = models.ForeignKey(Report, related_name="operation_report", on_delete=models.CASCADE)

    # Communication metrics
    number_of_people_reached_through_social_media = models.IntegerField(blank=True, default=0)
    number_of_new_followers = models.IntegerField(blank=True, default=0)
    number_of_mentions = models.IntegerField(blank=True, default=0)
    number_of_community_communications = models.IntegerField(blank=True, default=0)

    # Operational metrics
    number_of_events = models.IntegerField(blank=True, default=0)
    number_of_resources = models.IntegerField(blank=True, default=0)
    number_of_partnerships_activated = models.IntegerField(blank=True, default=0)
    number_of_new_partnerships = models.IntegerField(blank=True, default=0)

    def __str__(self):
        return self.report.description + " - " + self.metric.text