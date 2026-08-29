import calendar
import datetime
import re
from datetime import timedelta
from io import StringIO

from django import template
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Min, Q
from django.shortcuts import HttpResponse, redirect, render, reverse
from django.utils.translation import get_language, gettext as _
from django.views.decorators.http import require_http_methods

from metrics.link_utils import process_all_references
from metrics.models import Metric
from report.models import Editor, Organizer, Partner, Project, Report
from users.models import TeamArea

register = template.Library()
calendar.setfirstweekday(calendar.SUNDAY)

# ======================================================================================================================
# UTILS
# ======================================================================================================================
LIST_METRICS_PER_PROJECT_TEMPLATE = "metrics/list_metrics_per_project.html"
from metrics.utils import (
    EDITORS,
    EDITORS_RETAINED,
    EDITORS_NEW,
    ORGANIZERS,
    ORGANIZERS_RETAINED,
    ORGANIZERS_NEW,
    PARTNERSHIPS_ACTIVATED,
    get_results_divided_by_timespan,
    get_results_for_timespan,
    get_done_for_report,
    get_metrics_and_aggregate_per_project,
    get_goal_for_metric,
    render_to_pdf,
    _build_list_values,
)


# ======================================================================================================================
# ADMINISTRATIVE PAGES
# ======================================================================================================================
@require_http_methods(["GET"])
def index(request):
    context = {"title": _("Home")}
    return render(request, "metrics/home.html", context)


@require_http_methods(["GET"])
def about(request):
    context = {"title": _("About")}
    return render(request, "metrics/about.html", context)


@require_http_methods(["GET"])
def show_activities_plan(request):
    return redirect(settings.POA_URL)


# ======================================================================================================================
# METRICS
# ======================================================================================================================
@login_required
@permission_required("metrics.view_metric")
@require_http_methods(["GET"])
def show_metrics_per_project(request):
    """
    Aggregates metrics per active project.
    Prioritizes current Plan of Activities and Main Funding projects,
    but displays metrics for all the active projects.
    """

    current_language = get_language()

    full_dataset = get_metrics_and_aggregate_per_project(
        project_query=Q(active_status=True), lang=current_language
    )

    poa_dataset = {}
    other_projects_dataset = {}

    if full_dataset:
        for project_id, data in full_dataset.items():
            if data.get("current_poa"):
                poa_dataset[project_id] = data
            else:
                other_projects_dataset[project_id] = data

    context = {
        "poa_dataset": poa_dataset,
        "dataset": other_projects_dataset,
        "title": _("Show metrics per project"),
        "show_index": True,
    }

    return render(request, LIST_METRICS_PER_PROJECT_TEMPLATE, context)


@login_required
@permission_required("metrics.view_metric")
@require_http_methods(["GET"])
def show_metrics_for_specific_project(request, project_id):
    current_language = get_language()

    project = Project.objects.only("id", "current_poa", "text").get(pk=project_id)

    if project.current_poa:
        poa_query = Q(pk=project.id)

        operational_dataset = get_metrics_and_aggregate_per_project(
            project_query=poa_query,
            metric_query=Q(is_operation=True),
            lang=current_language,
        )

        metrics_aggregated = get_metrics_and_aggregate_per_project(
            project_query=poa_query,
            metric_query=Q(boolean_type=True),
            field="Occurrence",
            lang=current_language,
        )
        # Merge safely
        if (
            metrics_aggregated
            and operational_dataset
            and project.id in metrics_aggregated
            and project.id in operational_dataset
        ):
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

    return render(request, LIST_METRICS_PER_PROJECT_TEMPLATE, context)


@login_required
@permission_required("admin.delete_logentry")
@require_http_methods(["GET"])
def show_detailed_metrics_per_project(request):
    context = {
        "poa_dataset": {},
        "dataset": get_metrics_and_aggregate_per_project(
            project_query=Q(active_status=True)
        ),
        "title": _("Show metrics per project"),
    }
    return render(request, LIST_METRICS_PER_PROJECT_TEMPLATE, context)


