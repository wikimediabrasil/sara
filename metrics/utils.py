import datetime
import re
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.conf import settings
from django.db.models import F, Q, Sum
from django.shortcuts import HttpResponse

from metrics.link_utils import wikify_link
from metrics.models import Activity, Metric
from report.models import Editor, OperationReport, Organizer, Partner, Project, Report


# ======================================================================================================================
# VARIABLES
# ======================================================================================================================
PATTERNS = {
    r"https://(.*).(toolforge).org/(.*)": "toolforge:",
    r"https://(.*).wikibooks.org/wiki/(.*)": "b:",
    r"https://(.*).wikinews.org/wiki/(.*)": "n:",
    r"https://(.*).wikipedia.org/wiki/(.*)": "w:",
    r"https://(.*).wikiquote.org/wiki/(.*)": "q:",
    r"https://(.*).wikisource.org/wiki/(.*)": "s:",
    r"https://(.*).wikiversity.org/wiki/(.*)": "v:",
    r"https://(.*).wikivoyage.org/wiki/(.*)": "voy:",
    r"https://(.*).wiktionary.org/wiki/(.*)": "wikt:",
    r"https://commons.wikimedia.org/wiki/(.*)": "c",
    r"https://outreach.wikimedia.org/wiki/(.*)": "outreach",
    r"https://species.wikimedia.org/wiki/(.*)": "species",
    r"https://wikitech.wikimedia.org/wiki/(.*)": "wikitech",
    r"https://www.mediawiki.org/wiki/(.*)": "mw",
    r"https://www.wikidata.org/wiki/(.*)": "d",
    r"https://br.wikimedia.org/wiki/(.*)": "wmbr",
    r"https://meta.wikimedia.org/wiki/(.*)": "",
    r"https://phabricator.wikimedia.org/(.*)": "phab",
}

EDITORS = "Number of editors"
EDITORS_RETAINED = "Number of editors retained"
EDITORS_NEW = "Number of new editors"
ORGANIZERS = "Number of organizers"
ORGANIZERS_RETAINED = "Number of organizers retained"
ORGANIZERS_NEW = "Number of new organizers"
PARTNERSHIPS_ACTIVATED = "Number of partnerships activated"


# ======================================================================================================================
# FUNCTIONS
# ======================================================================================================================
def get_results_divided_by_timespan(buffer, area=None, with_goal=False, timeframe="semester"):
    timespan_array = _get_timespan_array(timeframe)

    if area:
        report_query = Q(area_responsible=area)
        header = (
            "==" + area.text + "==\n"
            "<div class='wmb_report_table_container bd-" + area.code + "'>\n"
            "{| class='wikitable wmb_report_table'\n"
            "! colspan='8' class='bg-"
            + area.code
            + " co-"
            + area.code
            + "' | <h5 id='Metrics'>Operational and General metrics</h5>\n|-\n"
        )
        footer = "|}\n</div>\n"
    else:
        report_query = Q(area_responsible__project__main_funding=True)
        header = "{| class='wikitable wmb_report_table'\n"
        footer = "|}\n"

    poa_results = get_results_for_timespan(
        timespan_array,
        Q(project=Project.objects.get(current_poa=True), is_operation=True),
        report_query,
        with_goal,
        "en",
        True,
    )
    main_results = get_results_for_timespan(
        timespan_array,
        Q(project=Project.objects.get(main_funding=True)),
        report_query,
        with_goal,
        "en",
        True,
    )

    poa_wikitext = _construct_wikitext(
        poa_results, header + _get_header_columns(timeframe)
    )

    main_wikitext = _construct_wikitext(main_results, "")

    poa_wikitext = _shorten_duplicate_refs(poa_wikitext)
    main_wikitext = _shorten_duplicate_refs(main_wikitext)

    buffer.write(poa_wikitext)
    buffer.write(main_wikitext)
    buffer.write(footer)


