import datetime
import pandas as pd
import zipfile
from io import BytesIO

from django.utils import timezone
from django.forms import inlineformset_factory
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect, reverse, HttpResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.translation import gettext as _
from django.utils import translation
from django.contrib import messages
from django.db.models import Q
from django.utils.timezone import now

from metrics.models import Metric, Project
from report.models import Funding, Report, Activity, OperationReport
from users.models import TeamArea
from report.forms import NewReportForm, OperationForm, OperationUpdateFormSet


# ======================================================================================================================
# CREATE
# ======================================================================================================================
@login_required
@permission_required("report.add_report")
def add_report(request):
    operation_form_set = get_operation_formset()

    if request.method == "POST":
        report_form = NewReportForm(request.POST, user=request.user)
        operation_metrics = operation_form_set(request.POST, prefix='Operation')

        if report_form.is_valid() and operation_metrics.is_valid():
            timediff = timezone.now() - datetime.timedelta(hours=24)
            description = report_form.cleaned_data.get("description")

            with transaction.atomic():
                report_exists = Report.objects.filter(
                    created_by__user=request.user,
                    description=description,
                    created_at__gte=timediff,
                ).exists()

                if report_exists:
                    raise ValueError(_("Report already exists!"))

                report = report_form.save(user=request.user)

                instances = operation_metrics.save(commit=False)
                operation_metrics_related = []

                for instance in instances:
                    instance.report = report
                    instance.save()

                    numeric_fields = [
                        "number_of_people_reached_through_social_media",
                        "number_of_new_followers",
                        "number_of_mentions",
                        "number_of_community_communications",
                        "number_of_events",
                        "number_of_resources",
                        "number_of_partnerships_activated",
                        "number_of_new_partnerships",
                    ]

                    if any(getattr(instance, f, 0) > 0 for f in numeric_fields):
                        operation_metrics_related.append(instance.metric)

                if operation_metrics_related:
                    report.metrics_related.add(*operation_metrics_related)

            messages.success(request, _("Report registered successfully!"))
            return redirect(reverse("report:detail_report", kwargs={"report_id": report.id}))
        else:
            messages.error(request, _("Something went wrong!"))
            for field, error in report_form.errors.items():
                messages.error(request, f"{field}: {error[0]}")
    else:
        report_form = NewReportForm(user=request.user)
        operation_metrics = operation_form_set(
            prefix='Operation',
            initial=[{"metric": metric} for metric in Metric.objects.filter(is_operation=True)],
        )

    context = {
        "report_form": report_form,
        "operation_metrics": operation_metrics,
        "title": _("Add report")
    }

    return render(request, "report/add_report.html", context)


def get_operation_formset():
    return inlineformset_factory(
        Report,
        OperationReport,
        form=OperationForm,
        fields=('metric',
                'number_of_people_reached_through_social_media',
                'number_of_new_followers',
                'number_of_mentions',
                'number_of_community_communications',
                'number_of_events',
                'number_of_resources',
                'number_of_partnerships_activated',
                'number_of_new_partnerships'), extra=Metric.objects.filter(is_operation=True).count(),
        can_delete=False)

# ======================================================================================================================
# REVIEW
# ======================================================================================================================
@login_required
@permission_required("report.view_report")
def list_reports(request):
    current_year = now().year

    return list_reports_of_year(request, current_year)


@login_required
@permission_required("report.view_report")
def list_reports_of_year(request, year):
    custom_filter = Q(initial_date__year=year) | Q(end_date__year=year)
    context = {"dataset": Report.objects.filter(custom_filter).order_by('-created_at'), "mine": False, "title": _("List reports of %(year)s") % {"year": year}, "year": year, "previous_year": int(year)-1}

    return render(request, "report/list_reports.html", context)


