import datetime
from django.conf import settings
from django.db import transaction
from django.forms import inlineformset_factory
from django.utils import timezone
from django.utils.translation import gettext as _

from metrics.models import Metric
from report.forms import OperationForm
from report.models import OperationReport, Report


def create_report(report_form, operation_metrics, user):
    """Validate-and-save path for a submitted report. Returns the saved
    Report, or raises ValueError if a duplicate was submitted recently."""
    description = report_form.cleaned_data.get("description")

    with transaction.atomic():
        if _report_already_submitted(user, description):
            raise ValueError(_("Report already exists!"))

        report = report_form.save(user=user)
        related_metrics = _save_operation_instances(operation_metrics, report)

        if related_metrics:
            report.metrics_related.add(*related_metrics)

    return report


def get_operation_formset():
    return inlineformset_factory(
        Report,
        OperationReport,
        form=OperationForm,
        fields=(
            "metric",
            "number_of_people_reached_through_social_media",
            "number_of_new_followers",
            "number_of_mentions",
            "number_of_community_communications",
            "number_of_events",
            "number_of_resources",
            "number_of_partnerships_activated",
            "number_of_new_partnerships",
        ),
        extra=Metric.objects.filter(is_operation=True).count(),
        can_delete=False,
    )


# ======================================================================================================================
# FUNCTIONS
# ======================================================================================================================
def _get_localized_field(lang, available_fields, default_field="text"):
    """
    Returns the name of the text field for the requested language.
    Uses the fallbacks defined in settings.LANGUAGE_FALLBACKS.

    :param lang: received language code (e.g., "en_GB")
    :param available_fields: list of available fields in the model
    :param default_field: generic field if none match

    :return: name of the field to be used
    """
    raw_lang = lang.lower().replace("-", "_")

    # Exact field
    exact_field = f"{default_field}_{raw_lang}"
    if exact_field in available_fields:
        return exact_field

    # Fallback
    fallback_list = getattr(settings, "LANGUAGE_FALLBACKS", {}).get(raw_lang, [])
    for fallback_lang in fallback_list:
        fallback_field = f"text_{fallback_lang.lower().replace('-', '_')}"
        if fallback_field in available_fields:
            return fallback_field

    # Generic fallback
    if default_field in available_fields:
        return default_field
    else:
        return None


def _report_already_submitted(user, description):
    timediff = timezone.now() - datetime.timedelta(hours=24)
    return Report.objects.filter(
        created_by__user=user,
        description=description,
        created_at__gte=timediff,
    ).exists()


def _save_operation_instances(operation_metrics, report):
    """Save each operation instance against the report and return the
    metrics that should be marked as related, based on nonzero fields."""
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

    related_metrics = []
    for instance in operation_metrics.save(commit=False):
        instance.report = report
        instance.save()

        if any(getattr(instance, field, 0) > 0 for field in numeric_fields):
            related_metrics.append(instance.metric)

    return related_metrics


def _joined_ids(queryset):
    """Turn a related query set's ids into a '; '-joined string, or '' if empty."""
    return "; ".join(map(str, queryset.values_list("id", flat=True)))


def _joined_ids_and_count(queryset):
    """Same as _joined_ids, but also returns how many ids there were."""
    ids = list(map(str, queryset.values_list("id", flat=True)))
    return "; ".join(ids), len(ids)