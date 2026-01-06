from django.contrib import admin
from .models import Report, AreaActivated, Editor, Funding, Organizer, Partner, \
    Technology, OperationReport

admin.site.register(Funding)
admin.site.register(Editor)
admin.site.register(Partner)
admin.site.register(Organizer)
admin.site.register(Technology)
admin.site.register(AreaActivated)
admin.site.register(Report)
admin.site.register(OperationReport)