def get_results_for_timespan(timespan_array, metric_query=Q(), report_query=Q(), with_goal=False, lang="pt", is_main_funding=False):
    results = []
    for metric in Metric.objects.filter(metric_query).select_related("activity").order_by("activity_id", "id"):
        done_row, goal_value, supplementary_query = _compute_done_row(metric, timespan_array, report_query, is_main_funding)
        done_row.append(_refs_summary(metric, supplementary_query))

        # Get goal and attach to the array
        if with_goal:
            done_row.append(goal_value if goal_value else "?")

        results.append(
            {
                "activity": metric.activity.text,
                "metric": metric.text if lang == "pt" else metric.text_en,
                "done": done_row,
            }
        )
    return results


def get_done_for_report(reports, metric):
    operation_reports = OperationReport.objects.filter(report__in=reports, metric=metric)
    alternative_operation_reports = OperationReport.objects.filter(report__in=reports)

    reports_aggregations = reports.aggregate(
        wikipedia_created=Sum("wikipedia_created"), wikipedia_edited=Sum("wikipedia_edited"),
        commons_created=Sum("commons_created"), commons_edited=Sum("commons_edited"),
        wikidata_created=Sum("wikidata_created"), wikidata_edited=Sum("wikidata_edited"),
        wikiversity_created=Sum("wikiversity_created"), wikiversity_edited=Sum("wikiversity_edited"),
        wikibooks_created=Sum("wikibooks_created"), wikibooks_edited=Sum("wikibooks_edited"),
        wikisource_created=Sum("wikisource_created"), wikisource_edited=Sum("wikisource_edited"),
        wikinews_created=Sum("wikinews_created"), wikinews_edited=Sum("wikinews_edited"),
        wikiquote_created=Sum("wikiquote_created"), wikiquote_edited=Sum("wikiquote_edited"),
        wiktionary_created=Sum("wiktionary_created"), wiktionary_edited=Sum("wiktionary_edited"),
        wikivoyage_created=Sum("wikivoyage_created"), wikivoyage_edited=Sum("wikivoyage_edited"),
        wikispecies_created=Sum("wikispecies_created"), wikispecies_edited=Sum("wikispecies_edited"),
        metawiki_created=Sum("metawiki_created"), metawiki_edited=Sum("metawiki_edited"),
        mediawiki_created=Sum("mediawiki_created"), mediawiki_edited=Sum("mediawiki_edited"),
        wikifunctions_created=Sum("wikifunctions_created"), wikifunctions_edited=Sum("wikifunctions_edited"),
        incubator_created=Sum("incubator_created"), incubator_edited=Sum("incubator_edited"),
        participants=Sum("participants"),
        feedbacks=Sum("feedbacks"),
        donors=Sum("donors"),
        submissions=Sum("submissions"),
    )

    operation_aggregations = operation_reports.aggregate(
        new_partnerships=Sum("number_of_new_partnerships"),
        resources=Sum("number_of_resources"),
        events=Sum("number_of_events"),
        new_followers=Sum("number_of_new_followers"),
        mentions=Sum("number_of_mentions"),
        communications=Sum("number_of_community_communications"),
        people_reached=Sum("number_of_people_reached_through_social_media"),
    )

    alternative_operation_aggregations = alternative_operation_reports.aggregate(
        new_partnerships=Sum("number_of_new_partnerships"),
        resources=Sum("number_of_resources"),
        events=Sum("number_of_events"),
        new_followers=Sum("number_of_new_followers"),
        mentions=Sum("number_of_mentions"),
        communications=Sum("number_of_community_communications"),
        people_reached=Sum("number_of_people_reached_through_social_media"),
    )

    editor_qs = Editor.objects.filter(editors__in=reports).distinct()
    organizer_qs = Organizer.objects.filter(organizers__in=reports).distinct()

    return {
        # Content metrics
        "Wikipedia (created)": _value_or_zero(reports_aggregations["wikipedia_created"]),
        "Wikipedia (edited)": _value_or_zero(reports_aggregations["wikipedia_edited"]),
        "Wikimedia Commons (created)": _value_or_zero(reports_aggregations["commons_created"]),
        "Wikimedia Commons (edited)": _value_or_zero(reports_aggregations["commons_edited"]),
        "Wikidata (created)": _value_or_zero(reports_aggregations["wikidata_created"]),
        "Wikidata (edited)": _value_or_zero(reports_aggregations["wikidata_edited"]),
        "Wikiversity (created)": _value_or_zero(reports_aggregations["wikiversity_created"]),
        "Wikiversity (edited)": _value_or_zero(reports_aggregations["wikiversity_edited"]),
        "Wikibooks (created)": _value_or_zero(reports_aggregations["wikibooks_created"]),
        "Wikibooks (edited)": _value_or_zero(reports_aggregations["wikibooks_edited"]),
        "Wikisource (created)": _value_or_zero(reports_aggregations["wikisource_created"]),
        "Wikisource (edited)": _value_or_zero(reports_aggregations["wikisource_edited"]),
        "Wikinews (created)": _value_or_zero(reports_aggregations["wikinews_created"]),
        "Wikinews (edited)": _value_or_zero(reports_aggregations["wikinews_edited"]),
        "Wikiquote (created)": _value_or_zero(reports_aggregations["wikiquote_created"]),
        "Wikiquote (edited)": _value_or_zero(reports_aggregations["wikiquote_edited"]),
        "Wiktionary (created)": _value_or_zero(reports_aggregations["wiktionary_created"]),
        "Wiktionary (edited)": _value_or_zero(reports_aggregations["wiktionary_edited"]),
        "Wikivoyage (created)": _value_or_zero(reports_aggregations["wikivoyage_created"]),
        "Wikivoyage (edited)": _value_or_zero(reports_aggregations["wikivoyage_edited"]),
        "Wikispecies (created)": _value_or_zero(reports_aggregations["wikispecies_created"]),
        "Wikispecies (edited)": _value_or_zero(reports_aggregations["wikispecies_edited"]),
        "MetaWiki (created)": _value_or_zero(reports_aggregations["metawiki_created"]),
        "MetaWiki (edited)": _value_or_zero(reports_aggregations["metawiki_edited"]),
        "MediaWiki (created)": _value_or_zero(reports_aggregations["mediawiki_created"]),
        "MediaWiki (edited)": _value_or_zero(reports_aggregations["mediawiki_edited"]),
        "Wikifunctions (created)": _value_or_zero(reports_aggregations["wikifunctions_created"]),
        "Wikifunctions (edited)": _value_or_zero(reports_aggregations["wikifunctions_edited"]),
        "Incubator (created)": _value_or_zero(reports_aggregations["incubator_created"]),
        "Incubator (edited)": _value_or_zero(reports_aggregations["incubator_edited"]),
        # Financial metrics
        "Number of donors": _value_or_zero(reports_aggregations["donors"]),
        "Number of submissions": _value_or_zero(reports_aggregations["submissions"]),
        # Community metrics
        "Number of participants": _value_or_zero(reports_aggregations["participants"]),
        "Number of feedbacks": _value_or_zero(reports_aggregations["feedbacks"]),
        EDITORS: editor_qs.count(),
        EDITORS_RETAINED: editor_qs.filter(retained=True).count(),
        EDITORS_NEW: Editor.objects.filter(
            editors__in=reports,
            account_creation_date__gte=F("editors__initial_date") - datetime.timedelta(days=30),
        ).distinct().count(),
        ORGANIZERS: organizer_qs.count(),
        ORGANIZERS_RETAINED: organizer_qs.filter(retained=True).count(),
        ORGANIZERS_NEW: Organizer.objects.filter(
            organizers__in=reports,
            first_seen_at__gte=F("organizers__initial_date")
        ).distinct().count(),
        PARTNERSHIPS_ACTIVATED: Partner.objects.filter(partners__in=reports).distinct().count(),
        "Number of new partnerships": _operation_metric(operation_aggregations, alternative_operation_aggregations, "new_partnerships"),
        "Number of resources": _operation_metric(operation_aggregations, alternative_operation_aggregations, "resources"),
        "Number of events": _operation_metric(operation_aggregations, alternative_operation_aggregations,"events"),
        # Communication metrics
        "Number of new followers": _operation_metric(operation_aggregations, alternative_operation_aggregations,"new_followers"),
        "Number of mentions": _operation_metric(operation_aggregations, alternative_operation_aggregations,"mentions"),
        "Number of community communications": _operation_metric(operation_aggregations, alternative_operation_aggregations,"communications"),
        "Number of people reached through social media": _operation_metric(operation_aggregations, alternative_operation_aggregations,"people_reached"),
        # Other metrics
        "Occurrence": reports.filter(metrics_related__boolean_type=True).exists(),
    }