@login_required
@permission_required("report.view_report")
def detail_report(request, report_id):
    report = Report.objects.get(id=report_id)
    operations = OperationReport.objects.filter(report=report)
    operations_with_value = operations.filter(Q(number_of_people_reached_through_social_media__gt=0) | Q(number_of_new_followers__gt=0) | Q(number_of_mentions__gt=0) | Q(number_of_community_communications__gt=0) | Q(number_of_events__gt=0) | Q(number_of_resources__gt=0) | Q(number_of_partnerships_activated__gt=0) | Q(number_of_new_partnerships__gt=0))
    context = {"data": report,
               "operations": operations_with_value,
               "operations_with_value": operations_with_value.exists(),
               "title": _("View report %(report_id)s") % {"report_id": report_id}}

    return render(request, "report/detail_report.html", context)


# ======================================================================================================================
# EXPORT
# ======================================================================================================================
@login_required
@permission_required("report.view_report")
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

        posfix = identifier + " - {}".format(datetime.datetime.today().strftime('%Y-%m-%d'))
        files = [[export_report_instance, sub_directory + 'Report' + posfix],
                 [export_operation_report, sub_directory + 'Operation report' + posfix],
                 [export_metrics, sub_directory + 'Metrics' + posfix],
                 [export_user_profile, sub_directory + 'Users' + posfix],
                 [export_area_activated, sub_directory + 'Areas' + posfix],
                 [export_directions_related, sub_directory + 'Directions' + posfix],
                 [export_learning_questions_related, sub_directory + 'Learning questions' + posfix],
                 [export_funding, sub_directory + 'Fundings' + posfix],
                 [export_editors, sub_directory + 'Editors' + posfix],
                 [export_organizers, sub_directory + 'Organizers' + posfix],
                 [export_partners_activated, sub_directory + 'Partners' + posfix],
                 [export_technologies_used, sub_directory + 'Technologies' + posfix]]

        for file in files:
            zip_file.writestr('{}.csv'.format(file[1]), add_csv_file(file[0], report_id, custom_query).getvalue())
        zip_file.writestr('Export' + posfix + '.xlsx', add_excel_file(report_id, custom_query, lang).getvalue())

        zip_file.close()

        response = HttpResponse(buffer.getvalue())
        response['Content-Type'] = 'application/x-zip-compressed'
        response['Content-Disposition'] = 'attachment; filename=' + zip_name + posfix + '.zip'

        return response
    else:
        return redirect(reverse("report:list_reports"))


def add_csv_file(function_name, report_id=None, custom_query=None):
    csv_file = BytesIO()
    function_name(report_id, custom_query).to_csv(path_or_buf=csv_file, index=False)

    return csv_file


def add_excel_file(report_id=None, custom_query=None, lang=""):
    excel_file = BytesIO()
    writer = pd.ExcelWriter(excel_file, engine='xlsxwriter')

    export_report_instance(report_id, custom_query).to_excel(writer, sheet_name='Report', index=False)
    export_operation_report(report_id, custom_query, lang).to_excel(writer, sheet_name='Operation report', index=False)
    export_metrics(report_id, custom_query).to_excel(writer, sheet_name='Metrics', index=False)
    export_user_profile(report_id, custom_query).to_excel(writer, sheet_name='Users', index=False)
    export_area_activated(report_id, custom_query).to_excel(writer, sheet_name='Areas', index=False)
    export_directions_related(report_id, custom_query).to_excel(writer, sheet_name='Directions', index=False)
    export_editors(report_id, custom_query).to_excel(writer, sheet_name='Editors', index=False)
    export_funding(report_id, custom_query).to_excel(writer, sheet_name='Fundings', index=False)
    export_learning_questions_related(report_id, custom_query).to_excel(writer, sheet_name='Learning questions', index=False)
    export_organizers(report_id, custom_query).to_excel(writer, sheet_name='Organizers', index=False)
    export_partners_activated(report_id, custom_query).to_excel(writer, sheet_name='Partners', index=False)
    export_technologies_used(report_id, custom_query).to_excel(writer, sheet_name='Technologies', index=False)

    writer.close()
    return excel_file


