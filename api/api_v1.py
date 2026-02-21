import time
import datetime
import math
import sentry_sdk
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from db.models import Contact, Book, Account, Adoption
from sf.models.contact import Contact as SFContact
from sf.models.case import Case
from openstax_accounts.functions import get_logged_in_user_uuid
from .auth import combined_auth, has_scope
from .models import FormSubmission
from .forms.pipeline import FormPipeline
from .forms.processors import process_submission
from .schemas import \
    ErrorSchema, \
    AdoptionsSchema, \
    ContactSchema, \
    ContactUpdateSchema, \
    BooksSchema, \
    CaseSchema, \
    CaseCreateSchema, \
    FormSubmissionSchema, \
    FormSubmissionResponseSchema, \
    UserSchema

from .schemas import AccountsSchema

from ninja_extra import NinjaExtraAPI, throttle, Router
from ninja_extra.throttling import UserRateThrottle

# Cache durations in seconds, calculated with math.prod() to use them in the api
# A reasonable format is to use math.prod([seconds, minutes, hours, days]) to calculate the duration
CONTACT_CACHE_DURATION = math.prod([60, 15])  # 15 minutes
ADOPTIONS_CACHE_DURATION = math.prod([60, 60])  # 1 hour
SCHOOL_COUNT_CACHE_DURATION = math.prod([60, 60, 24])  # 24 hours

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

# Legacy auth functions kept for /info/ endpoint (sf/views.py)
def has_auth(request):
    return get_logged_in_user_uuid(request) is not None

def has_super_auth(request):
    uuid = get_logged_in_user_uuid(request)
    return uuid in settings.SUPER_USERS

def calculate_cache_expire(duration):
    return timezone.now() + datetime.timedelta(seconds=duration)

def get_user_contact(request, expire=False):
    user_uuid = get_logged_in_user_uuid(request)
    if user_uuid is None:
        return 401, {'code': 401, 'detail': 'User is not logged in.'}

    # Check cache first (unless expire=True to force refresh)
    cache_key = f"sfapi:contact:{user_uuid}"
    if not expire:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    try:
        try:
            sf_contact = Contact.objects.select_related('account').get(accounts_uuid=user_uuid)
        except Contact.DoesNotExist:
            try:
                sf_contact = SFContact.objects.get(accounts_uuid=user_uuid)
                # cache locally if it's not in the database
                try:
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
                except Account.DoesNotExist:
                    pass  # don't block the request if for some reason the account doesn't exist
                    sentry_sdk.capture_message(f"Account {sf_contact.account.id} does not exist in local database. "
                                               f"Contact: {sf_contact.id}")
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
        sf_contact = Contact.objects.select_related('account').filter(accounts_id=user_uuid).latest('last_modified_date')
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
            "last_modified_date": sf_contact.last_modified_date.strftime(
                '%Y-%m-%d') if sf_contact.last_modified_date else None,
            "lead_source": sf_contact.lead_source,
        }

        cache.set(cache_key, contact, CONTACT_CACHE_DURATION)
        return contact

# API endpoints, responses are defined in schemas.py
###########
# Contact #
###########
@router.get("/contact", auth=combined_auth, response={200: ContactSchema, possible_error_codes: ErrorSchema}, tags=["user"])
@throttle(SalesforceAPIRateThrottle)
def salesforce_contact(request, expire: bool = False):
    contact = get_user_contact(request, expire)
    if not contact or not isinstance(contact, dict):
        return 404, {'code': 404, 'detail': 'No contact found.'}
    return contact

