import datetime
import zipfile
from io import BytesIO

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.shortcuts import HttpResponse, get_object_or_404, redirect, render, reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from .forms import BugForm, BugUpdateForm, ObservationForm
from .models import Bug, Observation

# ======================================================================================================================
# UTILS
# ======================================================================================================================
DATE_OF_REPORT = _("Date of report"),
UPDATE_DATE = _("Update date"),
ANSWER_DATE = _("Answer date")
ERROR_MESSAGE = _("Something went wrong!")
DATETIME64 = "datetime64[ns]"

URL_DETAIL_BUG = "bug:detail_bug"


# ======================================================================================================================
# BUGS
# ======================================================================================================================
@permission_required("bug.add_bug")
def add_bug(request):
    """
    Create a new bug report.

    - On GET: displays the bug creation form.
    - On POST: validates and saves a new bug, assigning the current user's profile
      as the reporter.

    Redirects to the bug detail page on success.
    """
    if request.method == "POST":
        bug_form = BugForm(request.POST)
        if bug_form.is_valid():
            bug = bug_form.save(commit=False)
            bug.reporter = request.user.profile
            bug.save()

            messages.success(request, _("Reported successfully!"))
            return redirect(reverse(URL_DETAIL_BUG, kwargs={"bug_id": bug.pk}))
        else:
            bug_form = BugForm(request.POST)
            messages.error(request, ERROR_MESSAGE)
    else:
        bug_form = BugForm()

    return render(request, "bug/add_bug.html", {"bug_form": bug_form})


@permission_required("bug.view_bug")
@require_http_methods(["GET"])
def list_bugs(request):
    """
    List all bug reports ordered by status.
    """
    bugs = Bug.objects.all().order_by("status")
    context = {"dataset": bugs}
    return render(request, "bug/list_bugs.html", context)


