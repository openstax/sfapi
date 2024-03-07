import sentry_sdk
from django.conf import settings
from django.core.cache import cache
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
    # TODO: fix this, mock something for tests
    # If testing, return True to bypass the authentication check
    if settings.IS_TESTING:
        return True
    return get_logged_in_user_uuid(request) is not None

def get_user_contact(request, expire=False):
    user_uuid = get_logged_in_user_uuid(request)
    if user_uuid is None and not settings.IS_TESTING:
        return 401, {"detail": "User is not logged in."}

    if expire:
        cache.delete(f"sfapi:contact:{user_uuid}")
        cache.delete(f"sfapi:adoptions:{user_uuid}")

    contact = cache.get(f"sfapi:contact:{user_uuid}")
    if contact is not None:
        return contact

    try:
        contact = Contact.objects.get(accounts_uuid=user_uuid)
        contact = {
            "id": contact.id,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "full_name": contact.full_name,
            "school": contact.account.name,
            "role": contact.role,
            "position": contact.position,
            "adoption_status": contact.adoption_status,
            "subject_interest": contact.subject_interest,
            "lms": contact.lms,
            "accounts_uuid": contact.accounts_uuid,
            "verification_status": contact.verification_status,
            "signup_date": contact.signup_date,
            "lead_source": contact.lead_source
        }
        cache.set(f"sfapi:contact:{user_uuid}", contact, 60*60*24*7)  # Cache the contact for 1 week
    except Contact.DoesNotExist:
        sentry_sdk.capture_message(f"User {user_uuid} does not have a valid Salesforce Contact.")
        return 404, {"detail": f"User {user_uuid} does not have a valid Salesforce Contact."}
    except Contact.MultipleObjectsReturned:
        sentry_sdk.capture_message(f"User {user_uuid} has multiple Salesforce Contacts.")

    sentry_sdk.set_user({"contact_id": contact['id']})
    return contact

# API endpoints, responses are defined in schemas.py
@router.get("/contact", auth=has_auth, response={200: ContactSchema, possible_error_codes: ErrorSchema}, tags=["user"])
@throttle(SalesforceAPIRateThrottle)
def user(request, expire: bool = False):
    return get_user_contact(request, expire)

@router.get("/adoptions", auth=has_auth, response={200: AdoptionsSchema, possible_error_codes: ErrorSchema}, tags=["user"])
@throttle(SalesforceAPIRateThrottle)
def adoptions(request, confirmed: bool = None, assumed: bool = None, expire: bool = False):
    contact = get_user_contact(request, expire)

    contact_adoptions = cache.get(f"sfapi:adoptions:{contact.id}")
    if contact_adoptions is not None:
        return contact_adoptions

    contact_adoptions = Adoption.objects.filter(contact=contact)
    if confirmed:
        contact_adoptions = contact_adoptions.filter(confirmation_type="OpenStax Confirmed Adoption")
    if assumed:
        contact_adoptions = contact_adoptions.exclude(confirmation_type="OpenStax Confirmed Adoption")

    if not contact_adoptions:
        return 404, {"detail": "No adoptions found."}

    # build the json for the cache, this keeps the database away from Salesforce on future requests
    # you must update this if you change the AdoptionsSchema or anything it depends on!
    response_json_for_cache = {
        "count": len(contact_adoptions),
        "contact_id": contact['id'],
        "adoptions": []
    }

    for adoption in contact_adoptions:
        response_json_for_cache["adoptions"].append({
            "id": adoption.id,
            "book": {
                "id": adoption.opportunity.book.id,
                "name": adoption.opportunity.book.name,
                "official_name": adoption.opportunity.book.official_name,
                "type": adoption.opportunity.book.type,
                "subject_areas": adoption.opportunity.book.subject_areas,
                "active_book": adoption.opportunity.book.active_book,
                "website_url": adoption.opportunity.book.website_url,
            },
            "base_year": adoption.base_year,
            "school_year": adoption.school_year,
            "school": adoption.opportunity.account.name,
            "confirmation_type": adoption.confirmation_type,
            "students": adoption.students,
            "savings": adoption.savings,
            "how_using": adoption.how_using,
            "confirmation_date": adoption.confirmation_date,
        })

    cache.set(f"sfapi:adoptions:{contact.id}", response_json_for_cache, 30)
    return response_json_for_cache


# Add the endpoints to the API
api.add_router("", router)
