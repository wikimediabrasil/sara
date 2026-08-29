import pandas as pd
from io import BytesIO
from django.db.models import Q
from django.utils.translation import gettext as _

from metrics.models import Metric
from report.models import Funding, OperationReport, Report
from report.utils import _get_localized_field, _joined_ids_and_count, _joined_ids

CREATED_AT = _("Created at")
MODIFIED_AT = _("Modified at")


def add_csv_file(function_name, report_id=None, custom_query=None):
    csv_file = BytesIO()
    function_name(report_id, custom_query).to_csv(path_or_buf=csv_file, index=False)

    return csv_file


def add_excel_file(report_id=None, custom_query=None, lang=""):
    excel_file = BytesIO()
    writer = pd.ExcelWriter(excel_file, engine="xlsxwriter")

    export_report_instance(report_id, custom_query).to_excel(
        writer, sheet_name="Report", index=False
    )
    export_operation_report(report_id, custom_query, lang).to_excel(
        writer, sheet_name="Operation report", index=False
    )
    export_metrics(report_id, custom_query).to_excel(
        writer, sheet_name="Metrics", index=False
    )
    export_user_profile(report_id, custom_query).to_excel(
        writer, sheet_name="Users", index=False
    )
    export_area_activated(report_id, custom_query).to_excel(
        writer, sheet_name="Areas", index=False
    )
    export_directions_related(report_id, custom_query).to_excel(
        writer, sheet_name="Directions", index=False
    )
    export_editors(report_id, custom_query).to_excel(
        writer, sheet_name="Editors", index=False
    )
    export_funding(report_id, custom_query).to_excel(
        writer, sheet_name="Fundings", index=False
    )
    export_learning_questions_related(report_id, custom_query).to_excel(
        writer, sheet_name="Learning questions", index=False
    )
    export_organizers(report_id, custom_query).to_excel(
        writer, sheet_name="Organizers", index=False
    )
    export_partners_activated(report_id, custom_query).to_excel(
        writer, sheet_name="Partners", index=False
    )
    export_technologies_used(report_id, custom_query).to_excel(
        writer, sheet_name="Technologies", index=False
    )

    writer.close()
    return excel_file


def export_report_instance(report_id=None, custom_query=Q()):
    header = [
        _("ID"),
        _("Created by"),
        CREATED_AT,
        _("Modified by"),
        MODIFIED_AT,
        _("Activity associated"),
        _("Partial report?"),
        _("Name of the activity"),
        _("Reference Text"),
        _("Area responsible"),
        _("Area activated"),
        _("Initial date"),
        _("End date"),
        _("Description"),
        _("Funding associated"),
        _("Links"),
        _("Are there private links?"),
        _("Number of participants"),
        _("Number of feedbacks"),
        _("Editors"),
        _("# Editors"),
        _("Organizers"),
        _("# Organizers"),
        _("Partnerships activated"),
        _("# Partnerships activated"),
        _("Technologies used"),
        _("# Donors"),
        _("# Submissions"),
        _("# Wikipedia created"),
        _("# Wikipedia edited"),
        _("# Commons created"),
        _("# Commons edited"),
        _("# Wikidata created"),
        _("# Wikidata edited"),
        _("# Wikiversity created"),
        _("# Wikiversity edited"),
        _("# Wikibooks created"),
        _("# Wikibooks edited"),
        _("# Wikisource created"),
        _("# Wikisource edited"),
        _("# Wikinews created"),
        _("# Wikinews edited"),
        _("# Wikiquote created"),
        _("# Wikiquote edited"),
        _("# Wiktionary created"),
        _("# Wiktionary edited"),
        _("# Wikivoyage created"),
        _("# Wikivoyage edited"),
        _("# Wikispecies created"),
        _("# Wikispecies edited"),
        _("# Metawiki created"),
        _("# Metawiki edited"),
        _("# MediaWiki created"),
        _("# MediaWiki edited"),
        _("# Wikifunctions created"),
        _("# Wikifunctions edited"),
        _("# Incubator created"),
        _("# Incubator edited"),
        _("Directions related"),
        _("Learning"),
        _("Learning questions related"),
        _("Metrics related"),
    ]

    if report_id:
        reports = Report.objects.filter(pk=report_id)
    else:
        reports = Report.objects.filter(custom_query)

    reports = reports.select_related(
        "created_by", "modified_by", "activity_associated", "area_responsible"
    ).prefetch_related(
        "area_activated",
        "funding_associated",
        "editors",
        "organizers",
        "partners_activated",
        "technologies_used",
        "directions_related",
        "learning_questions_related",
        "metrics_related",
    )

    wiki_fields = [
        "wikipedia",
        "commons",
        "wikidata",
        "wikiversity",
        "wikibooks",
        "wikisource",
        "wikinews",
        "wikiquote",
        "wiktionary",
        "wikivoyage",
        "wikispecies",
        "metawiki",
        "mediawiki",
        "wikifunctions",
        "incubator",
    ]

    rows = []
    for report in reports:
        editors, num_editors = _joined_ids_and_count(report.editors)
        organizers, num_organizers = _joined_ids_and_count(report.organizers)
        partners_activated, num_partners_activated = _joined_ids_and_count(
            report.partners_activated
        )

        wiki_values = []
        for wiki in wiki_fields:
            wiki_values.append(getattr(report, f"{wiki}_created"))
            wiki_values.append(getattr(report, f"{wiki}_edited"))

        rows.append(
            [
                report.id,
                report.created_by.id,
                report.created_at,
                report.modified_by.id,
                report.modified_at,
                report.activity_associated.id,
                report.partial_report,
                report.activity_associated.text or "",
                report.reference_text,
                report.area_responsible.id,
                _joined_ids(report.area_activated),
                report.initial_date,
                report.end_date,
                report.description,
                _joined_ids(report.funding_associated),
                report.links.replace("\r\n", "; "),
                report.private_links,
                report.participants,
                report.feedbacks,
                editors,
                num_editors,
                organizers,
                num_organizers,
                partners_activated,
                num_partners_activated,
                _joined_ids(report.technologies_used),
                report.donors,
                report.submissions,
                *wiki_values,
                _joined_ids(report.directions_related),
                report.learning.replace("\r\n", "\n"),
                _joined_ids(report.learning_questions_related),
                _joined_ids(report.metrics_related),
            ]
        )

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    df[CREATED_AT] = df[CREATED_AT].dt.tz_localize(None)
    df[MODIFIED_AT] = df[MODIFIED_AT].dt.tz_localize(None)
    return df