def get_metrics_and_aggregate_per_project(project_query=Q(active_status=True), metric_query=Q(), supplementary_query=Q(), field=None, lang=""):
    """
    Build a nested dictionary of the results, and goal for each metric, for each activity of each project.
    It shows the progress of completion of each metric in relation to its set goal.
    """
    aggregated_metrics_and_results = {}

    for project in Project.objects.filter(project_query).order_by(
        "-current_poa", "-main_funding"
    ):
        project_metrics = []
        for activity in Activity.objects.filter(area__project=project):
            activity_metrics = {}
            q_filter = _q_filter_for_activity(project, activity, metric_query)
            for metric in Metric.objects.filter(q_filter):
                goal, done, final = _get_goal_and_done_for_metric(
                    metric,
                    supplementary_query,
                    project.main_funding or project.counts_for_main_funding
                )

                result_metrics = _result_metrics_for(goal, done, final, field)
                localized_title = _localized_metric_title(metric, lang)
                activity_metrics[metric.id] = {"title": localized_title, "metrics": result_metrics}

            if activity_metrics:
                project_metrics.append(
                    {
                        "activity": activity.text,
                        "activity_id": activity.id,
                        "activity_metrics": activity_metrics,
                    }
                )

        if project_metrics:
            aggregated_metrics_and_results[project.id] = {
                "project": project.text,
                "project_metrics": project_metrics,
                "current_poa": project.current_poa,
                "main_funding": project.main_funding,
            }
    return aggregated_metrics_and_results


