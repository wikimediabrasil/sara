from django.contrib import admin

from .models import Activity, Area, Metric, Project

admin.site.register(Project)
admin.site.register(Area)
admin.site.register(Activity)
admin.site.register(Metric)
