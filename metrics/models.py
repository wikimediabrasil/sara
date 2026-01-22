from django.db import models
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from users.models import UserProfile, TeamArea


class Project(models.Model):
    """
    Represents a project in the system.

    Fields:
        text (CharField): Title of the project. Must be unique.
        active_status (BooleanField): Whether the project is currently active. Default: True.
        current_poa (BooleanField): Marks if this project is the current Plan of Activities. Default: False.
        main_funding (BooleanField): Indicates if this is the main funding project. Default: False.
        counts_for_main_funding (BooleanField): If metrics from this project contribute to main funding metrics. Default: False.

    Methods:
        __str__(): Returns the project title.
        clean(): Validates that `text` is not empty.
    """
    text = models.CharField(_("Project"), max_length=210, unique=True, help_text=_("Project title"))
    active_status = models.BooleanField(_("Active?"), default=True, help_text=_("Is the project active?"))
    current_poa = models.BooleanField(_("Current Plan of Activities"), default=False, help_text=_("Is this the current plan of activities?"))
    main_funding = models.BooleanField(_("Current Main Funding project?"), default=False, help_text=_("Is this the main funding project?"))
    counts_for_main_funding = models.BooleanField(_("Counts towards Main Funding project's metrics?"), default=False, help_text=_("Does this counts towards Main Funding project metrics?"))

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


class Area(models.Model):
    """
    Represents an area or category within a project. For example: Wiki Loves Minas Gerais

    Fields:
        text (CharField): Title of the area.
        project (ManyToManyField): Projects associated with this area.
        poa_area (BooleanField): Whether this area is part of the Plan of Activities. Default: False.

    Methods:
        __str__(): Returns the area title.
        clean(): Validates that `text` is not empty.
    """
    text = models.CharField(_("Title"), max_length=420, help_text=_("Area title"))
    project = models.ManyToManyField(Project, related_name="project_activity", blank=True, verbose_name=_("Project"))
    poa_area = models.BooleanField(_("Part of the Plan of Activities?"), default=False, help_text=_("Is this area part of the Plan of Activities?"))

    class Meta:
        verbose_name = _("Area")
        verbose_name_plural = _("Areas")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


class Activity(models.Model):
    """
    Represents an individual activity within an area.

    Fields:
        text (CharField): Title of the activity.
        code (CharField): Optional code for the activity (max length 20).
        area (ForeignKey): The area this activity belongs to.
        is_main_activity (BooleanField): Marks if this is a main activity. Default: False.
        area_responsible (ForeignKey): TeamArea responsible for this activity. Optional.

    Methods:
        __str__(): Returns the activity title.
        clean(): Validates that `text` is not empty.
    """
    text = models.CharField(_("Title"), max_length=420, help_text=_("Activity title"))
    code = models.CharField(_("Code"), max_length=20, null=True, blank=True, help_text=_("Activity code"))
    area = models.ForeignKey(Area, on_delete=models.RESTRICT, related_name='activities', null=True, verbose_name=_("Area"))
    is_main_activity = models.BooleanField(_("Is main activity?"), default=False, help_text=_("Is this the main activity?"))
    area_responsible = models.ForeignKey(TeamArea, on_delete=models.RESTRICT, related_name='activity_manager', null=True, blank=True, verbose_name=_("Area responsible"))

    class Meta:
        verbose_name = _("Activity")
        verbose_name_plural = _("Activities")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))