def get_goal_for_metric(metric):
    return {
        # Content metrics
        "Wikipedia (created)": metric.wikipedia_created,
        "Wikipedia (edited)": metric.wikipedia_edited,
        "Wikimedia Commons (created)": metric.commons_created,
        "Wikimedia Commons (edited)": metric.commons_edited,
        "Wikidata (created)": metric.wikidata_created,
        "Wikidata (edited)": metric.wikidata_edited,
        "Wikiversity (created)": metric.wikiversity_created,
        "Wikiversity (edited)": metric.wikiversity_edited,
        "Wikibooks (created)": metric.wikibooks_created,
        "Wikibooks (edited)": metric.wikibooks_edited,
        "Wikisource (created)": metric.wikisource_created,
        "Wikisource (edited)": metric.wikisource_edited,
        "Wikinews (created)": metric.wikinews_created,
        "Wikinews (edited)": metric.wikinews_edited,
        "Wikiquote (created)": metric.wikiquote_created,
        "Wikiquote (edited)": metric.wikiquote_edited,
        "Wiktionary (created)": metric.wiktionary_created,
        "Wiktionary (edited)": metric.wiktionary_edited,
        "Wikivoyage (created)": metric.wikivoyage_created,
        "Wikivoyage (edited)": metric.wikivoyage_edited,
        "Wikispecies (created)": metric.wikispecies_created,
        "Wikispecies (edited)": metric.wikispecies_edited,
        "MetaWiki (created)": metric.metawiki_created,
        "MetaWiki (edited)": metric.metawiki_edited,
        "MediaWiki (created)": metric.mediawiki_created,
        "MediaWiki (edited)": metric.mediawiki_edited,
        "Wikifucntions (created)": metric.wikifunctions_created,
        "Wikifucntions (edited)": metric.wikifunctions_edited,
        "Incubator (created)": metric.incubator_created,
        "Incubator (edited)": metric.incubator_edited,
        # Community metrics
        "Number of participants": metric.number_of_participants,
        "Number of feedbacks": metric.number_of_feedbacks,
        EDITORS: metric.number_of_editors,
        EDITORS_RETAINED: metric.number_of_editors_retained,
        EDITORS_NEW: metric.number_of_new_editors,
        ORGANIZERS: metric.number_of_organizers,
        ORGANIZERS_RETAINED: metric.number_of_organizers_retained,
        ORGANIZERS_NEW: metric.number_of_new_organizers,
        PARTNERSHIPS_ACTIVATED: metric.number_of_partnerships_activated,
        "Number of new partnerships": metric.number_of_new_partnerships,
        "Number of resources": metric.number_of_resources,
        "Number of events": metric.number_of_events,
        # Financial metrics
        "Number of donors": metric.number_of_donors,
        "Number of submissions": metric.number_of_submissions,
        # Communication metrics
        "Number of new followers": metric.number_of_new_followers,
        "Number of mentions": metric.number_of_mentions,
        "Number of community communications": metric.number_of_community_communications,
        "Number of people reached through social media": metric.number_of_people_reached_through_social_media,
        "Occurrence": metric.boolean_type,
    }


