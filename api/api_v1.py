import datetime
import math
import sentry_sdk
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from sf.models.adoption import Adoption
from sf.models.contact import Contact
from sf.models.book import Book
from sf.models.account import Account
from sf.models.case import Case
from openstax_accounts.functions import get_logged_in_user_uuid
from .schemas import \
    ErrorSchema, \
    AdoptionsSchema, \
    ContactSchema, \
    BooksSchema, \
    CaseSchema

from sf.objects.contact import get_contact
from sf.objects.adoption import get_adoptions

from .schemas import AccountsSchema

from ninja_extra import NinjaExtraAPI, throttle, Router
from ninja_extra.throttling import UserRateThrottle
from ninja import Query

# Cache durations in seconds, calculated with math.prod() to use them in the api
# A reasonable format is to use math.prod([seconds, minutes, hours, days]) to calculate the duration
CONTACT_CACHE_DURATION = math.prod([60, 60, 24, 7])  # 1 week
ADOPTIONS_CACHE_DURATION = math.prod([60, 60])  # 1 hour
BOOK_CACHE_DURATION = math.prod([60, 60, 24, 14])  # 2 weeks
ACCOUNT_CACHE_DURATION = math.prod([60, 60, 24, 14])  # 2 weeks

api = NinjaExtraAPI(
    version="1.0.0",  # Do not exceed 1.x.x in this file, create api_v2.py for new versions; NO breaking changes!
    title="OpenStax Salesforce API",
)
router = Router()

possible_error_codes = frozenset([401, 404, 422])

# TODO: consider this now that caching of requests is now in place
# Throttling for Salesforce endpoints to prevent API calls going over the limit
class SalesforceAPIRateThrottle(UserRateThrottle):
    rate = settings.SALESFORCE_API_RATE_LIMIT

# Authentication decorator to check if the user is authenticated with OpenStax Accounts
def has_auth(request):
    # TODO: fix this, mock something for tests
    # If testing, return True to bypass the authentication check
    if settings.IS_TESTING:
        return True
    return get_logged_in_user_uuid(request) is not None

def has_super_auth(request):
    uuid = get_logged_in_user_uuid(request)
    return uuid in settings.SUPER_USERS

def calculate_cache_expire(duration):
    return timezone.now() + datetime.timedelta(seconds=duration)

def get_user_contact(request, expire=False):
    user_uuid = get_logged_in_user_uuid(request)
    if user_uuid is None and not settings.IS_TESTING:
        return 401, {'code': 401, 'detail': 'User is not logged in.'}

    if expire:
        cache.delete(f"sfapi:contact:{user_uuid}")
        cache.delete(f"sfapi:adoptions:{user_uuid}")

    contact = cache.get(f"sfapi:contact:{user_uuid}")
    if contact is not None:
        return contact

    try:
        sf_contact = Contact.objects.get(accounts_uuid=user_uuid)
        contact = {
            "id": sf_contact.id,
            "first_name": sf_contact.first_name,
            "last_name": sf_contact.last_name,
            "full_name": sf_contact.full_name,
            "school": sf_contact.account.name,
            "role": sf_contact.role,
            "position": sf_contact.position,
            "adoption_status": sf_contact.adoption_status,
            "subject_interest": sf_contact.subject_interest,
            "lms": sf_contact.lms,
            "accounts_uuid": sf_contact.accounts_uuid,
            "verification_status": sf_contact.verification_status,
            "signup_date": sf_contact.signup_date.strftime('%Y-%m-%d') if sf_contact.signup_date else None,
            "lead_source": sf_contact.lead_source,
            "cache_create": timezone.now(),
            "cache_expire": calculate_cache_expire(CONTACT_CACHE_DURATION),
        }
        cache.set(f'sfapi:contact:{user_uuid}', contact, CONTACT_CACHE_DURATION)
    except Contact.DoesNotExist:
        sentry_sdk.capture_message(f'User {user_uuid} does not have a valid Salesforce Contact.')
        return 404, {'code': 404, 'detail': f'User {user_uuid} does not have a valid Salesforce Contact.'}
    except Contact.MultipleObjectsReturned:
        sentry_sdk.capture_message(f"User {user_uuid} has multiple Salesforce Contacts.")

    if contact:
        return contact
    else:
        return 404, {'code': 404, 'detail': f'No contact found for user {user_uuid}.'}

# API endpoints, responses are defined in schemas.py
###########
# Contact #
###########
@router.get("/contact", auth=has_auth, response={200: ContactSchema, possible_error_codes: ErrorSchema}, tags=["user"])
@throttle(SalesforceAPIRateThrottle)
def user(request, expire: bool = False):
    contact = get_user_contact(request, expire)
    if not contact and not isinstance(contact, dict):
        user_uuid = get_logged_in_user_uuid(request)
        if user_uuid:
            return 404, {'code': 404, 'detail': f'No contact found for user {user_uuid}.'}
        else:
            return 401, {'code': 401, 'detail': 'User is not logged in.'}
    return contact

