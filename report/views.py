import datetime
import zipfile
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import HttpResponse, get_object_or_404, redirect, render, reverse
from django.utils import translation
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from metrics.models import Metric
from report.forms import NewReportForm, OperationUpdateFormSet
from report.models import OperationReport, Report, Project, Activity


# ======================================================================================================================
# UTILS
# ======================================================================================================================
from report.export_utils import (add_csv_file, add_excel_file, export_report_instance, export_operation_report,
                                 export_metrics, export_user_profile, export_funding, export_area_activated,
                                 export_directions_related, export_editors, export_learning_questions_related,
                                 export_organizers, export_partners_activated, export_technologies_used)
from report.utils import get_operation_formset, create_report
DETAIL_REPORT_URL = "report:detail_report"



@login_required
@permission_required("report.add_report")
def add_report(request):
    operation_form_set = get_operation_formset()

    if request.method == "POST":
        report_form = NewReportForm(request.POST, user=request.user)
        operation_metrics = operation_form_set(request.POST, prefix="Operation")

        if report_form.is_valid() and operation_metrics.is_valid():
            report = create_report(report_form, operation_metrics, request.user)
            messages.success(request, _("Report registered successfully!"))
            return redirect(
                reverse(DETAIL_REPORT_URL, kwargs={"report_id": report.id})
            )

        messages.error(request, _("Something went wrong!"))
        for field, error in report_form.errors.items():
            messages.error(request, f"{field}: {error[0]}")
    else:
        report_form = NewReportForm(user=request.user)
        operation_metrics = operation_form_set(
            prefix="Operation",
            initial=[
                {"metric": metric}
                for metric in Metric.objects.filter(is_operation=True)
            ],
        )

    context = {
        "report_form": report_form,
        "operation_metrics": operation_metrics,
        "title": _("Add report"),
        "partners_set": (
            request.POST.getlist("partners_activated")
            if request.method == "POST"
            else []
        ),
    }

    return render(request, "report/add_report.html", context)


@login_required
@permission_required("report.view_report")
@require_http_methods(["GET"])
def list_reports(request):
    current_year = now().year

    return list_reports_of_year(request, current_year)


@login_required
@permission_required("report.view_report")
@require_http_methods(["GET"])
def list_reports_of_year(request, year):
    custom_filter = Q(initial_date__year=year) | Q(end_date__year=year)
    context = {
        "dataset": Report.objects.filter(custom_filter).order_by("-created_at"),
        "mine": False,
        "title": _("List reports of %(year)s") % {"year": year},
        "year": year,
        "previous_year": int(year) - 1,
    }

    return render(request, "report/list_reports.html", context)


@login_required
@permission_required("report.view_report")
@require_http_methods(["GET"])
def detail_report(request, report_id):
    report = Report.objects.get(id=report_id)
    operations = OperationReport.objects.filter(report=report)
    operations_with_value = operations.filter(
        Q(number_of_people_reached_through_social_media__gt=0)
        | Q(number_of_new_followers__gt=0)
        | Q(number_of_mentions__gt=0)
        | Q(number_of_community_communications__gt=0)
        | Q(number_of_events__gt=0)
        | Q(number_of_resources__gt=0)
        | Q(number_of_partnerships_activated__gt=0)
        | Q(number_of_new_partnerships__gt=0)
    )
    context = {
        "data": report,
        "operations": operations_with_value,
        "operations_with_value": operations_with_value.exists(),
        "title": _("View report %(report_id)s") % {"report_id": report_id},
    }

    return render(request, "report/detail_report.html", context)


@login_required
@permission_required("report.view_report")
@require_http_methods(["GET"])
def export_report(request, report_id=None, year=None):
    if Report.objects.count():
        lang = translation.get_language()
        buffer = BytesIO()
        zip_file = zipfile.ZipFile(buffer, mode="w")
        sub_directory = "csv/"

        if report_id:
            zip_name = _("Report")
            identifier = " {}".format(report_id)
        else:
            zip_name = _("SARA - Reports")
            identifier = ""

        if year:
            custom_query = Q(initial_date__year=year) | Q(end_date__year=year)
        else:
            custom_query = Q()

        posfix = identifier + " - {}".format(
            datetime.datetime.today().strftime("%Y-%m-%d")
        )
        files = [
            [export_report_instance, sub_directory + "Report" + posfix],
            [export_operation_report, sub_directory + "Operation report" + posfix],
            [export_metrics, sub_directory + "Metrics" + posfix],
            [export_user_profile, sub_directory + "Users" + posfix],
            [export_area_activated, sub_directory + "Areas" + posfix],
            [export_directions_related, sub_directory + "Directions" + posfix],
            [
                export_learning_questions_related,
                sub_directory + "Learning questions" + posfix,
            ],
            [export_funding, sub_directory + "Fundings" + posfix],
            [export_editors, sub_directory + "Editors" + posfix],
            [export_organizers, sub_directory + "Organizers" + posfix],
            [export_partners_activated, sub_directory + "Partners" + posfix],
            [export_technologies_used, sub_directory + "Technologies" + posfix],
        ]

        for file in files:
            zip_file.writestr(
                "{}.csv".format(file[1]),
                add_csv_file(file[0], report_id, custom_query).getvalue(),
            )
        zip_file.writestr(
            "Export" + posfix + ".xlsx",
            add_excel_file(report_id, custom_query, lang).getvalue(),
        )

        zip_file.close()

        response = HttpResponse(buffer.getvalue())
        response["Content-Type"] = "application/x-zip-compressed"
        response["Content-Disposition"] = (
            "attachment; filename=" + zip_name + posfix + ".zip"
        )

        return response
    else:
        return redirect(reverse("report:list_reports"))


