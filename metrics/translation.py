from modeltranslation.translator import register, TranslationOptions
from .models import Project, Area, Activity, Metric


@register(Project)
class ProjectTranslationOptions(TranslationOptions):
    fields = ("text",)


@register(Area)
class AreaTranslationOptions(TranslationOptions):
    fields = ("text",)


@register(Activity)
class ActivityTranslationOptions(TranslationOptions):
    fields = ("text",)


@register(Metric)
class MetricTranslationOptions(TranslationOptions):
    fields = ("text",)
