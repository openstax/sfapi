import sentry_sdk
from django.conf import settings
from sf.models.adoption import Adoption
from sf.models.contact import Contact
from openstax_accounts.functions import get_logged_in_user_uuid
from .schemas import ErrorSchema, AdoptionsSchema, ContactSchema

from ninja_extra import NinjaExtraAPI, throttle, Router
from ninja_extra.throttling import UserRateThrottle

api = NinjaExtraAPI(
    version="1.0.0",  # Do not exceed 1.x.x in this file, create api_v2.py for new versions; NO breaking changes!
    title="OpenStax Salesforce API",
)
router = Router()

possible_error_codes = frozenset([401, 404, 422])

# Throttling for Salesforce endpoints to prevent API calls going over the limit
class SalesforceAPIRateThrottle(UserRateThrottle):
    rate = "5/min"
    scope = 'minutes'

# Authentication decorator to check if the user is authenticated with OpenStax Accounts
def has_auth(request):
    # If testing, return True to bypass the authentication check
    if settings.IS_TESTING:
        return True
    return get_logged_in_user_uuid(request) is not None

def get_user_contact(request):
    user_uuid = get_logged_in_user_uuid(request)
    if user_uuid is None and not settings.IS_TESTING:
        return 401, {"detail": "User is not logged in."}

    try:
        contact = Contact.objects.get(accounts_uuid=user_uuid)
    except Contact.DoesNotExist:
        sentry_sdk.capture_message(f"User {user_uuid} does not have a valid Salesforce Contact.")
        return 404, {"detail": f"User {user_uuid} does not have a valid Salesforce Contact."}
    except Contact.MultipleObjectsReturned:
        sentry_sdk.capture_message(f"User {user_uuid} has multiple Salesforce Contacts.")

    sentry_sdk.set_user({"contact_id": contact.id})
    return contact

# API endpoints, responses are defined in schemas.py
@router.get("/contact", auth=has_auth, response={200: ContactSchema, possible_error_codes: ErrorSchema}, tags=["user"])
@throttle(SalesforceAPIRateThrottle)
def user(request):
    return get_user_contact(request)

@router.get("/adoptions", auth=has_auth, response={200: AdoptionsSchema, possible_error_codes: ErrorSchema}, tags=["user"])
@throttle(SalesforceAPIRateThrottle)
def adoptions(request, confirmed: bool = None, assumed: bool = None):
    contact = get_user_contact(request)
    if isinstance(contact, tuple):  # user has multiple contacts
        return contact

    contact_adoptions = Adoption.objects.filter(contact=contact)
    if confirmed:
        contact_adoptions = contact_adoptions.filter(confirmation_type="OpenStax Confirmed Adoption")
    if assumed:
        contact_adoptions = contact_adoptions.exclude(confirmation_type="OpenStax Confirmed Adoption")

    if not contact_adoptions:
        return 404, {"detail": "No adoptions found."}
    else:
        return {"count": len(contact_adoptions), "adoptions": contact_adoptions}


# Add the endpoints to the API
api.add_router("", router)