class Metric(models.Model):
    """
    Represents metrics associated with an activity and optionally linked to projects.
    Metrics are divided into content, community, communication, financial, and other types.

    Fields:

    Identification:
        text (CharField): Title of the metric.
        activity (ForeignKey → Activity): Activity associated with the metric.
        project (ManyToManyField → Project): Projects associated with the metric. Optional.

    Content Metrics:
        wikipedia_created, wikipedia_edited, commons_created, commons_edited,
        wikidata_created, wikidata_edited, wikiversity_created, wikiversity_edited,
        wikibooks_created, wikibooks_edited, wikisource_created, wikisource_edited,
        wikinews_created, wikinews_edited, wikiquote_created, wikiquote_edited,
        wiktionary_created, wiktionary_edited, wikivoyage_created, wikivoyage_edited,
        wikispecies_created, wikispecies_edited, metawiki_created, metawiki_edited,
        mediawiki_created, mediawiki_edited (IntegerField): Number of items edited on each platform.

    Community Metrics:
        number_of_editors, number_of_editors_retained, number_of_new_editors (IntegerField)
        number_of_organizers, number_of_organizers_retained, number_of_new_organizers (IntegerField)
        number_of_participants, number_of_feedbacks (IntegerField)
        number_of_partnerships_activated, number_of_new_partnerships (IntegerField)

    Communication Metrics:
        number_of_new_followers, number_of_mentions, number_of_community_communications,
        number_of_people_reached_through_social_media (IntegerField)

    Financial Metrics:
        number_of_donors, number_of_submissions (IntegerField)

    Other Metrics:
        number_of_resources, number_of_events (IntegerField)
        boolean_type (BooleanField)
        other_type (CharField, optional)
        observation (CharField, optional)
        is_operation (BooleanField): Whether this metric corresponds to an operational metric.

    Methods:
        __str__(): Returns the metric title.
        clean(): Validates that `text` is not empty.
    """
    # ==================================================================================================================
    # IDENTIFICATION
    # ==================================================================================================================
    text = models.CharField(_("Title"), max_length=420, help_text=_("Metric title"))
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="metrics", verbose_name=_("Activity"))
    project = models.ManyToManyField(Project, related_name="project_associated", blank=True, verbose_name=_("Project"))

    # ==================================================================================================================
    # CONTENT METRICS
    # ==================================================================================================================
    wikipedia_created     = models.IntegerField(_("Created in Wikipedia"), null=True, default=0, help_text=_("Number of articles created on Wikipedia."))
    wikipedia_edited      = models.IntegerField(_("Edited in Wikipedia"), null=True, default=0, help_text=_("Number of articles edited on Wikipedia."))
    commons_created       = models.IntegerField(_("Created in Wikimedia Commons"), null=True, default=0, help_text=_("Number of medias created on Wikimedia Commons."))
    commons_edited        = models.IntegerField(_("Edited in Wikimedia Commons"), null=True, default=0, help_text=_("Number of medias edited on Wikimedia Commons."))
    wikidata_created      = models.IntegerField(_("Created in Wikidata"), null=True, default=0, help_text=_("Number of items created on Wikidata."))
    wikidata_edited       = models.IntegerField(_("Edited in Wikidata"), null=True, default=0, help_text=_("Number of items edited on Wikidata."))
    wikiversity_created   = models.IntegerField(_("Created in Wikiversity"), null=True, default=0, help_text=_("Number of pages or materials created on Wikiversity."))
    wikiversity_edited    = models.IntegerField(_("Edited in Wikiversity"), null=True, default=0, help_text=_("Number of pages or materials edited on Wikiversity."))
    wikibooks_created     = models.IntegerField(_("Created in Wikibooks"), null=True, default=0, help_text=_("Number of pages or materials created on Wikibooks."))
    wikibooks_edited      = models.IntegerField(_("Edited in Wikibooks"), null=True, default=0, help_text=_("Number of pages or materials edited on Wikibooks."))
    wikisource_created    = models.IntegerField(_("Created in Wikisource"), null=True, default=0, help_text=_("Number of pages or materials created on Wikisource."))
    wikisource_edited     = models.IntegerField(_("Edited in Wikisource"), null=True, default=0, help_text=_("Number of pages or materials edited on Wikisource."))
    wikinews_created      = models.IntegerField(_("Created in Wikinews"), null=True, default=0, help_text=_("Number of pages or materials created on Wikinews."))
    wikinews_edited       = models.IntegerField(_("Edited in Wikinews"), null=True, default=0, help_text=_("Number of pages or materials edited on Wikinews."))
    wikiquote_created     = models.IntegerField(_("Created in Wikiquote"), null=True, default=0, help_text=_("Number of pages or materials created on Wikiquote."))
    wikiquote_edited      = models.IntegerField(_("Edited in Wikiquote"), null=True, default=0, help_text=_("Number of pages or materials edited on Wikiquote."))
    wiktionary_created    = models.IntegerField(_("Created in Wiktionary"), null=True, default=0, help_text=_("Number of pages or materials created on Wiktionary."))
    wiktionary_edited     = models.IntegerField(_("Edited in Wiktionary"), null=True, default=0, help_text=_("Number of pages or materials edited on Wiktionary."))
    wikivoyage_created    = models.IntegerField(_("Created in Wikivoyage"), null=True, default=0, help_text=_("Number of pages or materials created on Wikivoyage."))
    wikivoyage_edited     = models.IntegerField(_("Edited in Wikivoyage"), null=True, default=0, help_text=_("Number of pages or materials edited on Wikivoyage."))
    wikispecies_created   = models.IntegerField(_("Created in Wikispecies"), null=True, default=0, help_text=_("Number of pages or materials created on Wikispecies."))
    wikispecies_edited    = models.IntegerField(_("Edited in Wikispecies"), null=True, default=0, help_text=_("Number of pages or materials edited on Wikispecies."))
    metawiki_created      = models.IntegerField(_("Created in Meta-Wiki"), null=True, default=0, help_text=_("Number of pages or materials created on Meta-Wiki."))
    metawiki_edited       = models.IntegerField(_("Edited in Meta-Wiki"), null=True, default=0, help_text=_("Number of pages or materials edited on Meta-Wiki."))
    mediawiki_created     = models.IntegerField(_("Created in Mediawiki"), null=True, default=0, help_text=_("Number of pages or materials created on Mediawiki."))
    mediawiki_edited      = models.IntegerField(_("Edited in Mediawiki"), null=True, default=0, help_text=_("Number of pages or materials edited on Mediawiki."))
    incubator_created     = models.IntegerField(_("Created in Wikimedia Incubator"), null=True, default=0, help_text=_("Number of pages or materials created on Wikimedia Incubator."))
    incubator_edited      = models.IntegerField(_("Edited in Wikimedia Incubator"), null=True, default=0, help_text=_("Number of pages or materials edited on Wikimedia Incubator."))
    wikifunctions_created = models.IntegerField(_("Created in Wikifunctions"), null=True, default=0, help_text=_("Number of pages or materials created on Wikifunctions."))
    wikifunctions_edited  = models.IntegerField(_("Edited in Wikifunctions"), null=True, default=0, help_text=_("Number of pages or materials edited on Wikifunctions."))

    # ==================================================================================================================
    # COMMUNITY METRICS
    # ==================================================================================================================
    # Editors
    number_of_editors = models.IntegerField(_("Number of editors"), null=True, default=0, help_text=_("Number of editors"))
    number_of_editors_retained = models.IntegerField(_("Number of editors retained"), null=True, default=0, help_text=_("Number of editors participating in more activities"))
    number_of_new_editors = models.IntegerField(_("Number of new editors"), null=True, default=0, help_text=_("Number of editors recently registered"))

    # Organizers
    number_of_organizers = models.IntegerField(_("Number of organizers"), null=True, default=0, help_text=_("Number of organizers"))
    number_of_organizers_retained = models.IntegerField(_("Number of organizers retained"), null=True, default=0, help_text=_("Number of organizers participating in more activities"))
    number_of_new_organizers = models.IntegerField(_("Number of new organizers"), null=True, default=0, help_text=_("Number of organizers recently registered"))

    # Participants
    number_of_participants = models.IntegerField(_("Number of participants"), null=True, default=0, help_text=_("Number of participants"))
    number_of_feedbacks = models.IntegerField(_("Number of feedbacks"), null=True, default=0, help_text=_("Number of feedbacks"))

    # Partnerships
    number_of_partnerships_activated = models.IntegerField(_("Number of partnerships activated"), null=True, default=0, help_text=_("Number of partnerships activated"))
    number_of_new_partnerships = models.IntegerField(_("Number of new partnerships"), null=True, default=0, help_text=_("Number of new partnerships"))

    # ==================================================================================================================
    # COMMUNICATION METRICS
    # ==================================================================================================================
    number_of_new_followers = models.IntegerField(_("Number of new followers"), null=True, default=0, help_text=_("Number of new followers in social media"))
    number_of_mentions = models.IntegerField(_("Number of mentions"), null=True, default=0, help_text=_("Media clipping"))
    number_of_community_communications = models.IntegerField(_("Number of community communications"), null=True, default=0, help_text=_("Number of communications and newsletters"))
    number_of_people_reached_through_social_media = models.IntegerField(_("Number of people reached through social media"), null=True, default=0, help_text=_("Number of people reached through social media"))

    # ==================================================================================================================
    # FINANCIAL METRICS
    # ==================================================================================================================
    number_of_donors = models.IntegerField(_("Number of donors"), null=True, default=0, help_text=_("Number of donors"))
    number_of_submissions = models.IntegerField(_("Number of submissions"), null=True, default=0, help_text=_("Number of grants submissions"))

    # ==================================================================================================================
    # OTHER METRICS
    # ==================================================================================================================
    number_of_resources = models.IntegerField(_("Number of resources"), null=True, default=0, help_text=_("Number of resources produced"))
    number_of_events = models.IntegerField(_("Number of events"), null=True, default=0, help_text=_("Number of activities"))
    boolean_type = models.BooleanField(_("Boolean type?"), default=False, help_text=_("Boolean type metric"))
    is_operation = models.BooleanField(_("Operation?"), default=False, help_text=_("Is the metric an operation metric?"))

    class Meta:
        verbose_name = _("Metric")
        verbose_name_plural = _("Metrics")

    def __str__(self):
        return self.text

    def clean(self):
        if not self.text:
            raise ValidationError(_("You need to fill the text field"))