def export_report_instance(report_id=None, custom_query=Q()):
    header = [_('ID'), _('Created by'), _('Created at'), _('Modified by'), _('Modified at'), _('Activity associated'),
              _('Partial report?'), _('Name of the activity'), _('Reference Text'), _('Area responsible'),
              _('Area activated'), _('Initial date'), _('End date'), _('Description'), _('Funding associated'),
              _('Links'), _('Are there private links?'), _('Number of participants'), _('Number of feedbacks'),
              _('Editors'), _('# Editors'), _('Organizers'), _('# Organizers'), _('Partnerships activated'),
              _('# Partnerships activated'), _('Technologies used'), _('# Donors'), _('# Submissions'),
              _('# Wikipedia created'), _('# Wikipedia edited'),
              _('# Commons created'), _('# Commons edited'),
              _('# Wikidata created'), _('# Wikidata edited'),
              _('# Wikiversity created'), _('# Wikiversity edited'),
              _('# Wikibooks created'), _('# Wikibooks edited'),
              _('# Wikisource created'), _('# Wikisource edited'),
              _('# Wikinews created'), _('# Wikinews edited'),
              _('# Wikiquote created'), _('# Wikiquote edited'),
              _('# Wiktionary created'), _('# Wiktionary edited'),
              _('# Wikivoyage created'), _('# Wikivoyage edited'),
              _('# Wikispecies created'), _('# Wikispecies edited'),
              _('# Metawiki created'), _('# Metawiki edited'),
              _('# MediaWiki created'), _('# MediaWiki edited'),
              _('# Wikifunctions created'), _('# Wikifunctions edited'),
              _('# Incubator created'), _('# Incubator edited'),
              _('Directions related'), _('Learning'), _('Learning questions related'), _('Metrics related')]

    if report_id:
        reports = Report.objects.filter(pk=report_id)
    else:
        reports = Report.objects.filter(custom_query)

    rows = []
    for report in reports:
        # Database
        id_ = report.id
        created_by = report.created_by.id
        created_at = report.created_at
        modified_by = report.modified_by.id
        modified_at = report.modified_at
        partial_report = report.partial_report
        reference_text = report.reference_text
        private_links = report.private_links

        # Administrative
        activity_associated = report.activity_associated.id
        activity_name = report.activity_associated.text or ""
        area_responsible = report.area_responsible.id
        if report.area_activated.exists():
            area_activated = "; ".join(map(str, report.area_activated.values_list("id", flat=True)))
        else:
            area_activated = ""
        initial_date = report.initial_date
        end_date = report.end_date
        description = report.description
        if report.funding_associated.exists():
            funding_associated = "; ".join(map(str, report.funding_associated.values_list("id", flat=True)))
        else:
            funding_associated = ""
        links = report.links.replace("\r\n", "; ")

        # Quantitative
        participants = report.participants
        donors = report.donors
        submissions = report.submissions
        # resources = report.resources
        feedbacks = report.feedbacks
        if report.editors.exists():
            editors_list = list(map(str, report.editors.values_list("id", flat=True)))
            editors = "; ".join(editors_list)
            num_editors = len(editors_list)
        else:
            editors = ""
            num_editors = 0
        if report.organizers.exists():
            organizers_list = list(map(str, report.organizers.values_list("id", flat=True)))
            organizers = "; ".join(organizers_list)
            num_organizers = len(organizers_list)
        else:
            organizers = ""
            num_organizers = 0
        if report.partners_activated.exists():
            partners_list = list(map(str, report.partners_activated.values_list("id", flat=True)))
            partners_activated = "; ".join(partners_list)
            num_partners_activated = len(partners_list)
        else:
            partners_activated = ""
            num_partners_activated = 0
        if report.technologies_used.exists():
            technologies_used = "; ".join(map(str, report.technologies_used.values_list("id", flat=True)))
        else:
            technologies_used = ""

        # Wikimedia
        wikipedia_created = report.wikipedia_created
        wikipedia_edited = report.wikipedia_edited
        commons_created = report.commons_created
        commons_edited = report.commons_edited
        wikidata_created = report.wikidata_created
        wikidata_edited = report.wikidata_edited
        wikiversity_created = report.wikiversity_created
        wikiversity_edited = report.wikiversity_edited
        wikibooks_created = report.wikibooks_created
        wikibooks_edited = report.wikibooks_edited
        wikisource_created = report.wikisource_created
        wikisource_edited = report.wikisource_edited
        wikinews_created = report.wikinews_created
        wikinews_edited = report.wikinews_edited
        wikiquote_created = report.wikiquote_created
        wikiquote_edited = report.wikiquote_edited
        wiktionary_created = report.wiktionary_created
        wiktionary_edited = report.wiktionary_edited
        wikivoyage_created = report.wikivoyage_created
        wikivoyage_edited = report.wikivoyage_edited
        wikispecies_created = report.wikispecies_created
        wikispecies_edited = report.wikispecies_edited
        metawiki_created = report.metawiki_created
        metawiki_edited = report.metawiki_edited
        mediawiki_created = report.mediawiki_created
        mediawiki_edited = report.mediawiki_edited
        wikifunctions_created = report.wikifunctions_created
        wikifunctions_edited = report.wikifunctions_edited
        incubator_created = report.incubator_created
        incubator_edited = report.incubator_edited

        # Strategy
        if report.directions_related.exists():
            directions_related = "; ".join(map(str, report.directions_related.values_list("id", flat=True)))
        else:
            directions_related = ""
        learning = report.learning.replace("\r\n", "\n")

        # Theory
        if report.learning_questions_related.exists():
            learning_questions_related = "; ".join(map(str, report.learning_questions_related.values_list("id", flat=True)))
        else:
            learning_questions_related = ""

        # Metrics
        if report.metrics_related.exists():
            metrics_related = "; ".join(map(str, report.metrics_related.values_list("id", flat=True)))
        else:
            metrics_related = ""

        rows.append([id_, created_by, created_at, modified_by, modified_at, activity_associated, partial_report,
                     activity_name, reference_text, area_responsible, area_activated, initial_date, end_date,
                     description, funding_associated, links, private_links, participants,
                     feedbacks, editors, num_editors, organizers, num_organizers, partners_activated,
                     num_partners_activated, technologies_used, donors, submissions, wikipedia_created,
                     wikipedia_edited, commons_created, commons_edited, wikidata_created, wikidata_edited,
                     wikiversity_created, wikiversity_edited, wikibooks_created, wikibooks_edited, wikisource_created,
                     wikisource_edited, wikinews_created, wikinews_edited, wikiquote_created, wikiquote_edited,
                     wiktionary_created, wiktionary_edited, wikivoyage_created, wikivoyage_edited, wikispecies_created,
                     wikispecies_edited, metawiki_created, metawiki_edited, mediawiki_created, mediawiki_edited,
                     wikifunctions_created, wikifunctions_edited, incubator_created, incubator_edited,
                     directions_related, learning, learning_questions_related, metrics_related])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)

    df[_('Created at')] = df[_('Created at')].dt.tz_localize(None)
    df[_('Modified at')] = df[_('Modified at')].dt.tz_localize(None)
    return df


