from django.conf import settings
from django.shortcuts import redirect


def show_strategy(request):
    """
    Redirects the user to the strategy page
    :param request: The HTTP request object.
    :return: HttpResponseRedirect: Redirects to the strategy page.
    """
    return redirect(settings.STRATEGY_URL)
