from modeltranslation.translator import register, TranslationOptions
from .models import StrategicAxis, Direction


@register(StrategicAxis)
class TeamAreaTranslationOptions(TranslationOptions):
    fields = ("text",)


@register(Direction)
class PositionTranslationOptions(TranslationOptions):
    fields = ("text",)