@permission_required("bug.view_bug")
@require_http_methods(["GET"])
def export_bugs(request):
    """
    Export all bugs and their observations as a ZIP file.

    The ZIP contains:
    - A CSV file
    - An Excel (.xlsx) file

    Both files include bug metadata and related observation data when available.
    """
    buffer = BytesIO()
    zip_file = zipfile.ZipFile(buffer, mode="w")
    pos_fix = " - {}".format(datetime.datetime.today().strftime("%Y-%m-%d %H-%M-%S"))
    zip_name = _("SARA - Bugs")

    bugs = Bug.objects.all()
    header = [
        _("ID"),
        _("Title"),
        _("Description"),
        _("Type"),
        _("Status"),
        DATE_OF_REPORT,
        _("Reporter"),
        UPDATE_DATE,
        _("Observation"),
        ANSWER_DATE,
    ]
    rows = []

    for bug in bugs:
        try:
            bug_observation = bug.observation
        except Observation.DoesNotExist:
            bug_observation = None

        observation = bug_observation.observation if bug_observation else ""
        answer_date = bug_observation.answer_date if bug_observation else ""

        rows.append(
            [
                bug.pk,
                bug.title,
                bug.description,
                bug.bug_type,
                bug.status,
                bug.report_date,
                bug.reporter_id,
                bug.update_date,
                observation,
                answer_date,
            ]
        )

    df = pd.DataFrame(rows, columns=header).drop_duplicates()
    df = df.astype(
        dtype={
            _("ID"): int,
            _("Title"): str,
            _("Description"): str,
            _("Type"): int,
            _("Status"): int,
            DATE_OF_REPORT: DATETIME64,
            _("Reporter"): int,
            UPDATE_DATE: DATETIME64,
            _("Observation"): str,
            ANSWER_DATE: DATETIME64,
        }
    )
    df[DATE_OF_REPORT] = df[DATE_OF_REPORT].dt.tz_localize(None)
    df[UPDATE_DATE] = df[UPDATE_DATE].dt.tz_localize(None)
    df[ANSWER_DATE] = df[ANSWER_DATE].dt.tz_localize(None)

    csv_file = BytesIO()
    df.to_csv(path_or_buf=csv_file, index=False)
    zip_file.writestr("{}.csv".format("Bug report" + pos_fix), csv_file.getvalue())

    excel_file = BytesIO()
    writer = pd.ExcelWriter(excel_file, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Report", index=False)
    writer.close()
    zip_file.writestr("{}.xlsx".format("Bug report" + pos_fix), excel_file.getvalue())

    zip_file.close()
    response = HttpResponse(buffer.getvalue())
    response["Content-Type"] = "application/x-zip-compressed"
    response["Content-Disposition"] = (
        "attachment; filename=" + zip_name + pos_fix + ".zip"
    )

    return response


@permission_required("bug.view_bug")
@require_http_methods(["GET"])
def detail_bug(request, bug_id):
    """
    Display details for a single bug report.
    """
    context = {"data": Bug.objects.get(pk=bug_id)}

    return render(request, "bug/detail_bug.html", context)


@permission_required("bug.change_bug")
def update_bug(request, bug_id):
    """
    Update an existing bug.

    Users with observation permissions can update additional fields.
    Updates the bug's `update_date` on successful save.
    """
    bug = get_object_or_404(Bug, pk=bug_id)

    if request.user.has_perm("bug.add_observation"):
        bug_form = BugUpdateForm(request.POST or None, instance=bug)
    else:
        bug_form = BugForm(request.POST or None, instance=bug)

    if request.method == "POST":
        if bug_form.is_valid():
            bug = bug_form.save(commit=False)
            bug.update_date = datetime.datetime.today()
            bug.save()
            messages.success(request, _("Changes made successfully!"))
            return redirect(reverse(URL_DETAIL_BUG, kwargs={"bug_id": bug_id}))
        else:
            messages.error(request, ERROR_MESSAGE)
    return render(
        request, "bug/update_bug.html", {"bug_form": bug_form, "bug_id": bug_id}
    )


# ======================================================================================================================
# OBSERVATIONS
# ======================================================================================================================
@permission_required("bug.add_observation")
def add_observation(request, bug_id):
    """
    Add an observation (answer) to a bug.

    If an observation already exists, redirects to the edit view instead.
    """
    if request.method == "POST":
        obs_form = ObservationForm(request.POST)
        if obs_form.is_valid():
            obs = obs_form.save(commit=False)
            obs.bug_report = Bug.objects.get(pk=bug_id)
            obs.save()

            messages.success(request, _("Answered successfully!"))
            return redirect(reverse(URL_DETAIL_BUG, kwargs={"bug_id": bug_id}))
        else:
            obs_form = ObservationForm(request.POST)
            messages.error(request, ERROR_MESSAGE)
    else:
        if Observation.objects.filter(bug_report_id=bug_id).exists():
            return redirect(reverse("bug:edit_obs", kwargs={"bug_id": bug_id}))
        else:
            obs_form = ObservationForm()
    return render(
        request, "bug/add_observation.html", {"obs_form": obs_form, "bug_id": bug_id}
    )


@permission_required("bug.change_observation")
def edit_observation(request, bug_id):
    """
    Edit an existing observation for a bug.

    Automatically updates the observation answer date on save.
    """
    obs = get_object_or_404(Observation, bug_report=bug_id)

    if request.method == "POST":
        obs_form = ObservationForm(request.POST, instance=obs)

        if obs_form.is_valid():
            obs = obs_form.save(commit=False)
            obs.answer_date = datetime.datetime.today()
            obs.save()
            messages.success(request, _("Changes made successfully!"))

            return redirect(reverse(URL_DETAIL_BUG, kwargs={"bug_id": bug_id}))
        else:
            obs_form = ObservationForm(instance=obs)
            messages.error(request, ERROR_MESSAGE)
    else:
        obs_form = ObservationForm(instance=obs)
    return render(
        request, "bug/update_observation.html", {"obs_form": obs_form, "bug_id": bug_id}
    )
