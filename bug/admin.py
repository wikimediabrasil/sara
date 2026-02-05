from django.conf import settings

if settings.ENABLE_BUG_APP:
    from django.contrib import admin

    from .models import Bug, Observation

    admin.site.register(Bug)
    admin.site.register(Observation)
