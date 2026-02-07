import calendar
import datetime
import re
from io import StringIO

from django import template
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Q, Sum
from django.shortcuts import HttpResponse, redirect, render, reverse
from django.utils.translation import get_language
from django.utils.translation import gettext as _

from metrics.link_utils import process_all_references, wikify_link
from metrics.models import Activity, Metric
from metrics.utils import render_to_pdf
from report.models import Editor, OperationReport, Organizer, Partner, Project, Report
from users.models import TeamArea

register = template.Library()
calendar.setfirstweekday(calendar.SUNDAY)

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


# ======================================================================================================================
# ADMINISTRATIVE PAGES
# ======================================================================================================================
def index(request):
    context = {"title": _("Home")}
    return render(request, "metrics/home.html", context)


def about(request):
    context = {"title": _("About")}
    return render(request, "metrics/about.html", context)


def show_activities_plan(request):
    return redirect(settings.POA_URL)


# ======================================================================================================================
# METRICS
# ======================================================================================================================
@login_required
@permission_required("metrics.view_metric")
def prepare_pdf(request, *args, **kwargs):
    timespan_array = [
        (
            datetime.date(datetime.datetime.today().year, 1, 1),
            datetime.date(datetime.datetime.today().year, 3, 31),
        ),
        (
            datetime.date(datetime.datetime.today().year, 4, 1),
            datetime.date(datetime.datetime.today().year, 6, 18),
        ),
        (
            datetime.date(datetime.datetime.today().year, 6, 19),
            datetime.date(datetime.datetime.today().year, 9, 20),
        ),
        (
            datetime.date(datetime.datetime.today().year, 9, 21),
            datetime.date(datetime.datetime.today().year, 12, 31),
        ),
        (
            datetime.date(datetime.datetime.today().year, 1, 1),
            datetime.date(datetime.datetime.today().year, 12, 31),
        ),
    ]
    main_project = Project.objects.get(main_funding=True)
    main_results = get_results_for_timespan(
        timespan_array, Q(project=main_project), Q(), True, "en", True
    )

    metrics = []
    refs = []
    for metric in main_results:
        metrics.append(
            {
                "metric": metric["metric"],
                "q1": metric["done"][0],
                "q2": metric["done"][1],
                "q3": metric["done"][2],
                "q4": metric["done"][3],
                "total": metric["done"][4],
                "refs_short": sorted(re.findall(r"sara-(\d+)", metric["done"][5])),
                "goal": metric["done"][6],
            }
        )
        refs += process_all_references(metric["done"][5])

    refs = sorted(list(set(refs)))
    context = {"project": str(main_project), "metrics": metrics, "references": refs}

    return render_to_pdf("metrics/wmf_report.html", context)


@login_required
@permission_required("metrics.view_metric")
def show_metrics_per_project(request):
    current_language = get_language()
    poa_project = Project.objects.filter(current_poa=True).first()
    operational_dataset = get_metrics_and_aggregate_per_project(
        project_query=Q(current_poa=True),
        metric_query=Q(is_operation=True),
        lang=current_language,
    )

    poa_dataset = get_metrics_and_aggregate_per_project(
        project_query=Q(current_poa=True),
        metric_query=Q(boolean_type=True),
        field="Occurrence",
        lang=current_language,
    )

    if poa_dataset and operational_dataset:
        poa_dataset[poa_project.id]["project_metrics"] += operational_dataset[
            poa_project.id
        ]["project_metrics"]

    context = {
        "poa_dataset": poa_dataset,
        "dataset": get_metrics_and_aggregate_per_project(
            project_query=Q(active_status=True, current_poa=False),
            lang=current_language,
        ),
        "title": _("Show metrics per project"),
        "show_index": True,
    }

    return render(request, "metrics/list_metrics_per_project.html", context)


