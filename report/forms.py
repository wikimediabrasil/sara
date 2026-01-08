from venv import create

from django.utils import timezone
from django import forms
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.core.exceptions import FieldDoesNotExist
from django.db.models import fields, Q, Case, When, Value, IntegerField
from django.db.models.functions import Lower
from report.models import Report, Funding, Partner, Technology, Editor, Organizer, OperationReport
from metrics.models import Area, Metric, Project
from strategy.models import StrategicAxis, LearningArea
from users.models import TeamArea, UserProfile

from urllib.parse import quote
import requests
from datetime import datetime
from django.forms import inlineformset_factory


class NewReportForm(forms.ModelForm):
    editors_string = forms.CharField(required=False, widget=forms.Textarea,)
    organizers_string = forms.CharField(required=False, widget=forms.Textarea,)

    class Meta:
        model = Report
        fields = "__all__"
        exclude = ["created_by", "created_at", "modified_by", "modified_at"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.is_update = kwargs.pop("is_update", False)
        super().__init__(*args, **kwargs)

        self.fields["activity_associated"].choices = activities_associated_as_choices()
        self.fields["directions_related"].choices = directions_associated_as_choices()
        self.fields["learning_questions_related"].choices = learning_questions_as_choices()

        self.fields["area_responsible"].queryset = TeamArea.objects.order_by(Lower("text"))
        self.fields["area_activated"].queryset = TeamArea.objects.order_by(Lower("text"))
        self.fields["partners_activated"].queryset = Partner.objects.order_by(Lower("name"))
        self.fields["technologies_used"].queryset = Technology.objects.order_by(Lower("name"))

        self.fields["funding_associated"].queryset = Funding.objects.filter(project__active_status=True).order_by(Lower("name"))

        if self.instance.pk:
            self.fields["area_responsible"].initial = self.instance.area_responsible_id
        else:
            self.fields["area_responsible"].initial = area_responsible_of_user(self.user)

    def clean(self):
        cleaned = super().clean()

        raw_editors = cleaned.get("editors_string", "")
        editors = [
            u.strip()
            for u in remove_domain(raw_editors).splitlines()
            if u.strip()
        ]
        cleaned["_parsed_editors"] = list(set(editors))

        raw_organizers = cleaned.get("organizers_string", "")
        organizers = []
        inferred_partners = set()

        for line in raw_organizers.splitlines():
            if not line.strip():
                continue

            name, institutions = (line + "|").split("|", 1)
            organizers.append(line.strip())

            for institution in institutions.split("|"):
                if institution.strip():
                    inferred_partners.add(institution.strip())

        cleaned["_parsed_organizers"] = list(set(organizers))
        cleaned["_inferred_partner_names"] = list(inferred_partners)

        return cleaned

    def clean_end_date(self):
        initial_date = self.cleaned_data.get('initial_date')
        end_date = self.cleaned_data.get('end_date')

        if end_date:
            return end_date
        else:
            return initial_date

    def add_metrics_related_depending_on_values(self):
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
            ["participants"],
            ["feedbacks"],
        ]

        for field_set in int_fields_names:
            if any(self.cleaned_data.get(field_name) > 0 for field_name in field_set):
                query = Q()
                for field_name in field_set:
                    if hasattr(Metric, f"{field_name}"):
                        query |= Q(**{f"{field_name}__gt": 0})
                    else:
                        query |= Q(**{f"number_of_{field_name}__gt": 0})
                if len(query):
                    metrics_related = metrics_related.union(metrics_main_funding.filter(query))

        obj_fields_names = {
            "editors": ["number_of_editors", "number_of_editors_retained", "number_of_new_editors"],
            "organizers": ["number_of_organizers", "number_of_organizers_retained"],
            "partners_activated": ["number_of_partnerships_activated"],
        }

        for field_set, field_names in obj_fields_names.items():
            if self.cleaned_data.get(field_set):
                query = Q()
                for field_name in field_names:
                    query |= Q(**{f"{field_name}__gt": 0})
                if len(query):
                    metrics_related = metrics_related.union(metrics_main_funding.filter(query))

        return metrics_related

    def save(self, commit=True, user=None, *args, **kwargs):
        report = super(NewReportForm, self).save(commit=False)

        if commit:
            user_profile = get_object_or_404(UserProfile, user=user)
            report.created_by = user_profile
            report.modified_by = user_profile
            report.save()

            self._save_editors(report)
            self._save_organizers(report)
            self._save_partners(report)

            report.technologies_used.set(self.cleaned_data['technologies_used'])
            report.area_activated.set(self.cleaned_data['area_activated'])
            report.directions_related.set(self.cleaned_data['directions_related'])
            report.learning_questions_related.set(self.cleaned_data['learning_questions_related'])

            metrics = self._metrics_related() or []
            report.metrics_related.set(metrics)

        return report

    def _save_editors(self, report):
        editors = []
        for username in self.cleaned_data["_parsed_editors"]:
            editor, created = Editor.objects.get_or_create(username=username)

            if created:
                editor.account_creation_date = get_user_date_of_registration(username)
            elif not self.is_update:
                editor.retained = True
                editor.retained_at = self.cleaned_data["initial_date"]

            editor.save()
            editors.append(editor)

        report.editors.set(editors)

    def _save_organizers(self, report):
        organizers = {}
        created_in_this_save = set()

        for line in self.cleaned_data["_parsed_organizers"]:
            name, institutions = (line + "|").split("|", 1)
            key = name.strip().lower()

            organizer, created = Organizer.objects.get_or_create(name=name.strip())

            if created:
                organizer.first_seen_at = timezone.now().date()
                organizer.save()
                created_in_this_save.add(organizer.id)
            elif not self.is_update and organizer.id not in created_in_this_save:
                organizer.retained = True
                organizer.retained_at = self.cleaned_data["initial_date"]
                organizer.save()

            for inst_name in institutions.split("|"):
                if inst_name.strip():
                    partner, _ = Partner.objects.get_or_create(name=inst_name.strip())
                    organizer.institution.add(partner)

            organizers[key] = organizer

        report.organizers.set(organizers.values())

    def _save_partners(self, report):
        partners = {p.id: p for p in list(Partner.objects.filter(id__in=self.cleaned_data["partners_activated"]))}

        for name in self.cleaned_data["_inferred_partner_names"]:
            partner, _ = Partner.objects.get_or_create(name=name)
            partners[partner.id] = partner

        report.partners_activated.set(partners.values())

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
            ["participants"],
            ["feedbacks"],
        ]

        for field_set in int_fields_names:
            if any(self.cleaned_data.get(field_name, 0) > 0 for field_name in field_set):
                query = Q()
                for field in field_set:
                    try:
                        Metric._meta.get_field(field)
                        metric_field= field
                    except FieldDoesNotExist:
                        metric_field = f"number_of_{field}"

                    query |= Q(**{f"{metric_field}__gt": 0})

                metrics_related = metrics_related.union(metrics_main_funding.filter(query))

        obj_fields_names = {
            "editors": ["number_of_editors", "number_of_editors_retained", "number_of_new_editors"],
            "organizers": ["number_of_organizers", "number_of_organizers_retained"],
            "partners_activated": ["number_of_partnerships_activated"],
        }

        for field_set, field_names in obj_fields_names.items():
            if self.cleaned_data.get(field_set):
                query = Q()
                for field_name in field_names:
                    query |= Q(**{f"{field_name}__gt": 0})

                metrics_related = metrics_related.union(metrics_main_funding.filter(query))

        return metrics_related


