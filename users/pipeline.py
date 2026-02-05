from django.contrib.auth import get_user_model

from users.models import UserProfile

User = get_user_model()


def associate_by_wiki_handle(backend, uid, user=None, *args, **kwargs):
    """
    Authentication pipeline step that associates a login attempt with an
    existing User based on a Wikimedia username.

    If a user is already authenticated, it returns immediately.
    Otherwise, it attempts to match the external username against:
    1. UserProfile.professional_wiki_handle (case-insensitive)
    2. User.username (fallback)

    This prevents duplicate accounts and allows users to authenticate
    using their Wikimedia username even if their Django username differs
    (backward compatibility, from when the login was not made with OAuth)

    Args:
        backend: Authentication backend in use.
        uid: Unique identifier provided by the authentication backend.
        user (User, optional): Already authenticated user, if any.
        *args: Additional positional arguments.
        **kwargs: Additional keyword arguments, expected to include
                  a 'details' dict containing a 'username' key.

    Returns:
        dict: {'user': User} if a matching user is found, otherwise an empty dict.
    """
    if user:
        return {"user": user}

    details = kwargs.get("details", {})
    wiki_username = details.get("username")

    if wiki_username:
        profile = (
            UserProfile.objects.filter(professional_wiki_handle__iexact=wiki_username)
            .select_related("user")
            .first()
        )
        if profile:
            return {"user": profile.user}

        user_ = User.objects.filter(username=wiki_username).first()
        if user_:
            return {"user": user_}

    return {}


def get_username(strategy, details, user=None, *args, **kwargs):
    """
    Determines the username to be used during authentication.

    If the user already exists, their current username is preserved.
    Otherwise, the username is derived from the Wikimedia authentication details.

    Args:
        strategy: Authentication strategy in use.
        details (dict): Authentication details provided by the backend,
            expected to include a 'username' key.
        user (User, optional): Existing user, if already authenticated.
        *args: Additional positional arguments.
        **kwargs: Additional keyword arguments.

    Returns:
        dict: {'username': str} representing the resolved username.
    """
    if user:
        return {"username": user.username}
    else:
        return {"username": details["username"]}