def export_operation_report(report_id=None, custom_query=Q(), lang=""):
    header = [_('ID'), _('Report ID'), _('Metric ID'), _('Metric'), _('Number of people reached through social media'),
              _('Number of new followers'), _('Number of mentions'), _('Number of community communications'),
              _('Number of events'), _('Number of resources'), _('Number of partnerships activated'),
              _('Number of new partnerships')]

    if report_id:
        operation_reports = OperationReport.objects.filter(report_id=report_id)
    else:
        reports = Report.objects.filter(custom_query)
        operation_reports = OperationReport.objects.filter(report_id__in=reports.values_list("id", flat=True))

    metric_name_attr = f"text_{lang}" if lang == "en" else "text"

    rows = []
    for operation_report in operation_reports:
        rows.append([operation_report.id,
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
                     operation_report.number_of_new_partnerships])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_metrics(report_id=None, custom_query=Q()):
    header = [_('ID'), _('Metric'), _('Activity ID'), _('Activity'), _('Activity code'), _('Number of editors'),
              _('Number of participants'), _('Number of partnerships activated'), _('Number of feedbacks'),
              _('Number of events'),
              _('# Wikipedia created'), _('# Wikipedia edited'),
              _('# Commons created'), _('# Commons edited'),
              _('# Wikidata created'), _('# Wikidata edited'),
              _('# Wikiversity created'), _('# Wikiversity edited'),
              _('# Wikibooks created'), _('# Wikibooks edited'),
              _('# Wikisource created'), _('# Wikisource edited'),
              _('# Wikinews created'), _('# Wikinews edited'),
              _('# Wikiquote created'), _('# Wikiquote edited'),
              _('# Wiktionary created'), _('# Wiktionary edited'),
              _('# Wikivoyage created'), _('# Wikivoyage edited'),
              _('# Wikispecies created'), _('# Wikispecies edited'),
              _('# Metawiki created'), _('# Metawiki edited'),
              _('# MediaWiki created'), _('# MediaWiki edited'),
              _('# Wikifunctions created'), _('# Wikifunctions edited'),
              _('# Incubator created'), _('# Incubator edited')]

    if report_id:
        reports = Report.objects.filter(pk=report_id)
    else:
        reports = Report.objects.filter(custom_query)

    rows = []
    for report in reports:
        if report.activity_associated:
            for instance in report.activity_associated.metrics.all():
                rows.append([instance.id, instance.text, instance.activity_id, instance.activity.text,
                             instance.activity.code, instance.number_of_editors, instance.number_of_participants,
                             instance.number_of_partnerships_activated, instance.number_of_feedbacks,
                             instance.number_of_events,
                             instance.wikipedia_created, instance.wikipedia_edited, instance.commons_created,
                             instance.commons_edited, instance.wikidata_created, instance.wikidata_edited,
                             instance.wikiversity_created, instance.wikiversity_edited, instance.wikibooks_created,
                             instance.wikibooks_edited, instance.wikisource_created, instance.wikisource_edited,
                             instance.wikinews_created, instance.wikinews_edited, instance.wikiquote_created,
                             instance.wikiquote_edited, instance.wiktionary_created, instance.wiktionary_edited,
                             instance.wikivoyage_created, instance.wikivoyage_edited, instance.wikispecies_created,
                             instance.wikispecies_edited, instance.metawiki_created, instance.metawiki_edited,
                             instance.mediawiki_created, instance.mediawiki_edited, instance.wikifunctions_created,
                             instance.wikifunctions_edited, instance.incubator_created, instance.incubator_edited])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_user_profile(report_id=None, custom_query=Q()):
    header = [_('ID'), _('First name'), _('Last Name'), _('Username on Wiki (WMB)'), _('Username on Wiki'),
              _('Photograph'), _('Position'), _('Twitter'), _('Facebook'), _('Instagram'), _('Email'),
              _('Wikidata item'), _('LinkedIn'), _('Lattes'), _('Orcid'), _('Google_scholar')]

    if report_id:
        reports = Report.objects.filter(pk=report_id)
    else:
        reports = Report.objects.filter(custom_query)

    rows = []
    for report in reports:
        for instance in [report.created_by, report.modified_by]:
            rows.append([instance.id,
                         instance.user.first_name or "",
                         instance.user.last_name or "",
                         instance.professional_wiki_handle or "",
                         instance.personal_wiki_handle or "",
                         instance.photograph or "",
                         instance.user.position_history or "",
                         instance.twitter or "",
                         instance.facebook or "",
                         instance.instagram or "",
                         instance.user.email or "",
                         instance.wikidata_item or "",
                         instance.linkedin or "",
                         instance.lattes or "",
                         instance.orcid or "",
                         instance.google_scholar or ""])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_funding(report_id=None, custom_query=Q()):
    header = [_('ID'), _('Funding'), _('Value'), _('Project ID'), _('Project'), _('Active?'), _('Type of project')]

    if report_id:
        fundings = Funding.objects.filter(funding_associated=report_id)
    else:
        reports = Report.objects.filter(custom_query)
        fundings = Funding.objects.filter(funding_associated__in = reports.values_list("id", flat=True))

    rows = []
    for funding in fundings:
        type_of_funding = _("Ordinary")
        if funding.project.current_poa:
            type_of_funding = _("Current Plan of Activities")
        elif funding.project.main_funding:
            type_of_funding = _("Main funding")
        rows.append([funding.id,
                     funding.name,
                     funding.value,
                     funding.project_id,
                     funding.project.text,
                     funding.project.active_status,
                     type_of_funding])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_area_activated(report_id=None, custom_query=Q()):
    header = [_('ID'), _('Area activated')]

    if report_id:
        reports = Report.objects.filter(pk=report_id)
    else:
        reports = Report.objects.filter(custom_query)

    rows = []
    for report in reports:
        rows.append([report.area_responsible.id, report.area_responsible.text])
        for instance in report.area_activated.all():
            rows.append([instance.id, instance.text])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_directions_related(report_id=None, custom_query=Q()):
    header = [_('ID'), _('Direction related'), _('Strategic axis ID'), _('Strategic axis text')]

    if report_id:
        reports = Report.objects.filter(pk=report_id)
    else:
        reports = Report.objects.filter(custom_query)

    rows = []
    for report in reports:
        for instance in report.directions_related.all():
            rows.append([instance.id, instance.text, instance.strategic_axis_id, instance.strategic_axis.text])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_editors(report_id=None, custom_query=Q()):
    header = [_('ID'), _('Username'), _('Number of reports including this editor')]

    if report_id:
        reports = Report.objects.filter(pk=report_id)
    else:
        reports = Report.objects.filter(custom_query)

    rows = []
    for report in reports:
        for instance in report.editors.all():
            rows.append([instance.id, instance.username, instance.editors.count()])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_learning_questions_related(report_id=None, custom_query=Q()):
    header = [_('ID'), _('Learning question'), _('Learning area ID'), _('Learning area')]

    if report_id:
        reports = Report.objects.filter(pk=report_id)
    else:
        reports = Report.objects.filter(custom_query)

    rows = []
    for report in reports:
        for instance in report.learning_questions_related.all():
            rows.append([instance.id, instance.text, instance.learning_area_id, instance.learning_area.text])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_organizers(report_id=None, custom_query=Q()):
    header = [_('ID'), _("Organizer's name"), _("Organizer's institution ID"), _("Organizer institution's name"), _('Number of reports including this organizer')]

    if report_id:
        reports = Report.objects.filter(pk=report_id)
    else:
        reports = Report.objects.filter(custom_query)

    rows = []
    for report in reports:
        for instance in report.organizers.all():
            rows.append([instance.id, instance.name, ";".join(map(str, instance.institution.values_list("id", flat=True))), ";".join(map(str, instance.institution.values_list("name", flat=True))),instance.organizers.count()])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_partners_activated(report_id=None, custom_query=Q()):
    header = [_('ID'), _("Partners"), _("Partner's website"), _('Number of reports including this partner')]

    if report_id:
        reports = Report.objects.filter(pk=report_id)
    else:
        reports = Report.objects.filter(custom_query)

    rows = []
    for report in reports:
        for instance in report.partners_activated.all():
            rows.append([instance.id, instance.name, instance.website, instance.partners.count()])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


