from modeltranslation.translator import register, TranslationOptions
from .models import TeamArea, Position


@register(TeamArea)
class TeamAreaTranslationOptions(TranslationOptions):
    fields = ("text",)


@register(Position)
class PositionTranslationOptions(TranslationOptions):
    fields = ("text",)