def export_operation_report(report_id=None, custom_query=Q(), lang=""):
    header = [
        _("ID"),
        _("Report ID"),
        _("Metric ID"),
        _("Metric"),
        _("Number of people reached through social media"),
        _("Number of new followers"),
        _("Number of mentions"),
        _("Number of community communications"),
        _("Number of events"),
        _("Number of resources"),
        _("Number of partnerships activated"),
        _("Number of new partnerships"),
    ]

    if report_id:
        operation_reports = OperationReport.objects.filter(report_id=report_id)
    else:
        reports = Report.objects.filter(custom_query)
        operation_reports = OperationReport.objects.filter(
            report_id__in=reports.values_list("id", flat=True)
        )

    available_fields = [
        f.name for f in Metric._meta.get_fields() if f.name.startswith("text")
    ]
    metric_name_attr = _get_localized_field(lang, available_fields)

    rows = []
    for operation_report in operation_reports:
        rows.append(
            [
                operation_report.id,
                operation_report.report_id,
                operation_report.metric_id,
                getattr(operation_report.metric, metric_name_attr),
                operation_report.number_of_people_reached_through_social_media,
                operation_report.number_of_new_followers,
                operation_report.number_of_mentions,
                operation_report.number_of_community_communications,
                operation_report.number_of_events,
                operation_report.number_of_resources,
                operation_report.number_of_partnerships_activated,
                operation_report.number_of_new_partnerships,
            ]
        )

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_metrics(report_id=None, custom_query=Q()):
    header = [
        _("ID"),
        _("Metric"),
        _("Activity ID"),
        _("Activity"),
        _("Activity code"),
        _("Number of editors"),
        _("Number of participants"),
        _("Number of partnerships activated"),
        _("Number of feedbacks"),
        _("Number of events"),
        _("# Wikipedia created"),
        _("# Wikipedia edited"),
        _("# Commons created"),
        _("# Commons edited"),
        _("# Wikidata created"),
        _("# Wikidata edited"),
        _("# Wikiversity created"),
        _("# Wikiversity edited"),
        _("# Wikibooks created"),
        _("# Wikibooks edited"),
        _("# Wikisource created"),
        _("# Wikisource edited"),
        _("# Wikinews created"),
        _("# Wikinews edited"),
        _("# Wikiquote created"),
        _("# Wikiquote edited"),
        _("# Wiktionary created"),
        _("# Wiktionary edited"),
        _("# Wikivoyage created"),
        _("# Wikivoyage edited"),
        _("# Wikispecies created"),
        _("# Wikispecies edited"),
        _("# Metawiki created"),
        _("# Metawiki edited"),
        _("# MediaWiki created"),
        _("# MediaWiki edited"),
        _("# Wikifunctions created"),
        _("# Wikifunctions edited"),
        _("# Incubator created"),
        _("# Incubator edited"),
    ]

    if report_id:
        reports = Report.objects.filter(pk=report_id).prefetch_related(
            "metrics_related"
        )
    else:
        reports = Report.objects.filter(custom_query).prefetch_related(
            "metrics_related"
        )

    rows = []
    for report in reports:
        if report.activity_associated:
            for instance in report.activity_associated.metrics.all():
                rows.append(
                    [
                        instance.id,
                        instance.text,
                        instance.activity_id,
                        instance.activity.text,
                        instance.activity.code,
                        instance.number_of_editors,
                        instance.number_of_participants,
                        instance.number_of_partnerships_activated,
                        instance.number_of_feedbacks,
                        instance.number_of_events,
                        instance.wikipedia_created,
                        instance.wikipedia_edited,
                        instance.commons_created,
                        instance.commons_edited,
                        instance.wikidata_created,
                        instance.wikidata_edited,
                        instance.wikiversity_created,
                        instance.wikiversity_edited,
                        instance.wikibooks_created,
                        instance.wikibooks_edited,
                        instance.wikisource_created,
                        instance.wikisource_edited,
                        instance.wikinews_created,
                        instance.wikinews_edited,
                        instance.wikiquote_created,
                        instance.wikiquote_edited,
                        instance.wiktionary_created,
                        instance.wiktionary_edited,
                        instance.wikivoyage_created,
                        instance.wikivoyage_edited,
                        instance.wikispecies_created,
                        instance.wikispecies_edited,
                        instance.metawiki_created,
                        instance.metawiki_edited,
                        instance.mediawiki_created,
                        instance.mediawiki_edited,
                        instance.wikifunctions_created,
                        instance.wikifunctions_edited,
                        instance.incubator_created,
                        instance.incubator_edited,
                    ]
                )

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_user_profile(report_id=None, custom_query=Q()):
    header = [
        _("ID"),
        _("First name"),
        _("Last Name"),
        _("Username on Wiki (WMB)"),
        _("Username on Wiki"),
        _("Photograph"),
        _("Position"),
        _("Twitter"),
        _("Facebook"),
        _("Instagram"),
        _("Email"),
        _("Wikidata item"),
        _("LinkedIn"),
        _("Lattes"),
        _("Orcid"),
        _("Google_scholar"),
    ]

    if report_id:
        reports = Report.objects.filter(pk=report_id)
    else:
        reports = Report.objects.filter(custom_query)

    reports = reports.select_related(
        "created_by__user__profile", "modified_by__user__profile"
    )

    rows = []
    for report in reports:
        for instance in [report.created_by, report.modified_by]:
            values = [
                instance.id,
                instance.user.first_name,
                instance.user.last_name,
                instance.professional_wiki_handle,
                instance.personal_wiki_handle,
                instance.photograph,
                instance.user.profile.current_position,
                instance.twitter,
                instance.facebook,
                instance.instagram,
                instance.user.email,
                instance.wikidata_item,
                instance.linkedin,
                instance.lattes,
                instance.orcid,
                instance.google_scholar,
            ]
            rows.append([v or "" for v in values])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_funding(report_id=None, custom_query=Q()):
    header = [
        _("ID"),
        _("Funding"),
        _("Value"),
        _("Project ID"),
        _("Project"),
        _("Active?"),
        _("Type of project"),
    ]

    if report_id:
        fundings = Funding.objects.filter(funding_associated=report_id).select_related(
            "project"
        )
    else:
        reports = Report.objects.filter(custom_query)
        fundings = Funding.objects.filter(
            funding_associated__in=reports.values_list("id", flat=True)
        ).select_related("project")

    rows = []
    for funding in fundings:
        type_of_funding = _("Ordinary")
        if funding.project.current_poa:
            type_of_funding = _("Current Plan of Activities")
        elif funding.project.main_funding:
            type_of_funding = _("Main funding")
        rows.append(
            [
                funding.id,
                funding.name,
                funding.value,
                funding.project_id,
                funding.project.text,
                funding.project.active_status,
                type_of_funding,
            ]
        )

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_area_activated(report_id=None, custom_query=Q()):
    header = [_("ID"), _("Area activated")]

    if report_id:
        reports = Report.objects.filter(pk=report_id).prefetch_related("area_activated")
    else:
        reports = Report.objects.filter(custom_query).prefetch_related("area_activated")

    rows = []
    for report in reports:
        rows.append([report.area_responsible.id, report.area_responsible.text])
        for instance in report.area_activated.all():
            rows.append([instance.id, instance.text])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_directions_related(report_id=None, custom_query=Q()):
    header = [
        _("ID"),
        _("Direction related"),
        _("Strategic axis ID"),
        _("Strategic axis text"),
    ]

    if report_id:
        reports = Report.objects.filter(pk=report_id).prefetch_related(
            "directions_related"
        )
    else:
        reports = Report.objects.filter(custom_query).prefetch_related(
            "directions_related"
        )

    rows = []
    for report in reports:
        for instance in report.directions_related.all():
            rows.append(
                [
                    instance.id,
                    instance.text,
                    instance.strategic_axis_id,
                    instance.strategic_axis.text,
                ]
            )

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_editors(report_id=None, custom_query=Q()):
    header = [_("ID"), _("Username"), _("Number of reports including this editor")]

    if report_id:
        reports = Report.objects.filter(pk=report_id).prefetch_related("editors")
    else:
        reports = Report.objects.filter(custom_query).prefetch_related("editors")

    rows = []
    for report in reports:
        for instance in report.editors.all():
            rows.append([instance.id, instance.username, instance.editors.count()])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_learning_questions_related(report_id=None, custom_query=Q()):
    header = [
        _("ID"),
        _("Learning question"),
        _("Learning area ID"),
        _("Learning area"),
    ]

    if report_id:
        reports = Report.objects.filter(pk=report_id).prefetch_related(
            "learning_questions_related"
        )
    else:
        reports = Report.objects.filter(custom_query).prefetch_related(
            "learning_questions_related"
        )

    rows = []
    for report in reports:
        for instance in report.learning_questions_related.all():
            rows.append(
                [
                    instance.id,
                    instance.text,
                    instance.learning_area_id,
                    instance.learning_area.text,
                ]
            )

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_organizers(report_id=None, custom_query=Q()):
    header = [
        _("ID"),
        _("Organizer's name"),
        _("Organizer's institution ID"),
        _("Organizer institution's name"),
        _("Number of reports including this organizer"),
    ]

    if report_id:
        reports = Report.objects.filter(pk=report_id).prefetch_related("organizers")
    else:
        reports = Report.objects.filter(custom_query).prefetch_related("organizers")

    rows = []
    for report in reports:
        for instance in report.organizers.all():
            rows.append(
                [
                    instance.id,
                    instance.name,
                    ";".join(
                        map(str, instance.institution.values_list("id", flat=True))
                    ),
                    ";".join(
                        map(str, instance.institution.values_list("name", flat=True))
                    ),
                    instance.organizers.count(),
                ]
            )

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_partners_activated(report_id=None, custom_query=Q()):
    header = [
        _("ID"),
        _("Partners"),
        _("Partner's website"),
        _("Number of reports including this partner"),
    ]

    if report_id:
        reports = Report.objects.filter(pk=report_id).prefetch_related(
            "partners_activated"
        )
    else:
        reports = Report.objects.filter(custom_query).prefetch_related(
            "partners_activated"
        )

    rows = []
    for report in reports:
        for instance in report.partners_activated.all():
            rows.append(
                [
                    instance.id,
                    instance.name,
                    instance.website,
                    instance.partners.count(),
                ]
            )

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_technologies_used(report_id=None, custom_query=Q()):
    header = [
        _("ID"),
        _("Technology"),
        _("Number of reports including this technology"),
    ]

    if report_id:
        reports = Report.objects.filter(pk=report_id).prefetch_related(
            "technologies_used"
        )
    else:
        reports = Report.objects.filter(custom_query).prefetch_related(
            "technologies_used"
        )

    rows = []
    for report in reports:
        for instance in report.technologies_used.all():
            rows.append([instance.id, instance.name, instance.technologies.count()])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df