def remove_domain(users_string):
    user_domains = ["User:", "Usuário (a):", "Usuário:", "Usuária:", "Utilizador(a):", "Utilizadora:", "Utilizador:"]
    for domain in user_domains:
        users_string = users_string.replace(domain, "")
    return users_string


def area_responsible_of_user(user):
    try:
        team_area = user.profile.position.area_associated
        return team_area.id
    except TeamArea.DoesNotExist:
        return ""


def activities_associated_as_choices():
    areas = []
    area_list = Area.objects.filter(project__active_status=True).distinct().order_by("-poa_area", "text")
    for area in area_list:
        activities = []
        for activity in area.activities.all():
            activities.append((activity.id, activity.text + " (" + activity.code + ")"))
        areas.append((area.text, int(area.poa_area), tuple(activities)))
    return tuple(areas)


def directions_associated_as_choices():
    axes = []
    for axis in StrategicAxis.objects.filter(active=True).distinct():
        directions = []
        for direction in axis.directions.all():
            directions.append((direction.id, direction.text))
        axes.append((axis.text, tuple(directions)))

    return tuple(axes)


def learning_questions_as_choices():
    learning_areas = []
    for learning_area in LearningArea.objects.filter(active=True).distinct():
        learning_questions = []
        for learning_question in learning_area.strategic_question.all():
            learning_questions.append((learning_question.id, learning_question.text))
        learning_areas.append((learning_area.text, tuple(learning_questions)))

    return tuple(learning_areas)