def render_to_pdf(template_src, context_dict=None):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)
    if pdf.err:
        return HttpResponse("Invalid PDF", status=400, content_type="text/plain")
    return HttpResponse(result.getvalue(), content_type="application/pdf")


def _get_goal_and_done_for_metric(metric, supplementary_query=Q(), is_main_funding=False):
    query = Q(metrics_related__in=[metric]) & supplementary_query
    reports = Report.objects.filter(query)
    if is_main_funding:
        reports = reports.exclude(
            (
                Q(activity_associated__area__project__counts_for_main_funding=False)
                | Q(funding_associated__project__counts_for_main_funding=False)
            )
            & ~(
                Q(activity_associated__id=1)
                & Q(funding_associated__project__counts_for_main_funding=True)
            )
            & ~(Q(activity_associated__id=1) & Q(funding_associated__isnull=True))
        )
    goal = get_goal_for_metric(metric)
    done = get_done_for_report(reports, metric)
    final = _is_there_a_final_report(reports)

    return goal, done, final


def _get_timespan_array(timeframe):
    year = datetime.datetime.today().year

    config = settings.REPORT_TIMESPANS.get(timeframe)
    if not config:
        raise ValueError(f"Invalid timeframe: {timeframe}")

    spans = [
        (datetime.date(year, start[0], start[1]), datetime.date(year, end[0], end[1]))
        for start, end in config["periods"]
    ]
    total = config.get("total")
    if total:
        spans.append(
            (
                datetime.date(year, total[0][0], total[0][1]),
                datetime.date(year, total[1][0], total[1][1]),
            )
        )

    return spans


def _get_header_columns(timeframe):
    labels = settings.REPORT_TIMESPANS[timeframe]["labels"]
    columns = " !! ".join(labels)
    return f"!Activity !! Metrics !! {columns} !! Total !! References\n|-\n"


def _compute_done_row(metric, timespan_array, report_query, is_main_funding):
    """
    For the timespan for this metric, and for each goal key of non-zero metric
    record what was done (or "-").
    """
    done_row = []
    goal_value = 0
    supplementary_query = Q()

    for time_ini, time_end in timespan_array:
        supplementary_query = (
            Q(end_date__gte=time_ini) & Q(end_date__lte=time_end) & report_query
        )
        goal, done, _ = _get_goal_and_done_for_metric(
            metric,
            supplementary_query=supplementary_query,
            is_main_funding=is_main_funding,
        )
        for key, value in goal.items():
            if value != 0:
                done_row.append(done[key] if done[key] else "-")
                goal_value = value

    return done_row, goal_value, supplementary_query


