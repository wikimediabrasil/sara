import re
import calendar
import datetime
from io import StringIO
from django import template
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, reverse, HttpResponse
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, Sum, F

from report.models import Report, Editor, Organizer, Partner, Project, OperationReport
from users.models import TeamArea
from metrics.utils import render_to_pdf
from metrics.models import Activity, Metric
from metrics.link_utils import process_all_references, wikify_link

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


def index(request):
    context = {"title": _("Home")}
    return render(request, "metrics/home.html", context)


def about(request):
    context = {"title": _("About")}
    return render(request, "metrics/about.html", context)


def show_activities_plan(request):
    return redirect(settings.POA_URL)


@login_required
@permission_required("metrics.view_metric")
def prepare_pdf(request, *args, **kwargs):
    timespan_array = [
        (datetime.date(datetime.datetime.today().year, 1, 1), datetime.date(datetime.datetime.today().year, 3, 31)),
        (datetime.date(datetime.datetime.today().year, 4, 1), datetime.date(datetime.datetime.today().year, 6, 18)),
        (datetime.date(datetime.datetime.today().year, 6, 19), datetime.date(datetime.datetime.today().year, 9, 20)),
        (datetime.date(datetime.datetime.today().year, 9, 21), datetime.date(datetime.datetime.today().year, 12, 31)),
        (datetime.date(datetime.datetime.today().year, 1, 1), datetime.date(datetime.datetime.today().year, 12, 31))
    ]
    main_project = Project.objects.get(main_funding=True)
    main_results = get_results_for_timespan(timespan_array,
                                            Q(project=main_project),
                                            Q(),
                                            True,
                                            "en",
                                            True)

    metrics = []
    refs = []
    for metric in main_results:
        metrics.append({
                           "metric": metric["metric"],
                           "q1": metric["done"][0],
                           "q2": metric["done"][1],
                           "q3": metric["done"][2],
                           "q4": metric["done"][3],
                           "total": metric["done"][4],
                           "refs_short": sorted(re.findall(r"sara-(\d+)", metric["done"][5])),
                           "goal": metric["done"][6],
                       })
        refs += process_all_references(metric["done"][5])

    refs = sorted(list(set(refs)))
    context = {"project":str(main_project), "metrics": metrics, "references": refs}

    return render_to_pdf('metrics/wmf_report.html', context)


@login_required
@permission_required("metrics.view_metric")
def show_metrics_per_project(request):
    current_language = get_language()
    poa_project = Project.objects.get(current_poa=True)
    operational_dataset = get_metrics_and_aggregate_per_project(project_query=Q(current_poa=True), metric_query=Q(is_operation=True), lang=current_language)

    poa_dataset = get_metrics_and_aggregate_per_project(project_query=Q(current_poa=True), metric_query=Q(boolean_type=True), field="Occurrence", lang=current_language)

    if poa_dataset and operational_dataset:
        poa_dataset[poa_project.id]["project_metrics"] += operational_dataset[poa_project.id]["project_metrics"]

    context = {
        "poa_dataset": poa_dataset,
        "dataset": get_metrics_and_aggregate_per_project(project_query=Q(active=True, current_poa=False), lang=current_language),
        "title": _("Show metrics per project")
    }

    return render(request, "metrics/list_metrics_per_project.html", context)


@login_required
@permission_required("metrics.view_metric")
def show_metrics_for_specific_project(request, project_id):
    current_language = get_language()
    project = Project.objects.get(pk=project_id)

    if project.current_poa:
        operational_dataset = get_metrics_and_aggregate_per_project(project_query=Q(current_poa=True), metric_query=Q(is_operation=True),
                                                                    lang=current_language)

        metrics_aggregated = get_metrics_and_aggregate_per_project(project_query=Q(current_poa=True), metric_query=Q(boolean_type=True),
                                                                   field="Occurrence", lang=current_language)
        if metrics_aggregated and operational_dataset:
            metrics_aggregated[project.id]["project_metrics"] += operational_dataset[project.id]["project_metrics"]
    else:
        metrics_aggregated = get_metrics_and_aggregate_per_project(project_query=Q(pk=project_id), lang=current_language)

    context = { "dataset": metrics_aggregated, "title": project.text }

    return render(request, "metrics/list_metrics_per_project.html", context)


