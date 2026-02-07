from datetime import datetime
from urllib.parse import quote

import requests
from django import forms
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from django.db.models.functions import Lower
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404
from django.utils import timezone

from metrics.models import Area, Metric, Project
from report.models import (
    Editor,
    Funding,
    OperationReport,
    Organizer,
    Partner,
    Report,
    Technology,
)
from strategy.models import LearningArea, StrategicAxis
from users.models import TeamArea, UserProfile


class NewReportForm(forms.ModelForm):
    editors_string = forms.CharField(
        required=False,
        widget=forms.Textarea,
    )
    organizers_string = forms.CharField(
        required=False,
        widget=forms.Textarea,
    )

    class Meta:
        model = Report
        fields = "__all__"
        exclude = ["created_by", "created_at", "modified_by", "modified_at"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.is_update = kwargs.pop("is_update", False)
        super().__init__(*args, **kwargs)

        self.fields["activity_associated"].choices = activities_associated_as_choices()
        self.fields["directions_related"].choices = directions_associated_as_choices()
        self.fields["learning_questions_related"].choices = (
            learning_questions_as_choices()
        )

        self.fields["area_responsible"].queryset = TeamArea.objects.order_by(
            Lower("text")
        )
        self.fields["area_activated"].queryset = TeamArea.objects.order_by(
            Lower("text")
        )
        self.fields["partners_activated"].queryset = Partner.objects.order_by(
            Lower("name")
        )
        self.fields["technologies_used"].queryset = Technology.objects.order_by(
            Lower("name")
        )

        self.fields["funding_associated"].queryset = Funding.objects.filter(
            project__active_status=True
        ).order_by(Lower("name"))

        if self.instance.pk:
            self.fields["area_responsible"].initial = self.instance.area_responsible_id
        else:
            self.fields["area_responsible"].initial = area_responsible_of_user(
                self.user
            )

    def clean(self):
        cleaned = super().clean()

        raw_editors = cleaned.get("editors_string", "")
        editors = [
            u.strip() for u in remove_domain(raw_editors).splitlines() if u.strip()
        ]
        cleaned["_parsed_editors"] = list(set(editors))

        raw_organizers = cleaned.get("organizers_string", "")

        parsed_organizers = []
        for line in raw_organizers.splitlines():
            if not line.strip():
                continue

            name, institutions = (line + "|").split("|", 1)
            parsed_organizers.append(
                {
                    "name": name.strip(),
                    "institutions": [
                        inst.strip() for inst in institutions.split("|") if inst.strip()
                    ],
                }
            )

        cleaned["_parsed_organizers"] = parsed_organizers

        return cleaned

    def clean_end_date(self):
        initial_date = self.cleaned_data.get("initial_date")
        end_date = self.cleaned_data.get("end_date")

        if end_date:
            return end_date
        else:
            return initial_date

    def save(self, commit=True, user=None, *args, **kwargs):
        report = super(NewReportForm, self).save(commit=False)

        if commit:
            user_profile = get_object_or_404(UserProfile, user=user)
            report.created_by = user_profile
            report.modified_by = user_profile
            report.save()

            self._save_editors(report)
            self._save_organizers(report)

            report.technologies_used.set(self.cleaned_data["technologies_used"])
            report.area_activated.set(self.cleaned_data["area_activated"])
            report.directions_related.set(self.cleaned_data["directions_related"])
            report.learning_questions_related.set(
                self.cleaned_data["learning_questions_related"]
            )

            metrics = self._metrics_related()
            metrics = self._apply_implicit_metrics(report, metrics)
            report.metrics_related.set(metrics)

        return report

    def _save_editors(self, report):
        editors = []
        self._has_editors = False
        self._has_new_editors = False
        self._has_retained_editors = False

        for username in self.cleaned_data["_parsed_editors"]:
            editor, created = Editor.objects.get_or_create(username=username)

            if created:
                editor.account_creation_date = get_user_date_of_registration(username)
                self._has_editors = True
                if editor.first_seen_at.date() >= report.initial_date:
                    self._has_new_editors = True
            elif not self.is_update:
                editor.retained = True
                editor.retained_at = self.cleaned_data["initial_date"]
                self._has_retained_editors = True

            editor.save()
            editors.append(editor)

        report.editors.set(editors)

    def _save_organizers(self, report):
        organizers = {}
        created_in_this_save = set()

        self._has_organizers = False
        self._has_retained_organizers = False
        self._has_new_organizers = False

        for entry in self.cleaned_data["_parsed_organizers"]:
            name = entry["name"]
            institutions = entry["institutions"]

            key = name.lower()

            organizer, created = Organizer.objects.get_or_create(name=name)

            if created:
                organizer.first_seen_at = timezone.now().date()
                organizer.save()
                created_in_this_save.add(organizer.id)
                self._has_organizers = True

                if organizer.first_seen_at >= report.initial_date:
                    self._has_new_organizers = True

            elif not self.is_update and organizer.id not in created_in_this_save:
                organizer.retained = True
                organizer.retained_at = self.cleaned_data["initial_date"]
                organizer.save()
                self._has_retained_organizers = True

            for inst_name in institutions:
                if inst_name.strip():
                    partner, _ = Partner.objects.get_or_create(name=inst_name)
                    organizer.institution.add(partner)

            organizers[key] = organizer

        report.organizers.set(organizers.values())

    def _metrics_related(self):
        metrics_related = self.cleaned_data.get("metrics_related")
        main_funding = Project.objects.get(main_funding=True)
        metrics_main_funding = Metric.objects.filter(project=main_funding)

        int_fields_names = [
            ["wikipedia_created", "wikipedia_edited"],
            ["commons_created", "commons_edited"],
            ["wikidata_created", "wikidata_edited"],
            ["wikiversity_created", "wikiversity_edited"],
            ["wikibooks_created", "wikibooks_edited"],
            ["wikisource_created", "wikisource_edited"],
            ["wikinews_created", "wikinews_edited"],
            ["wikiquote_created", "wikiquote_edited"],
            ["wiktionary_created", "wiktionary_edited"],
            ["wikivoyage_created", "wikivoyage_edited"],
            ["wikispecies_created", "wikispecies_edited"],
            ["metawiki_created", "metawiki_edited"],
            ["mediawiki_created", "mediawiki_edited"],
            ["wikifunctions_created", "wikifunctions_edited"],
            ["incubator_created", "incubator_edited"],
            ["participants"],
            ["feedbacks"],
        ]

        for field_set in int_fields_names:
            if any(
                self.cleaned_data.get(field_name, 0) > 0 for field_name in field_set
            ):
                query = Q()
                for field in field_set:
                    try:
                        Metric._meta.get_field(field)
                        metric_field = field
                    except FieldDoesNotExist:
                        metric_field = f"number_of_{field}"

                    query |= Q(**{f"{metric_field}__gt": 0})

                metrics_related = metrics_related.union(
                    metrics_main_funding.filter(query)
                )

        obj_fields_names = {
            "editors": [
                "number_of_editors",
                "number_of_editors_retained",
                "number_of_new_editors",
            ],
            "organizers": ["number_of_organizers", "number_of_organizers_retained"],
            "partners_activated": ["number_of_partnerships_activated"],
        }

        for field_set, field_names in obj_fields_names.items():
            if self.cleaned_data.get(field_set):
                query = Q()
                for field_name in field_names:
                    query |= Q(**{f"{field_name}__gt": 0})

                metrics_related = metrics_related.union(
                    metrics_main_funding.filter(query)
                )

        return metrics_related

    @staticmethod
    def _contributes_to_main_funding(report):
        if not report.activity_associated or not report.activity_associated.area:
            return False
        return report.activity_associated.area.project.filter(
            counts_for_main_funding=True
        ).exists()

    def _apply_implicit_metrics(self, report, metrics):
        if not self._contributes_to_main_funding(report):
            return metrics

        main_funding = Project.objects.get(main_funding=True)

        if getattr(self, "_has_editors", False):
            metrics = metrics.union(
                Metric.objects.filter(project=main_funding, number_of_editors__gt=0)
            )
        if getattr(self, "_has_new_editors", False):
            metrics = metrics.union(
                Metric.objects.filter(project=main_funding, number_of_new_editors__gt=0)
            )
        if getattr(self, "_has_retained_editors", False):
            metrics = metrics.union(
                Metric.objects.filter(
                    project=main_funding, number_of_editors_retained__gt=0
                )
            )
        if getattr(self, "_has_organizers", False):
            metrics = metrics.union(
                Metric.objects.filter(project=main_funding, number_of_organizers__gt=0)
            )
        if getattr(self, "_has_new_organizers", False):
            metrics = metrics.union(
                Metric.objects.filter(
                    project=main_funding, number_of_new_organizers__gt=0
                )
            )
        if getattr(self, "_has_retained_organizers", False):
            metrics = metrics.union(
                Metric.objects.filter(
                    project=main_funding, number_of_organizers_retained__gt=0
                )
            )

        return metrics


def remove_domain(users_string):
    user_domains = [
        "User:",
        "Usuário (a):",
        "Usuário:",
        "Usuária:",
        "Utilizador(a):",
        "Utilizadora:",
        "Utilizador:",
    ]
    for domain in user_domains:
        users_string = users_string.replace(domain, "")
    return users_string


def area_responsible_of_user(user):
    try:
        team_area = user.profile.position.area_associated
        return team_area.id
    except (TeamArea.DoesNotExist, AttributeError):
        return ""


def activities_associated_as_choices():
    areas = []
    area_list = (
        Area.objects.filter(project__active_status=True)
        .prefetch_related("activities")
        .distinct()
        .order_by("-poa_area", "text")
    )

    for area in area_list:
        activities = [(a.id, f"{a.text} ({a.code})") for a in area.activities.all()]
        areas.append((area.text, int(area.poa_area), tuple(activities)))

    return tuple(areas)


def directions_associated_as_choices():
    axes = []
    axes_qs = (
        StrategicAxis.objects.filter(active=True)
        .prefetch_related("directions")
        .distinct()
    )
    for axis in axes_qs:
        directions = [(d.id, d.text) for d in axis.directions.all()]
        axes.append((axis.text, tuple(directions)))

    return tuple(axes)


def learning_questions_as_choices():
    learning_areas = []

    learning_areas_qs = (
        LearningArea.objects.filter(active=True)
        .prefetch_related("strategic_question")
        .distinct()
    )

    for learning_area in learning_areas_qs:
        learning_questions = [
            (learning.id, learning.text)
            for learning in learning_area.strategic_question.all()
        ]
        learning_areas.append((learning_area.text, tuple(learning_questions)))

    return tuple(learning_areas)


def get_user_date_of_registration(user):
    headers = {
        "User-Agent": "SARA-WMB/Toolforge (contact: User:EPorto (WMB) / mailto: eder.porto@wmnobrasil.org) environment=toolforge"
    }
    url = (
        "https://www.mediawiki.org/w/api.php?action=query&meta=globaluserinfo&format=json&guiuser="
        + quote(user, safe="")
    )
    result = requests.get(url, headers=headers)
    data = result.json()
    try:
        date_obj = datetime.strptime(
            data["query"]["globaluserinfo"]["registration"], "%Y-%m-%dT%H:%M:%SZ"
        )
        date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        return date_str
    except (KeyError, TypeError, ValueError):
        return None


class OperationForm(forms.ModelForm):
    class Meta:
        model = OperationReport
        fields = "__all__"

    def clean_number_of_people_reached_through_social_media(self):
        number_of_people_reached_through_social_media = self.cleaned_data.get(
            "number_of_people_reached_through_social_media", 0
        )
        return (
            number_of_people_reached_through_social_media
            if number_of_people_reached_through_social_media
            else 0
        )

    def clean_number_of_new_followers(self):
        number_of_new_followers = self.cleaned_data.get("number_of_new_followers", 0)
        return number_of_new_followers if number_of_new_followers else 0

    def clean_number_of_mentions(self):
        number_of_mentions = self.cleaned_data.get("number_of_mentions", 0)
        return number_of_mentions if number_of_mentions else 0

    def clean_number_of_community_communications(self):
        number_of_community_communications = self.cleaned_data.get(
            "number_of_community_communications", 0
        )
        return (
            number_of_community_communications
            if number_of_community_communications
            else 0
        )

    def clean_number_of_events(self):
        number_of_events = self.cleaned_data.get("number_of_events", 0)
        return number_of_events if number_of_events else 0

    def clean_number_of_resources(self):
        number_of_resources = self.cleaned_data.get("number_of_resources", 0)
        return number_of_resources if number_of_resources else 0

    def clean_number_of_partnerships_activated(self):
        number_of_partnerships_activated = self.cleaned_data.get(
            "number_of_partnerships_activated", 0
        )
        return (
            number_of_partnerships_activated if number_of_partnerships_activated else 0
        )

    def clean_number_of_new_partnerships(self):
        number_of_new_partnerships = self.cleaned_data.get(
            "number_of_new_partnerships", 0
        )
        return number_of_new_partnerships if number_of_new_partnerships else 0


OperationUpdateFormSet = inlineformset_factory(
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
    extra=0,
    can_delete=False,
)