#############
# Adoptions #
#############
@router.get("/adoptions", auth=combined_auth, response={200: AdoptionsSchema, possible_error_codes: ErrorSchema}, tags=["user"])
@throttle(SalesforceAPIRateThrottle)
def salesforce_adoptions(request, confirmed: bool = None, assumed: bool = None, expire: bool = False):
    contact = get_user_contact(request, expire)

    if not contact or not isinstance(contact, dict):
        return 404, {'code': 404, 'detail': 'No contact found.'}

    contact_adoptions = cache.get(f"sfapi:adoptions{confirmed}:{assumed}:{contact['id']}")
    if contact_adoptions is not None:
        return contact_adoptions

    contact_adoptions = Adoption.objects.select_related(
        'opportunity__book', 'opportunity__account'
    ).filter(contact__id=contact['id'])
    if confirmed:
        contact_adoptions = contact_adoptions.filter(confirmation_type='OpenStax Confirmed Adoption')
    if assumed:
        contact_adoptions = contact_adoptions.exclude(confirmation_type='OpenStax Confirmed Adoption')

    if not contact_adoptions:
        return 404, {'code': 404, 'detail': 'No adoptions found'}

    #  calculate the total students and savings for the adoptions (this could be null, so handle that)
    # if we know they won't be null, we can use a list comprehension to make this more concise in the response_json
    # total_students = sum([adoption.students for adoption in contact_adoptions if adoption.students])
    total_students = 0
    total_savings = 0
    for adoption in contact_adoptions:
        if not adoption.students or adoption.students < 0:
            pass
        else:
            total_students += adoption.students

        if not adoption.savings or adoption.savings < 0:
            pass
        else:
            total_savings += adoption.savings

    # build the json for the cache, this keeps the database away from Salesforce on future requests
    # you must update this if you change the AdoptionsSchema or anything it depends on!
    response_json = {
        "count": len(contact_adoptions),
        "contact_id": contact['id'],
        "first_year_adopting_openstax": contact_adoptions.order_by('base_year').first().base_year if contact_adoptions else None,
        "total_students": total_students,
        "total_savings": total_savings,
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
@router.get("/books", auth=combined_auth, response={200: BooksSchema, possible_error_codes: ErrorSchema}, tags=["core"])
@throttle(SalesforceAPIRateThrottle)
def salesforce_books(request):
    if not has_scope(request, 'read:books'):
        return 401, {'code': 401, 'detail': 'Insufficient permissions. Required scope: read:books'}
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
@router.get("/schools", response={200: AccountsSchema, possible_error_codes: ErrorSchema}, tags=["core"])
@throttle(SalesforceAPIRateThrottle)
def salesforce_schools(request, name: str = None):
    if not name:
        return 422, {'code': 422, 'detail': 'You must provide a name or city to search by.'}

    if len(name) < 3:
        return 422, {'code': 422, 'detail': 'The query must be at least 3 characters long.'}

    sf_schools = Account.objects.filter(name__icontains=name)

    if not sf_schools:
        return 404, {'code': 404, 'detail': 'No schools found.'}

    total_count = cache.get("sfapi:school_count")
    if total_count is None:
        total_count = Account.objects.count()
        cache.set("sfapi:school_count", total_count, SCHOOL_COUNT_CACHE_DURATION)

    # build the json for the cache, this keeps the database away from Salesforce on future requests
    # you must update this if you change the AccountsSchema or anything it depends on!
    response_json = {
        "count": len(sf_schools),
        "total_schools": total_count,
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

@router.post("/case", auth=combined_auth, response={200: CaseSchema, possible_error_codes: ErrorSchema}, tags=["support"])
@throttle(SalesforceAPIRateThrottle)
def salesforce_case(request, payload: CaseCreateSchema):
    if not has_scope(request, 'write:cases'):
        return 401, {'code': 401, 'detail': 'Insufficient permissions. Required scope: write:cases'}
    case = Case.objects.create(
        subject=payload.subject,
        description=payload.description,
        product=payload.product,
        feature=payload.feature,
        issue=payload.issue,
    )
    return case


######################
# Contact (Update)  #
######################
@router.put("/contact", auth=combined_auth, response={200: ContactSchema, possible_error_codes: ErrorSchema}, tags=["user"])
@throttle(SalesforceAPIRateThrottle)
def update_contact(request, payload: ContactUpdateSchema):
    user_uuid = get_logged_in_user_uuid(request)
    if user_uuid is None:
        return 401, {'code': 401, 'detail': 'User is not logged in.'}

    try:
        contact = Contact.objects.get(accounts_uuid=user_uuid)
    except Contact.DoesNotExist:
        return 404, {'code': 404, 'detail': 'No contact found.'}

    # Only update fields that were provided
    update_fields = []
    for field_name, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            setattr(contact, field_name, value)
            update_fields.append(field_name)

    if update_fields:
        # Update full_name if first or last name changed
        if 'first_name' in update_fields or 'last_name' in update_fields:
            contact.full_name = f"{contact.first_name} {contact.last_name}"
            update_fields.append('full_name')
        contact._change_source = 'api'
        contact._changed_by = user_uuid
        contact.save()

    # Invalidate cached contact after update
    cache.delete(f"sfapi:contact:{user_uuid}")
    return get_user_contact(request)


#################
# Form Gateway #
#################
form_pipeline = FormPipeline()

@router.post("/forms/submit", auth=combined_auth, response={200: FormSubmissionResponseSchema, 202: FormSubmissionResponseSchema, possible_error_codes: ErrorSchema}, tags=["forms"])
def submit_form(request, payload: FormSubmissionSchema):
    request_time = time.time()
    is_valid, errors = form_pipeline.validate(payload, request_time)

    # Get auth info for the submission record
    auth_type = getattr(request, 'auth_type', '')
    auth_identifier = ''
    if auth_type == 'sso':
        auth_identifier = getattr(request, 'auth_uuid', '')
    elif auth_type == 'api_key':
        auth_identifier = getattr(request, 'auth_key_name', '')

    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR')

    if not is_valid and 'spam' in errors:
        # Silent discard — return 202 so bots don't know they were detected
        submission = FormSubmission.objects.create(
            form_type=payload.form_type,
            data=payload.data,
            source_url=payload.source_url or '',
            status='spam',
            auth_type=auth_type,
            auth_identifier=auth_identifier,
            ip_address=ip_address,
        )
        return 202, {'id': str(submission.id), 'form_type': submission.form_type, 'status': 'pending'}

    if not is_valid:
        return 422, {'code': 422, 'detail': '; '.join(errors)}

    submission = FormSubmission.objects.create(
        form_type=payload.form_type,
        data=payload.data,
        source_url=payload.source_url or '',
        status='pending',
        auth_type=auth_type,
        auth_identifier=auth_identifier,
        ip_address=ip_address,
    )

    # Process synchronously for now
    process_submission(submission)

    return {'id': str(submission.id), 'form_type': submission.form_type, 'status': submission.status}


# Add the endpoints to the API
api.add_router("", router)
