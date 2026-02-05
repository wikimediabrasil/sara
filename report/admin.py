from django.contrib import admin

from .models import (Editor, Funding, OperationReport, Organizer, Partner,
                     Report, Technology)

admin.site.register(Funding)
admin.site.register(Editor)
admin.site.register(Partner)
admin.site.register(Organizer)
admin.site.register(Technology)
admin.site.register(Report)
admin.site.register(OperationReport)
