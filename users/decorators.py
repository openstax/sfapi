from django.conf import settings
from django.http import HttpResponseRedirect

from openstax_accounts.functions import get_logged_in_user_uuid


def logged_in(request):
    """
    Decorator for views that checks is user is logged-in to OpenStax Account
    """
    if settings.IS_TESTING:
        return True
    return get_logged_in_user_uuid(request) is not None