@login_required
@permission_required("admin.delete_logentry")
def show_detailed_metrics_per_project(request):
    context = {
        "poa_dataset": {},
        "dataset": get_metrics_and_aggregate_per_project(project_query=Q(active=True)),
        "title": _("Show metrics per project")
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
                report_values.append({
                    "id": report.id,
                    "description": report.description,
                    "initial_date": report.initial_date,
                    "end_date": report.end_date,
                    "done": done[goal_key],
                    "partial": report.partial_report
                })
            values.append({
                "text": goal_key,
                "goal": goal_value,
                "done": sum([report_aux["done"] for report_aux in report_values]),
                "reports": report_values
            })

        context = {"metric": metric, "values": values}

        return render(request, "metrics/list_metrics_reports.html", context)
    except ObjectDoesNotExist:
        return redirect(reverse('metrics:per_project'))


@login_required
@permission_required("metrics.view_metric")
def export_trimester_report(request):
    buffer = StringIO()

    get_results_divided_by_trimester(buffer, None, False)

    response = HttpResponse(buffer.getvalue())
    response['Content-Type'] = 'text/plain; charset=UTF-8'
    response['Content-Disposition'] = 'attachment; filename="trimester_report.txt"'

    return response

@login_required
@permission_required("metrics.view_metric")
def export_trimester_report_by_by_area_responsible(request):
    buffer = StringIO()

    for area in TeamArea.objects.all():
        get_results_divided_by_trimester(buffer, area, False)

    response = HttpResponse(buffer.getvalue())
    response['Content-Type'] = 'text/plain; charset=UTF-8'
    response['Content-Disposition'] = 'attachment; filename="trimester_report.txt"'

    return response


def get_results_divided_by_trimester(buffer, area=None, with_goal=False):
    timespan_array = [
        (datetime.date(datetime.datetime.today().year, 1, 1), datetime.date(datetime.datetime.today().year, 3, 31)),
        (datetime.date(datetime.datetime.today().year, 4, 1), datetime.date(datetime.datetime.today().year, 6, 18)),
        (datetime.date(datetime.datetime.today().year, 6, 19), datetime.date(datetime.datetime.today().year, 9, 20)),
        (datetime.date(datetime.datetime.today().year, 9, 21), datetime.date(datetime.datetime.today().year, 12, 31)),
        (datetime.date(datetime.datetime.today().year, 1, 1), datetime.date(datetime.datetime.today().year, 12, 31))
    ]
    if area:
        report_query = Q(area_responsible=area)
        header = ("==" + area.text + "==\n<div class='wmb_report_table_container bd-" + area.color_code +
                  "'>\n{| class='wikitable wmb_report_table'\n! colspan='8' class='bg-" + area.color_code +
                  " co-" + area.color_code + "' | <h5 id='Metrics'>Operational and General metrics</h5>\n|-\n")
        footer = "|}\n</div>\n"
    else:
        report_query = Q()
        header = "{| class='wikitable wmb_report_table'\n"
        footer = "|}\n"

    poa_results = get_results_for_timespan(timespan_array,
                                           Q(project=Project.objects.get(current_poa=True), is_operation=True),
                                           report_query,
                                           with_goal,
                                           "en",
                                           False)
    main_results = get_results_for_timespan(timespan_array,
                                            Q(project=Project.objects.get(main_funding=True)),
                                            report_query,
                                            with_goal,
                                            "en",
                                            True)

    poa_wikitext = construct_wikitext(poa_results, header +
                                      "!Activity !! Metrics !! Q1 !! Q2 !! Q3 !! Q4 !! Total !! References\n|-\n")
    main_wikitext = construct_wikitext(main_results, "")

    poa_wikitext = shorten_duplicate_refs(poa_wikitext)
    main_wikitext = shorten_duplicate_refs(main_wikitext)

    buffer.write(poa_wikitext)
    buffer.write(main_wikitext)
    buffer.write(footer)


def get_results_for_timespan(timespan_array, metric_query=Q(), report_query=Q(), with_goal=False, lang="pt", is_main_funding=False):
    results = []
    for metric in Metric.objects.filter(metric_query).order_by("activity_id", "id"):
        done_row = []
        refs = []
        goal_value = 0
        supplementary_query = Q()
        for time_ini, time_end in timespan_array:
            supplementary_query = Q(end_date__gte=time_ini) & Q(end_date__lte=time_end) & report_query
            goal, done, final = get_goal_and_done_for_metric(metric, supplementary_query=supplementary_query, is_main_funding=is_main_funding)
            for key, value in goal.items():
                if value != 0:
                    done_row.append(done[key]) if done[key] else done_row.append("-")
                    goal_value = value

        refs.append(build_wiki_ref_for_reports(metric, supplementary_query=supplementary_query))
        refs = list(dict.fromkeys(refs))
        done_row.append(" ".join(filter(None, refs)))

        # Get goal and attach to the array
        if with_goal:
            if goal_value:
                done_row.append(goal_value)
            else:
                done_row.append("?")

        if lang == "pt":
            results.append({"activity": metric.activity.text, "metric": metric.text, "done": done_row})
        else:
            results.append({"activity": metric.activity.text, "metric": metric.text_en, "done": done_row})
    return results


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
    activities = list(dict.fromkeys(row['activity'] for row in results))
    other_activity = Activity.objects.get(pk=1).text in activities
    for activity in activities:
        metrics = [row for row in results if row['activity'] == activity]
        rowspan = len(metrics)
        if not other_activity:
            header = "| rowspan='{}' | {} |".format(rowspan, activity) if len(metrics) > 1 else "| {} |".format(
                activity)
        else:
            header = "| rowspan='{}' | - |".format(rowspan) if len(metrics) > 1 else "| - |"

        for metric in metrics:
            wikitext += header + "| {} || {}\n|-\n".format(metric["metric"], " || ".join(map(str, metric["done"])))
            header = ""

    return wikitext


def get_metrics_and_aggregate_per_project(project_query=Q(active=True), metric_query=Q(), supplementary_query=Q(), field=None, lang=""):
    aggregated_metrics_and_results = {}

    for project in Project.objects.filter(project_query).order_by("-current_poa", "-main_funding"):
        project_metrics = []
        for activity in Activity.objects.filter(area__project=project):
            activity_metrics = {}
            if activity.id != 1:
                q_filter = Q(project=project, activity=activity) & metric_query
            else:
                q_filter = Q(project=project) & metric_query
            for metric in Metric.objects.filter(q_filter):
                goal, done, final = get_goal_and_done_for_metric(metric, supplementary_query, project.main_funding)

                if field and goal[field] != 0:
                    result_metrics = {field: {"goal": goal[field], "done": done[field], "final": final}}
                else:
                    result_metrics = {key: {"goal": value, "done": done[key], "final": final} for key, value in goal.items() if
                                      value != 0}

                if not result_metrics:
                    result_metrics = {"Other metric": {"goal": "-", "done": "-", "final": final}}

                localized_title = metric.text_en if lang=="en" else metric.text
                activity_metrics[metric.id] = {"title": localized_title, "metrics": result_metrics}

            if activity_metrics:
                project_metrics.append({
                    "activity": activity.text,
                    "activity_id": activity.id,
                    "activity_metrics": activity_metrics
                })

        if project_metrics:
            aggregated_metrics_and_results[project.id] = {
                "project": project.text,
                "project_metrics": project_metrics
            }
    return aggregated_metrics_and_results


def get_goal_and_done_for_metric(metric, supplementary_query=Q(), is_main_funding=False):
    query = Q(metrics_related__in=[metric]) & supplementary_query
    reports = Report.objects.filter(query)
    if is_main_funding:
        reports = reports.exclude(
            (Q(activity_associated__area__project__counts_for_main_funding=False) | Q(funding_associated__project__counts_for_main_funding=False)) &
            ~(Q(activity_associated__id=1) & Q(funding_associated__project__counts_for_main_funding=True)) &
            ~(Q(activity_associated__id=1) & Q(funding_associated__isnull=True))
        )
    goal = get_goal_for_metric(metric)
    done = get_done_for_report(reports, metric)
    final = is_there_a_final_report(reports)

    return goal, done, final


def get_goal_for_metric(metric):
    return {
        # Content metrics
        "Wikipedia": metric.wikipedia_created + metric.wikipedia_edited,
        "Wikimedia Commons": metric.commons_created + metric.commons_edited,
        "Wikidata": metric.wikidata_created + metric.wikidata_edited,
        "Wikiversity": metric.wikiversity_created + metric.wikiversity_edited,
        "Wikibooks": metric.wikibooks_created + metric.wikibooks_edited,
        "Wikisource": metric.wikisource_created + metric.wikisource_edited,
        "Wikinews": metric.wikinews_created + metric.wikinews_edited,
        "Wikiquote": metric.wikiquote_created + metric.wikiquote_edited,
        "Wiktionary": metric.wiktionary_created + metric.wiktionary_edited,
        "Wikivoyage": metric.wikivoyage_created + metric.wikivoyage_edited,
        "Wikispecies": metric.wikispecies_created + metric.wikispecies_edited,
        "MetaWiki": metric.metawiki_created + metric.metawiki_edited,
        "MediaWiki": metric.mediawiki_created + metric.mediawiki_edited,
        # Community metrics
        "Number of editors": metric.number_of_editors,
        "Number of editors retained": metric.number_of_editors_retained,
        "Number of new editors": metric.number_of_new_editors,
        "Number of participants": metric.number_of_participants,
        "Number of partnerships activated": metric.number_of_partnerships_activated,
        "Number of new partnerships": metric.number_of_new_partnerships,
        "Number of organizers": metric.number_of_organizers,
        "Number of organizers retained": metric.number_of_organizers_retained,
        "Number of resources": metric.number_of_resources,
        "Number of feedbacks": metric.number_of_feedbacks,
        "Number of events": metric.number_of_events,
        # Communication metrics
        "Number of new followers": metric.number_of_new_followers,
        "Number of mentions": metric.number_of_mentions,
        "Number of community communications": metric.number_of_community_communications,
        "Number of people reached through social media": metric.number_of_people_reached_through_social_media,
        "Occurrence": metric.boolean_type,
    }


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
                refs_set.append(f"<ref name=\"sara-{report.id}\">{ref_content}</ref>")
        else:
            refs_set.append(report.reference_text)
    return "".join(refs_set)


def is_there_a_final_report(reports):
    return reports.filter(metrics_related__boolean_type=True, partial_report=False).exists() or False


def get_done_for_report(reports, metric):
    operation_reports = OperationReport.objects.filter(report__in=reports, metric=metric)
    alt_operation_reports = OperationReport.objects.filter(report__in=reports)
    return {
        # Content metrics
        "Wikipedia": reports.aggregate(total=Sum(F("wikipedia_created") + F("wikipedia_edited")))["total"] or 0,
        "Wikimedia Commons": reports.aggregate(total=Sum(F("commons_created") + F("commons_edited")))["total"] or 0,
        "Wikidata": reports.aggregate(total=Sum(F("wikidata_created") + F("wikidata_edited")))["total"] or 0,
        "Wikiversity": reports.aggregate(total=Sum(F("wikiversity_created") + F("wikiversity_edited")))["total"] or 0,
        "Wikibooks": reports.aggregate(total=Sum(F("wikibooks_created") + F("wikibooks_edited")))["total"] or 0,
        "Wikisource": reports.aggregate(total=Sum(F("wikisource_created") + F("wikisource_edited")))["total"] or 0,
        "Wikinews": reports.aggregate(total=Sum(F("wikinews_created") + F("wikinews_edited")))["total"] or 0,
        "Wikiquote": reports.aggregate(total=Sum(F("wikiquote_created") + F("wikiquote_edited")))["total"] or 0,
        "Wiktionary": reports.aggregate(total=Sum(F("wiktionary_created") + F("wiktionary_edited")))["total"] or 0,
        "Wikivoyage": reports.aggregate(total=Sum(F("wikivoyage_created") + F("wikivoyage_edited")))["total"] or 0,
        "Wikispecies": reports.aggregate(total=Sum(F("wikispecies_created") + F("wikispecies_edited")))["total"] or 0,
        "MetaWiki": reports.aggregate(total=Sum(F("metawiki_created") + F("metawiki_edited")))["total"] or 0,
        "MediaWiki": reports.aggregate(total=Sum(F("mediawiki_created") + F("mediawiki_edited")))["total"] or 0,
        # Community metrics
        "Number of editors": Editor.objects.filter(editors__in=reports).distinct().count() or 0,
        "Number of editors retained": Editor.objects.filter(retained=True, editors__in=reports).distinct().count() or 0,
        "Number of new editors": Editor.objects.filter(editors__in=reports, account_creation_date__gte=F('editors__initial_date')).count() or 0,
        "Number of participants": reports.aggregate(total=Sum("participants"))["total"] or 0,
        "Number of partnerships activated": Partner.objects.filter(partners__in=reports).distinct().count() or 0,
        "Number of new partnerships": operation_reports.aggregate(total=Sum("number_of_new_partnerships"))["total"] or 0,
        "Number of organizers": Organizer.objects.filter(organizers__in=reports).distinct().count() or 0,
        "Number of organizers retained": Organizer.objects.filter(retained=True,organizers__in=reports).distinct().count() or 0,
        "Number of resources": operation_reports.aggregate(total=Sum("number_of_resources"))["total"] or alt_operation_reports.aggregate(total=Sum("number_of_resources"))["total"] or 0,
        "Number of feedbacks": reports.aggregate(total=Sum("feedbacks"))["total"] or 0,"Number of events": operation_reports.aggregate(total=Sum("number_of_events"))["total"] or alt_operation_reports.aggregate(total=Sum("number_of_events"))["total"] or 0,
        # Communication metrics
        "Number of new followers": operation_reports.aggregate(total=Sum("number_of_new_followers"))["total"] or alt_operation_reports.aggregate(total=Sum("number_of_new_followers"))["total"] or 0,
        "Number of mentions": operation_reports.aggregate(total=Sum("number_of_mentions"))["total"] or alt_operation_reports.aggregate(total=Sum("number_of_mentions"))["total"] or 0,
        "Number of community communications": operation_reports.aggregate(total=Sum("number_of_community_communications"))["total"] or alt_operation_reports.aggregate(total=Sum("number_of_community_communications"))["total"] or 0,
        "Number of people reached through social media": operation_reports.aggregate(total=Sum("number_of_people_reached_through_social_media"))["total"] or alt_operation_reports.aggregate(total=Sum("number_of_people_reached_through_social_media"))["total"] or 0,
        # Other metrics
        "Occurrence": reports.filter(metrics_related__boolean_type=True).exists() or False,
    }


def update_metrics_relations(request):
    main_funding = Project.objects.get(main_funding=True)
    editors_filter = Q(number_of_editors__gt=0) | Q(number_of_editors_retained__gt=0) | Q(number_of_new_editors__gt=0)
    editors_metrics = Metric.objects.filter(project=main_funding).filter(editors_filter)
    reports = Report.objects.filter(Q(metrics_related__number_of_editors__gt=0))
    for report in reports:
        report.metrics_related.add(*editors_metrics)
        report.save()

    return redirect(reverse("metrics:per_project"))
