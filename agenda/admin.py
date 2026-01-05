from django.conf import settings

if settings.ENABLE_AGENDA_APP:
    from django.contrib import admin
    from agenda.models import Event
    admin.site.register(Event)
