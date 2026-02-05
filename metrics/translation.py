from modeltranslation.translator import TranslationOptions, register

from .models import Activity, Area, Metric, Project


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