def _refs_summary(metric, supplementary_query):
    """Build the deduplicated reference string"""
    refs = [_build_wiki_ref_for_reports(metric, supplementary_query=supplementary_query)]
    refs = list(dict.fromkeys(refs))
    return " ".join(filter(None, refs))


def _q_filter_for_activity(project, activity, metric_query):
    if activity.pk != 1:
        return Q(project=project, activity=activity) & metric_query
    return Q(project=project) & metric_query


def _result_metrics_for(goal, done, final, field):
    if field and goal[field] != 0:
        result_metrics = {
            field: {"goal": goal[field], "done": done[field], "final": final}
        }
    else:
        result_metrics = {
            key: {"goal": value, "done": done[key], "final": final} for key, value in goal.items() if value != 0
        }

    if not result_metrics:
        result_metrics = {"Other metrics": {"goal": "-", "done": "-", "final": final}}

    return result_metrics


def _localized_metric_title(metric, lang):
    return metric.text_en if lang == "en" else metric.text


def _value_or_zero(value):
    return value or 0


def _operation_metric(operation_aggregations, alternative_operation_aggregations, key):
    return operation_aggregations[key] or alternative_operation_aggregations[key] or 0


def _construct_wikitext(results, wikitext):
    activities = list(dict.fromkeys(row["activity"] for row in results))
    other_activity = Activity.objects.get(pk=1).text in activities
    for activity in activities:
        metrics = [row for row in results if row["activity"] == activity]
        rowspan = len(metrics)
        if not other_activity:
            header = (
                "| rowspan='{}' | {} |".format(rowspan, activity)
                if len(metrics) > 1
                else "| {} |".format(activity)
            )
        else:
            header = (
                "| rowspan='{}' | - |".format(rowspan) if len(metrics) > 1 else "| - |"
            )

        for metric in metrics:
            wikitext += header + "| {} || {}\n|-\n".format(
                metric["metric"], " || ".join(map(str, metric["done"]))
            )
            header = ""

    return wikitext


def _shorten_duplicate_refs(wikitext):
    ref_counts = {}

    def replace_ref(match):
        ref_name = match.group(1)
        if ref_name in ref_counts:
            ref_counts[ref_name] += 1
            return f'<ref name="{ref_name}"/>'
        else:
            ref_counts[ref_name] = 1
            return match.group(0)

    pattern = r'<ref name="([^\"]+)">[^<]+</ref>'
    return re.sub(pattern, replace_ref, wikitext)


def _build_wiki_ref_for_reports(metric, supplementary_query=Q()):
    query = Q(metrics_related__in=[metric]) & supplementary_query
    reports = Report.objects.filter(query)
    refs_set = []
    for report in reports:
        if not report.reference_text:
            links = report.links.replace("\\r\\n", "\r\n").splitlines()
            formatted_links = []
            for link in links:
                formatted_links.append(wikify_link(link))

            ref_content = ", ".join(formatted_links)
            if ref_content:
                refs_set.append(f'<ref name="sara-{report.id}">{ref_content}</ref>')
        else:
            refs_set.append(report.reference_text)
    return "".join(refs_set)


def _is_there_a_final_report(reports):
    return (
        reports.filter(
            metrics_related__boolean_type=True, partial_report=False
        ).exists()
        or False
    )


def _build_list_values(qs, name_field, reports, related_name, filter_fn=None):
    result = []
    for obj in qs:
        obj_reports = reports.filter(**{related_name: obj})
        if filter_fn and not filter_fn(obj, obj_reports):
            continue
        result.append(
            {
                "name": getattr(obj, name_field),
                "reports": list(obj_reports.values("id", "description")),
            }
        )
    return result
