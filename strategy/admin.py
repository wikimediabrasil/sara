from django.contrib import admin
from .models import StrategicAxis, Direction, LearningArea, StrategicLearningQuestion, EvaluationObjective

admin.site.register(StrategicAxis)
admin.site.register(Direction)
admin.site.register(LearningArea)
admin.site.register(StrategicLearningQuestion)
admin.site.register(EvaluationObjective)