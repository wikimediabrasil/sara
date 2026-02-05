from modeltranslation.translator import TranslationOptions, register

from .models import Position, TeamArea


@register(TeamArea)
class TeamAreaTranslationOptions(TranslationOptions):
    fields = ("text",)


@register(Position)
class PositionTranslationOptions(TranslationOptions):
    fields = ("text",)
