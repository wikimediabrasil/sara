from django.contrib.auth import get_user_model
from users.models import UserProfile

User = get_user_model()

def associate_by_wiki_handle(backend, uid, user=None, *args, **kwargs):
    if user:
        return {'user': user}

    try:
        details = kwargs.get('details', {})
        wiki_username = details.get('username')

        if wiki_username:
            profile = UserProfile.objects.filter(professional_wiki_handle__iexact=wiki_username).select_related('user').first()
            if profile:
                return {'user': profile.user}
    except UserProfile.DoesNotExist:
        pass

    return {}


def get_username(strategy, details, user=None, *args, **kwargs):
    if user:
        return {"username": user.username}
    else:
        return {"username": details['username']}