def export_technologies_used(report_id=None, custom_query=Q()):
    header = [_('ID'), _("Technology"), _('Number of reports including this technology')]

    if report_id:
        reports = Report.objects.filter(pk=report_id)
    else:
        reports = Report.objects.filter(custom_query)

    rows = []
    for report in reports:
        for instance in report.technologies_used.all():
            rows.append([instance.id, instance.name, instance.technologies.count()])

    df = pd.DataFrame(rows, columns=header).drop_duplicates().reset_index(drop=True)
    return df


# ======================================================================================================================
# UPDATE
# ======================================================================================================================
@login_required
@permission_required("report.change_report")
def update_report(request, report_id):
    report = get_object_or_404(Report, id=report_id)

    if report.locked and not request.user.has_perm("report.can_edit_locked_report"):
        messages.error(request, _("You do not have permission to edit this report. Please, share the link with the Products and Technology team for any questions."))
        return redirect(reverse("report:detail_report", kwargs={"report_id": report_id}))

    if request.method == "POST":
        report_form = NewReportForm(request.POST, instance=report, user=request.user, is_update=True)
        operation_metrics = OperationUpdateFormSet(request.POST, instance=report, prefix='Operation')
        if report_form.is_valid() and operation_metrics.is_valid():
            with transaction.atomic():
                report = report_form.save(user=request.user)

                operation_metrics.save()

            messages.success(request, _("Report updated successfully!"))
            return redirect(reverse("report:detail_report", kwargs={"report_id": report.id}))
    else:
        report_form = NewReportForm(instance=report, user=request.user, is_update=True)
        operation_metrics = OperationUpdateFormSet(prefix="Operation", instance=report)

    context = {"report_form": report_form,
               "report_id": report.id,
               "operation_metrics": operation_metrics,
               "directions_related_set": list(report.directions_related.values_list("id", flat=True)),
               "learning_questions_related_set": list(report.learning_questions_related.values_list("id", flat=True)),
               "metrics_set": list(report.metrics_related.values_list("id", flat=True)),
               "title": _("Edit report %(report_id)s") % {"report_id": report.id},
               }

    return render(request, "report/update_report.html", context)


