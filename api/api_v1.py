import datetime
import math
import sentry_sdk
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from sf.models.adoption import Adoption
from db.models import Contact
from sf.models.contact import Contact as SFContact
from db.models import Book
from db.models import Account
from sf.models.case import Case
from openstax_accounts.functions import get_logged_in_user_uuid
from .schemas import \
    ErrorSchema, \
    AdoptionsSchema, \
    ContactSchema, \
    BooksSchema, \
    CaseSchema, \
    UserSchema

from .schemas import AccountsSchema

from ninja_extra import NinjaExtraAPI, throttle, Router
from ninja_extra.throttling import UserRateThrottle

# Cache durations in seconds, calculated with math.prod() to use them in the api
# A reasonable format is to use math.prod([seconds, minutes, hours, days]) to calculate the duration
# CONTACT_CACHE_DURATION = math.prod([60, 60, 24, 7])  # 1 week
ADOPTIONS_CACHE_DURATION = math.prod([60, 60])  # 1 hour
# BOOK_CACHE_DURATION = math.prod([60, 60, 24, 14])  # 2 weeks
# ACCOUNT_CACHE_DURATION = math.prod([60, 60, 24, 14])  # 2 weeks

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

    try:
        try:
            sf_contact = Contact.objects.get(accounts_uuid=user_uuid)
        except Contact.DoesNotExist:
            try:
                sf_contact = SFContact.objects.get(accounts_uuid=user_uuid)
                # cache locally if it's not in the database
                account = Account.objects.get(id=sf_contact.account.id)
                Contact.objects.update_or_create(
                    id=sf_contact.id,
                    defaults={
                        "first_name": sf_contact.first_name,
                        "last_name": sf_contact.last_name,
                        "full_name": sf_contact.full_name,
                        "email": sf_contact.email,
                        "role": sf_contact.role,
                        "position": sf_contact.position,
                        "title": sf_contact.title,
                        "account": account,
                        "adoption_status": sf_contact.adoption_status,
                        "verification_status": sf_contact.verification_status,
                        "accounts_uuid": sf_contact.accounts_uuid,
                        "accounts_id": sf_contact.accounts_id,
                        "signup_date": sf_contact.signup_date,
                        "lead_source": sf_contact.lead_source,
                        "lms": sf_contact.lms,
                        "last_modified_date": sf_contact.last_modified_date,
                        "subject_interest": sf_contact.subject_interest,
                    },
                )
            except SFContact.DoesNotExist:
                return 404, {'code': 404, 'detail': f'Salesforce: No contact found for user {user_uuid}.'}
            except SFContact.MultipleObjectsReturned:
                sf_contact = SFContact.objects.filter(accounts_id=user_uuid).latest('last_modified_date')
                sentry_sdk.capture_message(
                    f"User {user_uuid} has multiple Salesforce Contacts. Returning the last modified ({sf_contact.id}).")
    except Contact.DoesNotExist:
        sentry_sdk.capture_message(f'User {user_uuid} does not have a valid Salesforce Contact.')
        return 404, {'code': 404, 'detail': f'User {user_uuid} does not have a valid Contact.'}
    except Contact.MultipleObjectsReturned:
        sf_contact = Contact.objects.filter(accounts_id=user_uuid).latest('last_modified_date')
        sentry_sdk.capture_message(
            f"User {user_uuid} has multiple Salesforce Contacts. Returning the last modified ({sf_contact.id}).")

    if sf_contact:
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
            "last_modified_date": sf_contact.signup_date.strftime(
                '%Y-%m-%d') if sf_contact.last_modified_date else None,
            "lead_source": sf_contact.lead_source,
        }

        return contact

# API endpoints, responses are defined in schemas.py
###########
# Contact #
###########
@router.get("/user", auth=has_auth, response={200: UserSchema, possible_error_codes: ErrorSchema}, tags=["user"])
def accounts_user(request):
    try:
        user_uuid = get_logged_in_user_uuid(request)
        if user_uuid is None:
            return 401, {'code': 401, 'detail': 'User is not logged in.'}
        return {'uuid': user_uuid}
    except Exception as e:
        sentry_sdk.capture_exception(e)
        return 401, {'code': 401, 'detail': f'An error occurred while fetching the user (Accounts Server: {settings.ACCOUNTS_URL}).'}


@router.get("/contact", auth=has_auth, response={200: ContactSchema, possible_error_codes: ErrorSchema}, tags=["user"])
@throttle(SalesforceAPIRateThrottle)
def user(request, expire: bool = False):
    contact = get_user_contact(request, expire)
    if not contact and not isinstance(contact, dict):
        return 404, {'code': 404, 'detail': f'No contact found.'}
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
        "total_students": sum([adoption.students for adoption in contact_adoptions]),
        "total_savings": sum([adoption.savings for adoption in contact_adoptions]),
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
def books(request):
    sf_books = Book.objects.filter(active_book=True)
    if not sf_books:
        return 404, {'code': 404, 'detail': 'No books found.'}

    # build the json for the cache, this keeps the database away from Salesforce on future requests
    # you must update this if you change the BooksSchema or anything it depends on!
    response_json = {
        "count": len(sf_books),
        "books": []
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
    return response_json


###########
# Schools #
###########
@router.get("/schools", auth=has_super_auth, response={200: AccountsSchema, possible_error_codes: ErrorSchema}, tags=["core"])
@throttle(SalesforceAPIRateThrottle)
def schools(request, name: str = None):
    if name:
        sf_schools = Account.objects.filter(name__icontains=name)
    else:
        return 422, {'code': 422, 'detail': 'You must provide a name or city to search by.'}

    if len(name) < 3:
        return 422, {'code': 422, 'detail': 'The query must be at least 3 characters long.'}

    if not sf_schools:
        return 404, {'code': 404, 'detail': 'No schools found.'}

    # build the json for the cache, this keeps the database away from Salesforce on future requests
    # you must update this if you change the AccountsSchema or anything it depends on!
    response_json = {
        "count": len(sf_schools),
        "total_schools": Account.objects.count(),
        "schools": [],
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
