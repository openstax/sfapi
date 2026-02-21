import logging
from django.db import transaction
from .models import Contact, Account
from sentry_sdk import capture_exception

logger = logging.getLogger('openstax')

ACCOUNT_SYNC_FIELDS = [
    'name', 'type', 'country', 'state', 'city', 'country_code', 'state_code',
    'created_date', 'last_modified_date', 'last_activity_date', 'lms',
    'books_adopted', 'sheer_id_school_name', 'ipeds_id', 'nces_id',
]

CONTACT_SYNC_FIELDS = [
    'first_name', 'last_name', 'full_name', 'email', 'role', 'position',
    'title', 'account', 'adoption_status', 'verification_status',
    'accounts_uuid', 'accounts_id', 'signup_date', 'lead_source', 'lms',
    'last_modified_date', 'subject_interest',
]


def update_or_create_accounts(salesforce_accounts):
    """
    Bulk update or create accounts in the local database from a list of salesforce accounts.
    Uses bulk_create/bulk_update within a transaction for performance.
    """
    existing_ids = set(Account.objects.values_list('id', flat=True))
    to_create = []
    to_update = []

    for account in salesforce_accounts:
        db_account = Account(
            id=account.id,
            name=account.name,
            type=account.type,
            country=account.country,
            state=account.state,
            city=account.city,
            country_code=account.country_code,
            state_code=account.state_code,
            created_date=account.created_date,
            last_modified_date=account.last_modified_date,
            last_activity_date=account.last_activity_date,
            lms=account.lms,
            books_adopted=account.books_adopted,
            sheer_id_school_name=account.sheer_id_school_name,
            ipeds_id=account.ipeds_id,
            nces_id=account.nces_id,
        )
        if account.id in existing_ids:
            to_update.append(db_account)
        else:
            to_create.append(db_account)

    with transaction.atomic():
        if to_create:
            Account.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            Account.objects.bulk_update(to_update, fields=ACCOUNT_SYNC_FIELDS, batch_size=500)

    logger.info(f"Accounts sync: {len(to_create)} created, {len(to_update)} updated")
    return len(to_create)


def update_or_create_contacts(salesforce_contacts):
    """
    Bulk update or create contacts in the local database from a list of salesforce contacts.
    Uses bulk_create/bulk_update within a transaction for performance.
    """
    existing_ids = set(Contact.objects.values_list('id', flat=True))
    account_ids = set(Account.objects.values_list('id', flat=True))
    to_create = []
    to_update = []
    skipped = 0

    for contact in salesforce_contacts:
        account_id = contact.account.id if contact.account else None
        if account_id and account_id not in account_ids:
            capture_exception(Exception(f"Account with id {account_id} does not exist"))
            skipped += 1
            continue

        db_contact = Contact(
            id=contact.id,
            first_name=contact.first_name,
            last_name=contact.last_name,
            full_name=contact.full_name,
            email=contact.email,
            role=contact.role,
            position=contact.position,
            title=contact.title,
            account_id=account_id,
            adoption_status=contact.adoption_status,
            verification_status=contact.verification_status,
            accounts_uuid=contact.accounts_uuid,
            accounts_id=contact.accounts_id,
            signup_date=contact.signup_date,
            lead_source=contact.lead_source,
            lms=contact.lms,
            last_modified_date=contact.last_modified_date,
            subject_interest=contact.subject_interest,
        )
        if contact.id in existing_ids:
            to_update.append(db_contact)
        else:
            to_create.append(db_contact)

    with transaction.atomic():
        if to_create:
            Contact.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            Contact.objects.bulk_update(to_update, fields=CONTACT_SYNC_FIELDS, batch_size=500)

    logger.info(f"Contacts sync: {len(to_create)} created, {len(to_update)} updated, {skipped} skipped")
    return len(to_create)
