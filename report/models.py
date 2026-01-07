from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.dispatch import receiver
from django.db.models.signals import post_save

from metrics.link_utils import build_wiki_ref
from metrics.models import Activity, Project, Metric
from users.models import TeamArea, UserProfile
from strategy.models import StrategicAxis, Direction, StrategicLearningQuestion


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
    username = models.CharField(max_length=420, unique=True)
    account_creation_date = models.DateTimeField(null=True, blank=True)
    retained_at = models.DateField(null=True, blank=True)
    retained = models.BooleanField(default=False)

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


class Report(models.Model):
    # ==================================================================================================================
    # IDENTIFICATION
    # ==================================================================================================================
    created_by = models.ForeignKey(UserProfile, on_delete=models.RESTRICT, related_name="user_reporting", verbose_name=_("Created by"), help_text=_("The user who created the report"))
    modified_by = models.ForeignKey(UserProfile, on_delete=models.RESTRICT, related_name="user_modifying", verbose_name=_("Modified by"), help_text=_("The user who modified the report"))
    created_at = models.DateTimeField(_("Date of creation"), auto_now_add=True, help_text=_("Date the report was created"))
    modified_at = models.DateTimeField(_("Date of modification"), auto_now_add=True, help_text=_("Date the report was modified"))
    locked = models.BooleanField(_("Locked"), default=False, help_text=_("Whether the report is locked"))
    reference_text = models.TextField(_("Reference text"), max_length=10000, blank=True, null=True, default="", help_text=_("The reference text of the report, in wikitext"))

    # ==================================================================================================================
    # ADMINISTRATIVE
    # ==================================================================================================================
    activity_associated = models.ForeignKey(Activity, on_delete=models.RESTRICT, related_name="report_activity", null=True, blank=True, verbose_name=_("Activity"), help_text=_("The activity associated with the report"))
    partial_report = models.BooleanField(_("Partial report"), blank=True, default=False, help_text=_("Whether the report is a partial report"))
    area_responsible = models.ForeignKey(TeamArea, on_delete=models.RESTRICT, related_name="responsible", verbose_name=_("Area responsible"), help_text=_("The area responsible for the report"))
    area_activated = models.ManyToManyField(TeamArea, related_name="area_activated", blank=True, verbose_name=_("Areas activated"), help_text=_("The areas activated for the activity"))
    initial_date = models.DateField(_("Initial date"), help_text=_("The initial date of the activity reported"))
    end_date = models.DateField(_("End date"), null=True, blank=True, help_text=_("The end date of the activity reported"))
    description = models.TextField(_("Description"), max_length=420, help_text=_("The description of the activity reported"))
    funding_associated = models.ManyToManyField(Funding, related_name="funding_associated", blank=True, verbose_name=_("Funding associated"), help_text=_("The funding associated with the activity"))
    links = models.TextField(_("Links"), max_length=10000, blank=False, help_text=_("The links associated with the activity"))
    private_links = models.BooleanField(_("Private links"), blank=True, default=False, help_text=_("Whether the links associated with the activity are private"))

    # ==================================================================================================================
    # QUANTITATIVE
    # ==================================================================================================================
    # Content metrics
    wikipedia_created = models.IntegerField(_("Created in Wikipedia"), null=True, default=0, help_text=_("Number of items created/edited on Wikipedia."))
    wikipedia_edited = models.IntegerField(_("Edited in Wikipedia"), null=True, default=0, help_text=_("Number of items edited on Wikipedia."))
    commons_created = models.IntegerField(_("Created in Wikimedia Commons"), null=True, default=0, help_text=_("Number of items created/edited on Wikimedia Commons."))
    commons_edited = models.IntegerField(_("Edited in Wikimedia Commons"), null=True, default=0, help_text=_("Number of items edited on Wikimedia Commons."))
    wikidata_created = models.IntegerField(_("Created in Wikidata"), null=True, default=0, help_text=_("Number of items created/edited on Wikidata."))
    wikidata_edited = models.IntegerField(_("Edited in Wikidata"), null=True, default=0, help_text=_("Number of items created/edited on Wikidata."))
    wikiversity_created = models.IntegerField(_("Created in Wikiversity"), null=True, default=0, help_text=_("Number of items created/edited on Wikiversity."))
    wikiversity_edited = models.IntegerField(_("Edited in Wikiversity"), null=True, default=0, help_text=_("Number of items created/edited on Wikiversity."))
    wikibooks_created = models.IntegerField(_("Created in Wikibooks"), null=True, default=0, help_text=_("Number of items created/edited on Wikibooks."))
    wikibooks_edited = models.IntegerField(_("Edited in Wikibooks"), null=True, default=0, help_text=_("Number of items created/edited on Wikibooks."))
    wikisource_created = models.IntegerField(_("Created in Wikisource"), null=True, default=0, help_text=_("Number of items created/edited on Wikisource."))
    wikisource_edited = models.IntegerField(_("Edited in Wikisource"), null=True, default=0, help_text=_("Number of items created/edited on Wikisource."))
    wikinews_created = models.IntegerField(_("Created in Wikinews"), null=True, default=0, help_text=_("Number of items created/edited on Wikinews."))
    wikinews_edited = models.IntegerField(_("Edited in Wikinews"), null=True, default=0, help_text=_("Number of items created/edited on Wikinews."))
    wikiquote_created = models.IntegerField(_("Created in Wikiquote"), null=True, default=0, help_text=_("Number of items created/edited on Wikiquote."))
    wikiquote_edited = models.IntegerField(_("Edited in Wikiquote"), null=True, default=0, help_text=_("Number of items created/edited on Wikiquote."))
    wiktionary_created = models.IntegerField(_("Created in Wiktionary"), null=True, default=0, help_text=_("Number of items created/edited on Wiktionary."))
    wiktionary_edited = models.IntegerField(_("Edited in Wiktionary"), null=True, default=0, help_text=_("Number of items created/edited on Wiktionary."))
    wikivoyage_created = models.IntegerField(_("Created in Wikivoyage"), null=True, default=0, help_text=_("Number of items created/edited on Wikivoyage."))
    wikivoyage_edited = models.IntegerField(_("Edited in Wikivoyage"), null=True, default=0, help_text=_("Number of items created/edited on Wikivoyage."))
    wikispecies_created = models.IntegerField(_("Created in Wikispecies"), null=True, default=0, help_text=_("Number of items created/edited on Wikispecies."))
    wikispecies_edited = models.IntegerField(_("Edited in Wikispecies"), null=True, default=0, help_text=_("Number of items created/edited on Wikispecies."))
    metawiki_created = models.IntegerField(_("Created in Meta-Wiki"), null=True, default=0, help_text=_("Number of items created/edited on Meta-Wiki."))
    metawiki_edited = models.IntegerField(_("Edited in Meta-Wiki"), null=True, default=0, help_text=_("Number of items created/edited on Meta-Wiki."))
    mediawiki_created = models.IntegerField(_("Created in Mediawiki"), null=True, default=0, help_text=_("Number of items created/edited on Mediawiki."))
    mediawiki_edited = models.IntegerField(_("Edited in Mediawiki"), null=True, default=0, help_text=_("Number of items created/edited on Mediawiki."))
    wikifunctions_created = models.IntegerField(_("Created in WikiFunctions"), null=True, default=0, help_text=_("Number of items created/edited on WikiFunctions."))
    wikifunctions_edited = models.IntegerField(_("Edited in WikiFunctions"), null=True, default=0, help_text=_("Number of items created/edited on WikiFunctions."))
    incubator_created = models.IntegerField(_("Created in Wikimedia Incubator"), null=True, default=0, help_text=_("Number of items created/edited on Wikimedia Incubator."))
    incubator_edited = models.IntegerField(_("Edited in Wikimedia Incubator"), null=True, default=0, help_text=_("Number of items created/edited on Wikimedia Incubator."))

    # Community metrics
    editors = models.ManyToManyField(Editor, related_name="editors", blank=True, verbose_name=_("Editors"), help_text=_("Editors registered of the activity reported."))
    participants = models.IntegerField(_("Participants"), blank=True, default=0, help_text=_("Number of participants of the activity reported."))
    organizers = models.ManyToManyField(Organizer, related_name="organizers", blank=True, verbose_name=_("Organizers"), help_text=_("Organizers registered of the activity reported."))
    feedbacks = models.IntegerField(_("Feedbacks"), blank=True, default=0, help_text=_("Number of people providing feedback on the activity reported."))
    partners_activated = models.ManyToManyField(Partner, related_name="partners", blank=True, verbose_name=_("Partnerships activated"), help_text=_("Formal partners (institutions) activated of the activity reported."))

    # Other metrics
    technologies_used = models.ManyToManyField(Technology, related_name="technologies", blank=True, verbose_name=_("Technologies used"), help_text=_("Technologies used on the activity reported."))

    # ==================================================================================================================
    # STRATEGY
    # ==================================================================================================================
    directions_related = models.ManyToManyField(Direction, related_name="direction_related", blank=True, verbose_name=_("Directions related"), help_text=_("Directions guiding the activity reported."))

    # ==================================================================================================================
    # LEARNING
    # ==================================================================================================================
    learning_questions_related = models.ManyToManyField(StrategicLearningQuestion, related_name="strategic_learning_question_related", blank=True, verbose_name=_("Strategic Learning Question"), help_text=_("Strategic learning questions the activity reported tries to answer or reflects on."))
    learning = models.TextField(_("Learning"), max_length=5000, null=True, blank=True, default="", help_text=_("Specific learning about the activity reported."))

    # ==================================================================================================================
    # OPERATION
    # ==================================================================================================================
    metrics_related = models.ManyToManyField(Metric, related_name="metrics_related", blank=False, verbose_name=_("Metrics related"), help_text=_("Metrics guiding the activity reported."))

    # ==================================================================================================================
    # FINANCIAL
    # ==================================================================================================================
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
            self.reference_text = build_wiki_ref(self.links, self.pk)

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

    class Meta:
        verbose_name = _("Operation Report")
        verbose_name_plural = _("Operation Reports")

    def __str__(self):
        return self.report.description + " - " + self.metric.text