@login_required
@permission_required("report.change_report")
def update_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)

    if report.locked and not request.user.has_perm("report.can_edit_locked_report"):
        messages.error(
            request,
            _(
                "You do not have permission to edit this report. Please, share the link with the Products and Technology team for any questions."
            ),
        )
        return redirect(
            reverse(DETAIL_REPORT_URL, kwargs={"report_id": report_id})
        )

    if request.method == "POST":
        report_form = NewReportForm(
            request.POST, instance=report, user=request.user, is_update=True
        )
        operation_metrics = OperationUpdateFormSet(
            request.POST, instance=report, prefix="Operation"
        )
        if report_form.is_valid() and operation_metrics.is_valid():
            with transaction.atomic():
                report = report_form.save(user=request.user)

                operation_metrics.save()

            messages.success(request, _("Report updated successfully!"))
            return redirect(
                reverse(DETAIL_REPORT_URL, kwargs={"report_id": report.id})
            )
    else:
        report_form = NewReportForm(instance=report, user=request.user, is_update=True)
        operation_metrics = OperationUpdateFormSet(prefix="Operation", instance=report)

    context = {
        "report_form": report_form,
        "report_id": report.id,
        "operation_metrics": operation_metrics,
        "directions_related_set": list(
            report.directions_related.values_list("id", flat=True)
        ),
        "learning_questions_related_set": list(
            report.learning_questions_related.values_list("id", flat=True)
        ),
        "metrics_set": list(report.metrics_related.values_list("id", flat=True)),
        "title": _("Edit report %(report_id)s") % {"report_id": report.id},
        "partners_set": (
            request.POST.getlist("partners_activated")
            if request.method == "POST"
            else list(report.partners_activated.values_list("id", flat=True))
        ),
    }

    return render(request, "report/update_report.html", context)


@login_required
@permission_required("report.delete_report")
def delete_report(request, report_id):
    report = Report.objects.get(id=report_id)
    context = {
        "report": report,
        "title": _("Delete report %(report_id)s") % {"report_id": report_id},
    }

    if request.method == "POST":
        report.delete()
        return redirect(reverse("report:list_reports"))

    return render(request, "report/delete_report.html", context)


@login_required
@permission_required("report.view_report")
@require_http_methods(["GET"])
def get_metrics(request):
    projects = []
    main_ = False
    user_lang = translation.get_language()

    # ACTIVITY
    activity = request.GET.get("activity")
    if activity and activity != "1":
        activity_project = Project.objects.get(
            project_activity__activities=int(activity), active_status=True
        )
        metrics = Metric.objects.filter(activity_id=activity).values()
        main_ = Activity.objects.get(pk=int(activity)).is_main_activity
        projects.append(
            {
                "project": activity_project.text,
                "metrics": list(metrics),
                "main": main_,
                "lang": user_lang,
            }
        )
    elif activity == "1":
        for project in Project.objects.filter(active_status=True).exclude(
            current_poa=True
        ):
            metrics = Metric.objects.filter(project=project).values()
            if metrics:
                projects.append(
                    {
                        "project": project.text,
                        "metrics": list(metrics),
                        "lang": user_lang,
                    }
                )

    # FUNDINGS
    fundings_ids = request.GET.getlist("fundings[]")
    projects_ids = Project.objects.filter(Q(project_related__in=fundings_ids))
    for project in projects_ids:
        metrics = Metric.objects.filter(project=project).values().order_by("text")
        projects.append(
            {"project": project.text, "metrics": list(metrics), "lang": user_lang}
        )

    # INSTANCE
    instance = request.GET.get("instance")
    if instance:
        report = Report.objects.get(pk=instance)
        metrics_ids = [
            metric["id"] for project in projects for metric in project["metrics"]
        ]
        metrics_aux = report.metrics_related.all().values()
        metrics = [metric for metric in metrics_aux if metric["id"] not in metrics_ids]
        main_ = report.activity_associated.is_main_activity

        if metrics:
            projects.append(
                {
                    "project": _("Other metrics"),
                    "metrics": list(metrics),
                    "lang": user_lang,
                }
            )

    if projects:
        return JsonResponse({"objects": projects, "main": main_})
    else:
        return JsonResponse({"objects": None, "main": main_})