@login_required
@permission_required("metrics.view_metric")
def show_metrics_for_specific_project(request, project_id):
    current_language = get_language()
    project = Project.objects.get(pk=project_id)

    if project.current_poa:
        operational_dataset = get_metrics_and_aggregate_per_project(
            project_query=Q(current_poa=True),
            metric_query=Q(is_operation=True),
            lang=current_language,
        )

        metrics_aggregated = get_metrics_and_aggregate_per_project(
            project_query=Q(current_poa=True),
            metric_query=Q(boolean_type=True),
            field="Occurrence",
            lang=current_language,
        )
        if metrics_aggregated and operational_dataset:
            metrics_aggregated[project.id]["project_metrics"] += operational_dataset[
                project.id
            ]["project_metrics"]
    else:
        metrics_aggregated = get_metrics_and_aggregate_per_project(
            project_query=Q(pk=project_id), lang=current_language
        )

    context = {
        "dataset": metrics_aggregated,
        "title": project.text,
        "show_index": False,
    }

    return render(request, "metrics/list_metrics_per_project.html", context)


@login_required
@permission_required("admin.delete_logentry")
def show_detailed_metrics_per_project(request):
    context = {
        "poa_dataset": {},
        "dataset": get_metrics_and_aggregate_per_project(
            project_query=Q(active_status=True)
        ),
        "title": _("Show metrics per project"),
    }
    return render(request, "metrics/list_metrics_per_project.html", context)


@login_required
@permission_required("metrics.view_metric")
def metrics_reports(request, metric_id):
    try:
        metric = Metric.objects.get(pk=metric_id)
        reports = Report.objects.filter(metrics_related=metric_id).order_by("pk")

        goals = get_goal_for_metric(metric)
        filtered_goals = {key: value for key, value in goals.items() if goals[key] > 0}

        values = []
        for goal_key, goal_value in filtered_goals.items():
            report_values = []
            for report in reports:
                done = get_done_for_report(Report.objects.filter(pk=report.id), metric)
                report_values.append(
                    {
                        "id": report.id,
                        "description": report.description,
                        "initial_date": report.initial_date,
                        "end_date": report.end_date,
                        "done": done[goal_key],
                        "partial": report.partial_report,
                    }
                )
            values.append(
                {
                    "text": goal_key,
                    "goal": goal_value,
                    "done": sum([report_aux["done"] for report_aux in report_values]),
                    "reports": report_values,
                }
            )

        context = {"metric": metric, "values": values}

        return render(request, "metrics/list_metrics_reports.html", context)
    except ObjectDoesNotExist:
        return redirect(reverse("metrics:per_project"))


def update_metrics_relations(request):
    main_funding = Project.objects.get(main_funding=True)
    editors_filter = (
        Q(number_of_editors__gt=0)
        | Q(number_of_editors_retained__gt=0)
        | Q(number_of_new_editors__gt=0)
    )
    editors_metrics = Metric.objects.filter(project=main_funding).filter(editors_filter)
    reports = Report.objects.filter(Q(metrics_related__number_of_editors__gt=0))
    for report in reports:
        report.metrics_related.add(*editors_metrics)
        report.save()

    return redirect(reverse("metrics:per_project"))


# ======================================================================================================================
# EXPORT
# ======================================================================================================================
def export_trimester_report(request):
    return export_timespan_report(request, "trimester", False)


def export_trimester_report_by_area(request):
    return export_timespan_report(request, "trimester", True)


def export_semester_report(request):
    return export_timespan_report(request, "semester", False)


def export_semester_report_by_area(request):
    return export_timespan_report(request, "semester", True)


def export_year_report(request):
    return export_timespan_report(request, "year", False)


def export_year_report_by_area(request):
    return export_timespan_report(request, "year", True)


