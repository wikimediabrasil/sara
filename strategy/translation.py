from modeltranslation.translator import TranslationOptions, register

from .models import (Direction, EvaluationObjective, LearningArea,
                     StrategicAxis, StrategicLearningQuestion)


@register(StrategicAxis)
class StrategicAxisTranslationOptions(TranslationOptions):
    fields = ("text",)


@register(Direction)
class DirectionTranslationOptions(TranslationOptions):
    fields = ("text",)


@register(StrategicLearningQuestion)
class StrategicLearningQuestionTranslationOptions(TranslationOptions):
    fields = ("text",)


@register(EvaluationObjective)
class EvaluationObjectiveTranslationOptions(TranslationOptions):
    fields = ("text",)


@register(LearningArea)
class LearningAreaTranslationOptions(TranslationOptions):
    fields = ("text",)
