from sentry_sdk import capture_message
from django.shortcuts import render
from django.http import JsonResponse
from django.db import connections
from django.conf import settings
from salesforce.dbapi.driver import ApiUsage


def info(request):
    return JsonResponse({
        'release_information': release_information(),

    })

def sf_api_usage():
    api_usage = connections['salesforce'].connection.api_usage

    # Log a message if the API usage is over the set amount, default is 50%
    if api_usage.api_usage / api_usage.api_limit > settings.SALESFORCE_API_USE_ALERT_THRESHOLD:
        capture_message(f"Salesforce API usage is at {api_usage.api_usage / api_usage.api_limit * 100}%")

    return {
        'api_usage': api_usage.api_usage,
        'api_limit': api_usage.api_limit,
    }

def release_information():
    return {
        'sfapi_version': settings.RELEASE_VERSION,
        'deployment_version': settings.DEPLOYMENT_VERSION,
        'environment': settings.ENVIRONMENT,
    }
