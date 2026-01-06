from modeltranslation.translator import register, TranslationOptions
from .models import StrategicAxis, Direction, StrategicLearningQuestion, EvaluationObjective, LearningArea


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