@login_required
@permission_required("metrics.view_metric")
@require_http_methods(["GET"])
def metrics_reports(request, metric_id):
    try:
        metric = Metric.objects.get(pk=metric_id)
        reports = Report.objects.filter(metrics_related=metric_id).order_by("pk")

        goals = get_goal_for_metric(metric)
        filtered_goals = {key: value for key, value in goals.items() if goals[key] > 0}

        all_editors = Editor.objects.filter(editors__in=reports).distinct()
        all_organizers = Organizer.objects.filter(organizers__in=reports).distinct()
        all_partners = Partner.objects.filter(partners__in=reports).distinct()

        LIST_METRICS = {
            EDITORS: lambda: _build_list_values(
                all_editors, "username", reports, "editors"
            ),
            EDITORS_RETAINED: lambda: _build_list_values(
                all_editors.filter(retained=True), "username", reports, "editors"
            ),
            EDITORS_NEW: lambda: _build_list_values(
                all_editors,
                "username",
                reports,
                "editors",
                filter_fn=lambda ed, reps: (
                    lambda earliest: earliest is not None
                    and ed.account_creation_date is not None
                    and ed.account_creation_date.date() >= earliest - timedelta(days=30)
                )(reps.aggregate(earliest=Min("initial_date"))["earliest"]),
            ),
            ORGANIZERS: lambda: _build_list_values(
                all_organizers, "name", reports, "organizers"
            ),
            ORGANIZERS_RETAINED: lambda: _build_list_values(
                all_organizers.filter(retained=True), "name", reports, "organizers"
            ),
            ORGANIZERS_NEW: lambda: _build_list_values(
                all_organizers,
                "name",
                reports,
                "organizers",
                filter_fn=lambda org, reps: (
                    lambda earliest: earliest is not None
                    and org.first_seen_at is not None
                    and org.first_seen_at >= earliest
                )(reps.aggregate(earliest=Min("initial_date"))["earliest"]),
            ),
            PARTNERSHIPS_ACTIVATED: lambda: _build_list_values(
                all_partners, "name", reports, "partners_activated"
            ),
        }

        AGGREGATE_OVER_ALL_REPORTS = {
            "Number of new editors",
            "Number of new organizers",
        }

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
                        "area_responsible": report.area_responsible,
                    }
                )

            if goal_key in AGGREGATE_OVER_ALL_REPORTS:
                total_done = get_done_for_report(reports, metric)[goal_key]
            else:
                total_done = sum([report_aux["done"] for report_aux in report_values])

            values.append(
                {
                    "text": goal_key,
                    "goal": goal_value,
                    "done": total_done,
                    "reports": report_values,
                    "list_values": (
                        LIST_METRICS[goal_key]() if goal_key in LIST_METRICS else None
                    ),
                }
            )

        context = {"metric": metric, "values": values, "title": metric.text}

        return render(request, "metrics/list_metrics_reports.html", context)
    except ObjectDoesNotExist:
        return redirect(reverse("metrics:per_project"))


@login_required
@permission_required("metrics.view_metric")
@require_http_methods(["GET"])
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

    refs = sorted(set(refs))
    context = {"project": str(main_project), "metrics": metrics, "references": refs}

    return render_to_pdf("metrics/wmf_report.html", context)


@require_http_methods(["GET"])
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
@require_http_methods(["GET"])
def export_trimester_report(request):
    return export_timespan_report(request, "trimester", False)


@require_http_methods(["GET"])
def export_trimester_report_by_area(request):
    return export_timespan_report(request, "trimester", True)


@require_http_methods(["GET"])
def export_semester_report(request):
    return export_timespan_report(request, "semester", False)


@require_http_methods(["GET"])
def export_semester_report_by_area(request):
    return export_timespan_report(request, "semester", True)


@require_http_methods(["GET"])
def export_year_report(request):
    return export_timespan_report(request, "year", False)


@require_http_methods(["GET"])
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
