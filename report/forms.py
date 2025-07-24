from django.utils import timezone
from django import forms
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.db.models import fields, Q
from django.db.models.functions import Lower
from .models import Report, StrategicLearningQuestion, LearningArea, AreaActivated, Funding, Partner, Technology,\
    Editor, Organizer, OperationReport
from metrics.models import Area, Metric, Project
from strategy.models import StrategicAxis
from users.models import TeamArea, UserProfile

from urllib.parse import quote
import requests
from datetime import datetime
from django.forms import inlineformset_factory


class NewReportForm(forms.ModelForm):
    is_update = False

    class Meta:
        model = Report
        fields = "__all__"
        exclude = ["created_by", "created_at", "modified_by", "modified_at"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        self.is_update = kwargs.pop("is_update", False)
        super(NewReportForm, self).__init__(*args, **kwargs)
        self.fields["activity_associated"].choices = activities_associated_as_choices()
        self.fields["directions_related"].choices = directions_associated_as_choices()
        self.fields["learning_questions_related"].choices = learning_questions_as_choices()
        self.fields["area_responsible"].queryset = TeamArea.objects.order_by(Lower("text"))
        self.fields["funding_associated"].queryset = Funding.objects.filter(project__active=True).order_by(Lower("name"))
        self.fields["area_activated"].queryset = AreaActivated.objects.order_by(Lower("text"))
        self.fields["partners_activated"].queryset = Partner.objects.order_by(Lower("name"))
        if self.instance.id:
            self.fields["area_responsible"].initial = self.instance.area_responsible_id
        else:
            self.fields["area_responsible"].initial = area_responsible_of_user(user)
        self.fields["technologies_used"].queryset = Technology.objects.order_by(Lower("name"))

    def clean_editors(self):
        editors_string = self.data.get("editors_string", "")
        editors_list = remove_domain(editors_string).split("\r\n") if editors_string else []
        editors = []
        for editor in editors_list:
            editor_object, created = Editor.objects.get_or_create(username=editor)

            # Store the editor account date of registration
            if created:
                user_creation_date = get_user_date_of_registration(editor)
                if user_creation_date:
                    editor_object.account_creation_date = user_creation_date
            # Which means that the user is already on the database and is returning = retained
            else:
                if not self.is_update:
                    editor_object.retained = 1
                    editor_object.retained_at = datetime.today().date()

            editor_object.save()
            editors.append(editor_object)
        return editors

    def clean_organizers(self):
        organizers_string = self.data.get("organizers_string", "")
        organizers_list = remove_domain(organizers_string).split("\r\n") if organizers_string else []
        organizers = []
        for organizer in organizers_list:
            organizer_name, institution_name = (organizer + ";").split(";", maxsplit=1)
            organizer_object, created = Organizer.objects.get_or_create(name=organizer_name.strip())
            if not created and not self.is_update:
                organizer_object.retained = True
                organizer_object.save()
            if institution_name:
                for partner_name in institution_name.split(";"):
                    if partner_name:
                        partner, partner_created = Partner.objects.get_or_create(name=partner_name.strip())
                        organizer_object.institution.add(partner)
                organizer_object.save()
            organizers.append(organizer_object)
        return organizers

    def clean_partners_activated(self):
        organizers_string = self.data.get("organizers_string", "")
        organizers_list = organizers_string.split("\r\n") if organizers_string else []

        partners = self.data.getlist("partners_activated", []) if "partners_activated" in self.data else []
        for organizer in organizers_list:
            organizer_name, institution_name = (organizer + ";").split(";", maxsplit=1)
            if institution_name:
                for partner_name in institution_name.split(";"):
                    if partner_name:
                        partner, partner_created = Partner.objects.get_or_create(name=partner_name.strip())
                        partners.append(partner.id)
        return partners

    def clean_initial_date(self):
        initial_date = self.cleaned_data.get('initial_date')
        return initial_date

    def clean_metrics_related(self):
        metrics_related = self.cleaned_data.get('metrics_related')
        main_funding = Project.objects.get(main_funding=True)
        metrics_main_funding = Metric.objects.filter(project=main_funding)
        for metric in metrics_related:
            field_names = [metric_field.name for metric_field in metric._meta.fields if isinstance(metric_field, fields.IntegerField) and metric_field.name != "id" and getattr(metric, metric_field.name) > 0]

            # Check if the metrics of the main funding have values
            query = Q()
            for field_name in field_names:
                query |= Q(**{f"{field_name}__gt": 0})

            if len(query):
                metrics_related = metrics_related.union(metrics_main_funding.filter(query))
        return metrics_related

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
            report.editors.clear()
            report.organizers.clear()
            report.editors.set(self.cleaned_data['editors'])
            report.organizers.set(self.cleaned_data['organizers'])
            report.partners_activated.set(self.cleaned_data['partners_activated'])
            report.technologies_used.set(self.cleaned_data['technologies_used'])
            report.area_activated.set(self.cleaned_data['area_activated'])
            report.directions_related.set(self.cleaned_data['directions_related'])
            report.learning_questions_related.set(self.cleaned_data['learning_questions_related'])
            report.metrics_related.set(self.add_metrics_related_depending_on_values())
        return report


def remove_domain(users_string):
    user_domains = ["User:", "Usuário (a):", "Usuário:", "Usuária:", "Utilizador(a):", "Utilizadora:", "Utilizador:"]
    for domain in user_domains:
        users_string = users_string.replace(domain, "")
    return users_string


def area_responsible_of_user(user):
    try:
        team_area = TeamArea.objects.get(team_area_of_position=user.userprofile.position)
        return team_area.id
    except TeamArea.DoesNotExist:
        return ""


def activities_associated_as_choices():
    areas = []
    for area in Area.objects.filter(project__active=True).distinct().order_by("text"):
        activities = []
        for activity in area.activities.all():
            activities.append((activity.id, activity.text + " (" + activity.code + ")"))
        areas.append((area.text, tuple(activities)))
    return tuple(areas)


def directions_associated_as_choices():
    axes = []
    for axis in StrategicAxis.objects.all():
        directions = []
        for direction in axis.directions.all():
            directions.append((direction.id, direction.text))
        axes.append((axis.text, tuple(directions)))

    return tuple(axes)


def learning_questions_as_choices():
    learning_areas = []
    for learning_area in LearningArea.objects.all():
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
    url = "https://www.mediawiki.org/w/api.php?action=query&meta=globaluserinfo&format=json&guiuser=" + quote(user, safe="")
    result = requests.get(url)
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