#############
# Adoptions #
#############
@router.get("/adoptions", auth=has_auth, response={200: AdoptionsSchema, possible_error_codes: ErrorSchema}, tags=["user"])
@throttle(SalesforceAPIRateThrottle)
def adoptions(request, confirmed: bool = None, assumed: bool = None, expire: bool = False):
    contact = get_user_contact(request, expire)

    if not contact or not isinstance(contact, dict):
        return 404, {'code': 404, 'detail': 'No contact found.'}

    contact_adoptions = cache.get(f"sfapi:adoptions{confirmed}:{assumed}:{contact['id']}")
    if contact_adoptions is not None:
        return contact_adoptions

    contact_adoptions = Adoption.objects.filter(contact__id=contact['id'])
    if confirmed:
        contact_adoptions = contact_adoptions.filter(confirmation_type='OpenStax Confirmed Adoption')
    if assumed:
        contact_adoptions = contact_adoptions.exclude(confirmation_type='OpenStax Confirmed Adoption')

    if not contact_adoptions:
        return 404, {'code': 404, 'detail': 'No adoptions found'}

    # build the json for the cache, this keeps the database away from Salesforce on future requests
    # you must update this if you change the AdoptionsSchema or anything it depends on!
    response_json = {
        "count": len(contact_adoptions),
        "contact_id": contact['id'],
        "adoptions": [],
        "cache_create": timezone.now(),
        "cache_expire": calculate_cache_expire(ADOPTIONS_CACHE_DURATION),
    }

    for adoption in contact_adoptions:
        response_json["adoptions"].append({
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
            "confirmation_date": adoption.confirmation_date.strftime("%Y-%m-%d") if adoption.confirmation_date else None,
        })

    cache.set(f"sfapi:adoptions{confirmed}:{assumed}:{contact['id']}", response_json, ADOPTIONS_CACHE_DURATION)
    return response_json

#########
# Books #
#########
@router.get("/books", auth=has_super_auth, response={200: BooksSchema, possible_error_codes: ErrorSchema}, tags=["core"])
@throttle(SalesforceAPIRateThrottle)
def books(request, expire: bool = False):
    if expire:
        cache.delete("sfapi:books")

    books_from_cache = cache.get("sfapi:books")
    if books_from_cache is not None:
        return books_from_cache

    sf_books = Book.objects.filter(active_book=True)
    if not sf_books:
        return 404, {'code': 404, 'detail': 'No books found.'}

    # build the json for the cache, this keeps the database away from Salesforce on future requests
    # you must update this if you change the BooksSchema or anything it depends on!
    response_json = {
        "count": len(sf_books),
        "books": [],
        "cache_create": timezone.now(),
        "cache_expire": calculate_cache_expire(BOOK_CACHE_DURATION),
    }

    for book in sf_books:
        response_json["books"].append({
            "id": book.id,
            "name": book.name,
            "official_name": book.official_name,
            "type": book.type,
            "subject_areas": book.subject_areas,
            "website_url": book.website_url,
        })

    cache.set("sfapi:books", response_json, BOOK_CACHE_DURATION)
    return response_json


###########
# Schools #
###########
@router.get("/schools", auth=has_super_auth, response={200: AccountsSchema, possible_error_codes: ErrorSchema}, tags=["core"])
@throttle(SalesforceAPIRateThrottle)
def schools(request, name: str = None, city: str = None, expire: bool = False):
    if len(name) < 3 or len(city) < 3:
        return 422, {'code': 422, 'detail': 'The query must be at least 3 characters long.'}

    if expire:
        cache.delete(f"sfapi:schools:{name}")

    schools_from_cache = cache.get(f"sfapi:schools:{name}")
    if schools_from_cache is not None:
        return schools_from_cache

    if name:
        sf_schools = Account.objects.filter(name__icontains=name)
    elif city:
        sf_schools = Account.objects.filter(city__icontains=city)
    else:
        return 422, {'code': 422, 'detail': 'You must provide a name or city to search by.'}

    if not sf_schools:
        return 404, {'code': 404, 'detail': 'No schools found.'}

    # build the json for the cache, this keeps the database away from Salesforce on future requests
    # you must update this if you change the AccountsSchema or anything it depends on!
    response_json = {
        "count": len(sf_schools),
        "total_schools": Account.objects.count(),
        "schools": [],
        "cache_create": timezone.now(),
        "cache_expire": calculate_cache_expire(ACCOUNT_CACHE_DURATION),
    }

    for school in sf_schools:
        response_json["schools"].append({
            "id": school.id,
            "name": school.name,
            "type": school.type,
            "country": school.country,
            "state": school.state,
            "city": school.city,
            "lms": school.lms,
            "sheer_id_school_name": school.sheer_id_school_name,
        })

    cache.set(f"sfapi:schools:{name}", response_json, ACCOUNT_CACHE_DURATION)
    return response_json

@router.post("/case", auth=has_super_auth, response={200: CaseSchema, possible_error_codes: ErrorSchema}, tags=["support"])
@throttle(SalesforceAPIRateThrottle)
def case(request):
    case = Case.objects.create(
        subject=request.data['subject'],
        description=request.data['description'],
        product=request.data['product'],
        feature=request.data['feature'],
        issue=request.data['issue'],
    )
    return case


# Add the endpoints to the API
api.add_router("", router)
