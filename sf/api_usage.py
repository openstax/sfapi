import logging

import sentry_sdk
from django.db import connections
from django.utils import timezone

logger = logging.getLogger("openstax")


def get_sf_api_usage():
    """
    Query the Salesforce REST API /limits/ endpoint to get current daily API usage.
    Returns (used, limit) tuple, or (None, None) if unavailable.
    """
    try:
        db = connections["salesforce"]
        db.ensure_connection()
        connection = db.connection

        # Get instance URL and session from the SF connection
        instance_url = connection.sf_auth.instance_url
        session = db.sf_session

        from salesforce.auth import API_VERSION

        url = f"{instance_url}/services/data/v{API_VERSION}/limits/"
        response = session.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        daily_api = data.get("DailyApiRequests", {})
        used = daily_api.get("Max", 0) - daily_api.get("Remaining", 0)
        limit = daily_api.get("Max", 0)
        return used, limit
    except Exception as e:
        logger.warning("Failed to fetch SF API limits: %s", e)
        return None, None


def should_sync(command=None):
    """
    Check if syncs should proceed based on kill switch and API usage threshold.
    Returns (allowed, reason) tuple.

    Optionally pass a management command instance to write status messages.
    """
    from api.models import SyncConfig

    config = SyncConfig.get()

    # Check kill switch
    if not config.sync_enabled:
        reason = "Sync is disabled via admin kill switch."
        if command:
            command.stdout.write(command.style.WARNING(reason))
        return False, reason

    # Check API usage against threshold
    used, limit = get_sf_api_usage()
    if used is not None and limit:
        # Update the config with latest usage data
        config.last_usage_check = timezone.now()
        config.last_usage_value = used
        config.last_usage_limit = limit
        config.save(update_fields=["last_usage_check", "last_usage_value", "last_usage_limit"])

        ratio = used / limit
        if ratio >= config.pause_threshold:
            reason = (
                f"SF API usage too high: {used:,}/{limit:,} ({ratio:.1%}). "
                f"Threshold is {config.pause_threshold:.0%}. Skipping sync."
            )
            if command:
                command.stdout.write(command.style.WARNING(reason))
            sentry_sdk.capture_message(reason)
            return False, reason

        if command:
            command.stdout.write(f"SF API usage: {used:,}/{limit:,} ({ratio:.1%})")

    return True, "ok"
