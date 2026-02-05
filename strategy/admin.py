from django.contrib import admin

from .models import (Direction, EvaluationObjective, LearningArea,
                     StrategicAxis, StrategicLearningQuestion)

admin.site.register(StrategicAxis)
admin.site.register(Direction)
admin.site.register(LearningArea)
admin.site.register(StrategicLearningQuestion)
admin.site.register(EvaluationObjective)
