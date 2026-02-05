from django.apps import AppConfig


class UsersConfig(AppConfig):
    """
    User domain models and organizational structure.

    Manages team areas, positions, and user profiles,
    extending Django's auth User with organization-specific data.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