@login_required
@permission_required("metrics.view_metric")
def export_timespan_report(request, timeframe="trimester", by_area=False):
    buffer = StringIO()

    if by_area:
        for area in TeamArea.objects.filter(project__main_funding=True):
            get_results_divided_by_timespan(buffer, area, False, timeframe)
    else:
        get_results_divided_by_timespan(buffer, None, False, timeframe)

    response = HttpResponse(buffer.getvalue())
    response["Content-Type"] = "text/plain; charset=UTF-8"
    response["Content-Disposition"] = f'attachment; filename="{timeframe}_report.txt"'

    return response


# ======================================================================================================================
# FUNCTIONS
# ======================================================================================================================
def get_timespan_array(timeframe):
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


def get_header_columns(timeframe):
    labels = settings.REPORT_TIMESPANS[timeframe]["labels"]
    columns = " !! ".join(labels)
    return f"!Activity !! Metrics !! {columns} !! Total !! References\n|-\n"


def get_results_divided_by_timespan(
    buffer, area=None, with_goal=False, timeframe="semester"
):
    timespan_array = get_timespan_array(timeframe)

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

    poa_wikitext = construct_wikitext(
        poa_results, header + get_header_columns(timeframe)
    )

    main_wikitext = construct_wikitext(main_results, "")

    poa_wikitext = shorten_duplicate_refs(poa_wikitext)
    main_wikitext = shorten_duplicate_refs(main_wikitext)

    buffer.write(poa_wikitext)
    buffer.write(main_wikitext)
    buffer.write(footer)


def get_results_for_timespan(
    timespan_array,
    metric_query=Q(),
    report_query=Q(),
    with_goal=False,
    lang="pt",
    is_main_funding=False,
):
    results = []
    for metric in Metric.objects.filter(metric_query).order_by("activity_id", "id"):
        done_row = []
        refs = []
        goal_value = 0
        supplementary_query = Q()
        for time_ini, time_end in timespan_array:
            supplementary_query = (
                Q(end_date__gte=time_ini) & Q(end_date__lte=time_end) & report_query
            )
            goal, done, final = get_goal_and_done_for_metric(
                metric,
                supplementary_query=supplementary_query,
                is_main_funding=is_main_funding,
            )
            for key, value in goal.items():
                if value != 0:
                    done_row.append(done[key]) if done[key] else done_row.append("-")
                    goal_value = value

        refs.append(
            build_wiki_ref_for_reports(metric, supplementary_query=supplementary_query)
        )
        refs = list(dict.fromkeys(refs))
        done_row.append(" ".join(filter(None, refs)))

        # Get goal and attach to the array
        if with_goal:
            if goal_value:
                done_row.append(goal_value)
            else:
                done_row.append("?")

        if lang == "pt":
            results.append(
                {
                    "activity": metric.activity.text,
                    "metric": metric.text,
                    "done": done_row,
                }
            )
        else:
            results.append(
                {
                    "activity": metric.activity.text,
                    "metric": metric.text_en,
                    "done": done_row,
                }
            )
    return results


def get_metrics_and_aggregate_per_project(
    project_query=Q(active_status=True),
    metric_query=Q(),
    supplementary_query=Q(),
    field=None,
    lang="",
):
    aggregated_metrics_and_results = {}

    for project in Project.objects.filter(project_query).order_by(
        "-current_poa", "-main_funding"
    ):
        project_metrics = []
        for activity in Activity.objects.filter(area__project=project):
            activity_metrics = {}
            if activity.id != 1:
                q_filter = Q(project=project, activity=activity) & metric_query
            else:
                q_filter = Q(project=project) & metric_query
            for metric in Metric.objects.filter(q_filter):
                goal, done, final = get_goal_and_done_for_metric(
                    metric, supplementary_query, project.main_funding
                )

                if field and goal[field] != 0:
                    result_metrics = {
                        field: {
                            "goal": goal[field],
                            "done": done[field],
                            "final": final,
                        }
                    }
                else:
                    result_metrics = {
                        key: {"goal": value, "done": done[key], "final": final}
                        for key, value in goal.items()
                        if value != 0
                    }

                if not result_metrics:
                    result_metrics = {
                        "Other metric": {"goal": "-", "done": "-", "final": final}
                    }

                localized_title = metric.text_en if lang == "en" else metric.text
                activity_metrics[metric.id] = {
                    "title": localized_title,
                    "metrics": result_metrics,
                }

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
            }
    return aggregated_metrics_and_results