# ======================================================================================================================
# DELETE
# ======================================================================================================================
@login_required
@permission_required("report.delete_report")
def delete_report(request, report_id):
    report = Report.objects.get(id=report_id)
    context = {"report": report,
               "title": _("Delete report %(report_id)s") % {"report_id": report_id}}

    if request.method == "POST":
        report.delete()
        return redirect(reverse('report:list_reports'))

    return render(request, 'report/delete_report.html', context)


# ======================================================================================================================
# FUNCTIONS
# ======================================================================================================================
def get_metrics(request):
    projects = []
    main_ = False
    user_lang = translation.get_language()

    # ACTIVITY
    activity = request.GET.get("activity")
    if activity and activity != "1":
        activity_project = Project.objects.get(project_activity__activities=int(activity), active_status=True)
        metrics = Metric.objects.filter(activity_id=activity).values()
        main_ = Activity.objects.get(pk=int(activity)).is_main_activity
        projects.append({"project": activity_project.text, "metrics": list(metrics), "main": main_, "lang": user_lang})
    elif activity == "1":
        for project in Project.objects.filter(active_status=True).exclude(current_poa=True):
            metrics = Metric.objects.filter(project=project).values()
            if metrics:
                projects.append({"project": project.text, "metrics": list(metrics), "lang": user_lang})

    # FUNDINGS
    fundings_ids = request.GET.getlist("fundings[]")
    projects_ids = Project.objects.filter(Q(project_related__in=fundings_ids))
    for project in projects_ids:
        metrics = Metric.objects.filter(project=project).values().order_by('text')
        projects.append({"project": project.text, "metrics": list(metrics), "lang": user_lang})

    # INSTANCE
    instance = request.GET.get("instance")
    if instance:
        report = Report.objects.get(pk=instance)
        metrics_ids = [metric["id"] for project in projects for metric in project["metrics"]]
        metrics_aux = report.metrics_related.all().values()
        metrics = [metric for metric in metrics_aux if metric["id"] not in metrics_ids]
        main_ = report.activity_associated.is_main_activity

        if metrics:
            projects.append({"project": _("Other metrics"), "metrics": list(metrics), "lang": user_lang})

    if projects:
        return JsonResponse({"objects": projects, "main": main_})
    else:
        return JsonResponse({"objects": None, "main": main_})
