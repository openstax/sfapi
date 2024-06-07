from sentry_sdk import capture_message
from django.http import JsonResponse
from django.db import connections
from django.conf import settings
from openstax_accounts.functions import get_logged_in_user_uuid
from api.api_v1 import has_super_auth


def info(request):
    #if has_super_auth(request):
    return JsonResponse({
        'release_information': release_information(),
        'api_usage': sf_api_usage(),
        'your_uuid': get_logged_in_user_uuid(request),
    })
    # else:
    #     return JsonResponse({'details': 'Unauthorized'}, status=401)

def sf_api_usage():
    try:
        api_usage = connections['salesforce'].connection.api_usage

        # Log a message if the API usage is over the set amount, default is 50%
        if api_usage.api_usage / api_usage.api_limit > settings.SALESFORCE_API_USE_ALERT_THRESHOLD:
            capture_message(f"Salesforce API usage is at {api_usage.api_usage / api_usage.api_limit * 100}%")

        return {
            'api_usage': api_usage.api_usage,
            'api_limit': api_usage.api_limit,
        }
    except AttributeError:
        return {
            'error': 'Salesforce API usage not available.',
        }

def release_information():
    if settings.SALESFORCE_USERNAME.contains('.'):
        salesforce_environment = settings.SALESFORCE_USERNAME.split('.')[1]
    else:
        salesforce_environment = 'production'

    return {
        'sfapi_version': settings.RELEASE_VERSION,
        'deployment_version': settings.DEPLOYMENT_VERSION,
        'environment': settings.ENVIRONMENT,
        'accounts_environment': settings.ACCOUNTS_URL,
        'salesforce_environment': salesforce_environment
    }