def get_goal_and_done_for_metric(
    metric, supplementary_query=Q(), is_main_funding=False
):
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
    final = is_there_a_final_report(reports)

    return goal, done, final


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
        "Number of editors": metric.number_of_editors,
        "Number of editors retained": metric.number_of_editors_retained,
        "Number of new editors": metric.number_of_new_editors,
        "Number of organizers": metric.number_of_organizers,
        "Number of organizers retained": metric.number_of_organizers_retained,
        "Number of new organizers": metric.number_of_new_organizers,
        "Number of partnerships activated": metric.number_of_partnerships_activated,
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


def get_done_for_report(reports, metric):
    operation_reports = OperationReport.objects.filter(
        report__in=reports, metric=metric
    )
    alternative_operation_reports = OperationReport.objects.filter(report__in=reports)

    reports_aggregations = reports.aggregate(
        wikipedia_created=Sum("wikipedia_created"),
        wikipedia_edited=Sum("wikipedia_edited"),
        commons_created=Sum("commons_created"),
        commons_edited=Sum("commons_edited"),
        wikidata_created=Sum("wikidata_created"),
        wikidata_edited=Sum("wikidata_edited"),
        wikiversity_created=Sum("wikiversity_created"),
        wikiversity_edited=Sum("wikiversity_edited"),
        wikibooks_created=Sum("wikibooks_created"),
        wikibooks_edited=Sum("wikibooks_edited"),
        wikisource_created=Sum("wikisource_created"),
        wikisource_edited=Sum("wikisource_edited"),
        wikinews_created=Sum("wikinews_created"),
        wikinews_edited=Sum("wikinews_edited"),
        wikiquote_created=Sum("wikiquote_created"),
        wikiquote_edited=Sum("wikiquote_edited"),
        wiktionary_created=Sum("wiktionary_created"),
        wiktionary_edited=Sum("wiktionary_edited"),
        wikivoyage_created=Sum("wikivoyage_created"),
        wikivoyage_edited=Sum("wikivoyage_edited"),
        wikispecies_created=Sum("wikispecies_created"),
        wikispecies_edited=Sum("wikispecies_edited"),
        metawiki_created=Sum("metawiki_created"),
        metawiki_edited=Sum("metawiki_edited"),
        mediawiki_created=Sum("mediawiki_created"),
        mediawiki_edited=Sum("mediawiki_edited"),
        wikifunctions_created=Sum("wikifunctions_created"),
        wikifunctions_edited=Sum("wikifunctions_edited"),
        incubator_created=Sum("incubator_created"),
        incubator_edited=Sum("incubator_edited"),
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
        "Wikipedia (created)": reports_aggregations["wikipedia_created"] or 0,
        "Wikipedia (edited)": reports_aggregations["wikipedia_edited"] or 0,
        "Wikimedia Commons (created)": reports_aggregations["commons_created"] or 0,
        "Wikimedia Commons (edited)": reports_aggregations["commons_edited"] or 0,
        "Wikidata (created)": reports_aggregations["wikidata_created"] or 0,
        "Wikidata (edited)": reports_aggregations["wikidata_edited"] or 0,
        "Wikiversity (created)": reports_aggregations["wikiversity_created"] or 0,
        "Wikiversity (edited)": reports_aggregations["wikiversity_edited"] or 0,
        "Wikibooks (created)": reports_aggregations["wikibooks_created"] or 0,
        "Wikibooks (edited)": reports_aggregations["wikibooks_edited"] or 0,
        "Wikisource (created)": reports_aggregations["wikisource_created"] or 0,
        "Wikisource (edited)": reports_aggregations["wikisource_edited"] or 0,
        "Wikinews (created)": reports_aggregations["wikinews_created"] or 0,
        "Wikinews (edited)": reports_aggregations["wikinews_edited"] or 0,
        "Wikiquote (created)": reports_aggregations["wikiquote_created"] or 0,
        "Wikiquote (edited)": reports_aggregations["wikiquote_edited"] or 0,
        "Wiktionary (created)": reports_aggregations["wiktionary_created"] or 0,
        "Wiktionary (edited)": reports_aggregations["wiktionary_edited"] or 0,
        "Wikivoyage (created)": reports_aggregations["wikivoyage_created"] or 0,
        "Wikivoyage (edited)": reports_aggregations["wikivoyage_edited"] or 0,
        "Wikispecies (created)": reports_aggregations["wikispecies_created"] or 0,
        "Wikispecies (edited)": reports_aggregations["wikispecies_edited"] or 0,
        "MetaWiki (created)": reports_aggregations["metawiki_created"] or 0,
        "MetaWiki (edited)": reports_aggregations["metawiki_edited"] or 0,
        "MediaWiki (created)": reports_aggregations["mediawiki_created"] or 0,
        "MediaWiki (edited)": reports_aggregations["mediawiki_edited"] or 0,
        "Wikifunctions (created)": reports_aggregations["wikifunctions_created"] or 0,
        "Wikifunctions (edited)": reports_aggregations["wikifunctions_edited"] or 0,
        "Incubator (created)": reports_aggregations["incubator_created"] or 0,
        "Incubator (edited)": reports_aggregations["incubator_edited"] or 0,
        # Financial metrics
        "Number of donors": reports_aggregations["donors"] or 0,
        "Number of submissions": reports_aggregations["submissions"] or 0,
        # Community metrics
        "Number of participants": reports_aggregations["participants"] or 0,
        "Number of feedbacks": reports_aggregations["feedbacks"] or 0,
        "Number of editors": editor_qs.count(),
        "Number of editors retained": editor_qs.filter(retained=True).count(),
        "Number of new editors": editor_qs.filter(
            account_creation_date__gte=F("editors__initial_date")
        ).count(),
        "Number of organizers": organizer_qs.count(),
        "Number of organizers retained": organizer_qs.filter(retained=True).count(),
        "Number of new organizers": organizer_qs.filter(
            first_seen_at__gte=F("organizers__initial_date")
        ).count(),
        "Number of partnerships activated": Partner.objects.filter(partners__in=reports)
        .distinct()
        .count(),
        "Number of new partnerships": operation_aggregations["new_partnerships"] or 0,
        "Number of resources": operation_aggregations["resources"]
        or alternative_operation_aggregations["resources"]
        or 0,
        "Number of events": operation_aggregations["events"]
        or alternative_operation_aggregations["events"]
        or 0,
        # Communication metrics
        "Number of new followers": operation_aggregations["new_followers"]
        or alternative_operation_aggregations["new_followers"]
        or 0,
        "Number of mentions": operation_aggregations["mentions"]
        or alternative_operation_aggregations["mentions"]
        or 0,
        "Number of community communications": operation_aggregations["communications"]
        or alternative_operation_aggregations["communications"]
        or 0,
        "Number of people reached through social media": operation_aggregations[
            "people_reached"
        ]
        or alternative_operation_aggregations["people_reached"]
        or 0,
        # Other metrics
        "Occurrence": reports.filter(metrics_related__boolean_type=True).exists(),
    }


def shorten_duplicate_refs(wikitext):
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


def construct_wikitext(results, wikitext):
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


def build_wiki_ref_for_reports(metric, supplementary_query=Q()):
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


def is_there_a_final_report(reports):
    return (
        reports.filter(
            metrics_related__boolean_type=True, partial_report=False
        ).exists()
        or False
    )
