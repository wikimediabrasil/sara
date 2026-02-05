from django.conf import settings


def global_flags(request):
    return {
        "MAINTENANCE_MODE": getattr(settings, "SARA_MAINTENANCE_MODE", False),
    }


def global_settings(request):
    """
    Expose selected settings to all templates globally.
    """
    return {
        "DEBUG_MODE": settings.DEBUG,
        "ENABLE_BUG_APP": getattr(settings, "ENABLE_BUG_APP", True),
        "ENABLE_AGENDA_APP": getattr(settings, "ENABLE_BUG_APP", True),
    }
