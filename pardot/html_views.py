"""
HTML views for the Camp Campaign dashboard.
Serves the dashboard templates, requiring SuperUser auth via SSO.
"""

from django.shortcuts import render
from openstax_accounts.functions import get_logged_in_user_uuid

from api.models import SuperUser


def _check_super_user(request):
    """Check if the user is authenticated and is a SuperUser."""
    user_uuid = None

    # Check for DEV_USER_UUID bypass
    from django.conf import settings

    if getattr(settings, "DEV_USER_UUID", None):
        user_uuid = settings.DEV_USER_UUID
    else:
        user_uuid = get_logged_in_user_uuid(request)

    if user_uuid and SuperUser.is_super_user(user_uuid):
        return True
    return False


def _forbidden(request):
    """Render the camp-themed 403 page."""
    return render(request, "pardot/403.html", status=403)


def dashboard(request):
    if not _check_super_user(request):
        return _forbidden(request)
    return render(request, "pardot/index.html")


def admin_settings(request):
    if not _check_super_user(request):
        return _forbidden(request)
    return render(request, "pardot/admin.html")
