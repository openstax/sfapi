from sentry_sdk import capture_message

from sf.models.adoption import Adoption
from sf.models.contact import Contact
from accounts.functions import get_logged_in_user_uuid
from .schemas import Message, AdoptionsSchema, ContactSchema

from ninja_extra import NinjaExtraAPI, throttle
from ninja_extra.throttling import UserRateThrottle

api = NinjaExtraAPI(
    version="1.0.0",  # Do not exceed 1.x.x in this file, create api_v2.py for new versions; NO breaking changes!
    title="OpenStax Salesforce API",
)

possible_error_codes = frozenset([401, 404])

# Throttling for Salesforce endpoints to prevent API calls going over the limit
class User5MinRateThrottle(UserRateThrottle):
    rate = "5/min"
    scope = 'minutes'

# Authentication decorator to check if the user is authenticated with OpenStax Accounts
def is_authenticated(request):
    return get_logged_in_user_uuid(request) is not None

# API endpoints, responses are defined in schemas.py
@api.get("/contact", auth=is_authenticated, response={200: ContactSchema, possible_error_codes: Message}, tags=["user"])
@throttle(User5MinRateThrottle)
def user(request):
    user_uuid = get_logged_in_user_uuid(request)

    try:
        contact = Contact.objects.get(accounts_uuid=user_uuid)
    except Contact.DoesNotExist:
        capture_message(f"User {user_uuid} does not have a valid Salesforce Contact.")
        return 404, {"message": "User does not have a valid Salesforce Contact."}

    return contact

@api.get("/adoptions", auth=is_authenticated, response={200: AdoptionsSchema, possible_error_codes: Message}, tags=["user"])
@throttle(User5MinRateThrottle)
def adoptions(request, confirmed: bool = None, assumed: bool = None):
    user_uuid = get_logged_in_user_uuid(request)

    contact = Contact.objects.get(accounts_uuid=user_uuid)
    if not contact:
        capture_message(f"User {user_uuid} does not have a valid Salesforce Contact.")
        return 404, {"message": "User does not have a valid Salesforce Contact."}

    contact_adoptions = Adoption.objects.filter(contact=contact)
    if confirmed:
        contact_adoptions = contact_adoptions.filter(confirmation_type="OpenStax Confirmed Adoption")
    if assumed:
        contact_adoptions = contact_adoptions.exclude(confirmation_type="OpenStax Confirmed Adoption")

    if not contact_adoptions:
        return 404, {"message": "No adoptions found."}

    return {"count": len(contact_adoptions), "adoptions": contact_adoptions}
