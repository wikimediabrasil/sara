from django.conf import settings

def global_flags(request):
    return {
        "MAINTENANCE_MODE": getattr(settings, "SARA_MAINTENANCE_MODE", False),
    }