def learning_areas_as_choices():
    areas = []
    for area in LearningArea.objects.all():
        new_category = []
        questions = []
        for question in area.strategic_question.all():
            questions.append([question.id, question.text])
            new_category = [area.text, questions]
        areas.append(new_category)

    return areas


def get_user_date_of_registration(user):
    headers = {"User-Agent": "SARA-WMB/Toolforge (contact: User:EPorto (WMB) / mailto: eder.porto@wmnobrasil.org) environment=toolforge"}
    url = "https://www.mediawiki.org/w/api.php?action=query&meta=globaluserinfo&format=json&guiuser=" + quote(user, safe="")
    result = requests.get(url, headers=headers)
    data = result.json()
    try:
        date_obj = datetime.strptime(data["query"]["globaluserinfo"]["registration"], "%Y-%m-%dT%H:%M:%SZ")
        date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        return date_str
    except:
        return None


class OperationForm(forms.ModelForm):
    class Meta:
        model = OperationReport
        fields = "__all__"

    def clean_number_of_people_reached_through_social_media(self):
        number_of_people_reached_through_social_media = self.cleaned_data.get("number_of_people_reached_through_social_media", 0)
        return number_of_people_reached_through_social_media if number_of_people_reached_through_social_media else 0
    def clean_number_of_new_followers(self):
        number_of_new_followers = self.cleaned_data.get("number_of_new_followers", 0)
        return number_of_new_followers if number_of_new_followers else 0
    def clean_number_of_mentions(self):
        number_of_mentions = self.cleaned_data.get("number_of_mentions", 0)
        return number_of_mentions if number_of_mentions else 0
    def clean_number_of_community_communications(self):
        number_of_community_communications = self.cleaned_data.get("number_of_community_communications", 0)
        return number_of_community_communications if number_of_community_communications else 0
    def clean_number_of_events(self):
        number_of_events = self.cleaned_data.get("number_of_events", 0)
        return number_of_events if number_of_events else 0
    def clean_number_of_resources(self):
        number_of_resources = self.cleaned_data.get("number_of_resources", 0)
        return number_of_resources if number_of_resources else 0
    def clean_number_of_partnerships_activated(self):
        number_of_partnerships_activated = self.cleaned_data.get("number_of_partnerships_activated", 0)
        return number_of_partnerships_activated if number_of_partnerships_activated else 0
    def clean_number_of_new_partnerships(self):
        number_of_new_partnerships = self.cleaned_data.get("number_of_new_partnerships", 0)
        return number_of_new_partnerships if number_of_new_partnerships else 0


OperationUpdateFormSet = inlineformset_factory(
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
            'number_of_new_partnerships'), extra=0,
    can_delete=False)