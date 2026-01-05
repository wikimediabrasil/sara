from django.conf import settings

if settings.ENABLE_STRATEGY_APP:
    from django.contrib import admin
    from .models import StrategicAxis, Direction
    admin.site.register(StrategicAxis)
    admin.site.register(Direction)
