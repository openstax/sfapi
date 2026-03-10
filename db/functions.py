import logging

from django.core.cache import cache
from django.db import transaction
from sentry_sdk import capture_exception

from .models import Account, Adoption, Book, Contact, Opportunity

logger = logging.getLogger("openstax")

ACCOUNT_SYNC_FIELDS = [
    "name",
    "type",
    "country",
    "state",
    "city",
    "country_code",
    "state_code",
    "created_date",
    "last_modified_date",
    "last_activity_date",
    "lms",
    "books_adopted",
    "sheer_id_school_name",
    "ipeds_id",
    "nces_id",
]

CONTACT_SYNC_FIELDS = [
    "first_name",
    "last_name",
    "full_name",
    "email",
    "role",
    "position",
    "title",
    "account",
    "adoption_status",
    "verification_status",
    "accounts_uuid",
    "accounts_id",
    "signup_date",
    "lead_source",
    "lms",
    "last_modified_date",
    "subject_interest",
]

OPPORTUNITY_SYNC_FIELDS = [
    "account_id",
    "record_type_id",
    "name",
    "description",
    "stage_name",
    "amount",
    "probability",
    "close_date",
    "type",
    "lead_source",
    "is_closed",
    "is_won",
    "owner_id",
    "created_date",
    "created_by_id",
    "last_modified_date",
    "last_modified_by_id",
    "system_modstamp",
    "last_activity_date",
    "last_activity_in_days",
    "last_stage_change_date",
    "last_stage_change_in_days",
    "fiscal_year",
    "fiscal",
    "contact_id",
    "last_viewed_date",
    "last_referenced_date",
    "book_id",
]

ADOPTION_SYNC_FIELDS = [
    "contact_id",
    "adoption_number",
    "created_date",
    "last_modified_date",
    "system_modstamp",
    "last_activity_date",
    "class_start_date",
    "opportunity_id",
    "confirmation_date",
    "name",
    "base_year",
    "adoption_type",
    "students",
    "school_year",
    "terms_used",
    "confirmation_type",
    "how_using",
    "savings",
]

BOOK_SYNC_FIELDS = [
    "name",
    "official_name",
    "type",
    "subject_areas",
    "website_url",
]


def update_or_create_accounts(salesforce_accounts, full_sync=False):
    """
    Bulk upsert accounts into the local database using ON CONFLICT DO UPDATE.
    On full sync, marks records not in the batch as soft-deleted.
    """
    records = []
    synced_ids = []
    for account in salesforce_accounts:
        synced_ids.append(account.id)
        records.append(
            Account(
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
                is_deleted=False,
            )
        )

    with transaction.atomic():
        Account.all_objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=["id"],
            update_fields=ACCOUNT_SYNC_FIELDS + ["is_deleted"],
            batch_size=500,
        )
        if full_sync:
            Account.all_objects.exclude(id__in=synced_ids).update(is_deleted=True)

    cache.delete("sfapi:school_count")
    logger.info(f"Accounts sync: {len(records)} upserted (full_sync={full_sync})")
    return len(records)


def update_or_create_contacts(salesforce_contacts, full_sync=False):
    """
    Bulk upsert contacts into the local database using ON CONFLICT DO UPDATE.
    Validates FK references to accounts before insert.
    """
    # Materialize the SF queryset once to avoid re-querying Salesforce
    salesforce_contacts = list(salesforce_contacts)

    # Only check account IDs that are actually referenced in this batch
    referenced_account_ids = {c.account_id for c in salesforce_contacts if c.account_id}
    if referenced_account_ids:
        valid_account_ids = set(
            Account.all_objects.filter(id__in=referenced_account_ids).values_list("id", flat=True)
        )
    else:
        valid_account_ids = set()

    records = []
    synced_ids = []
    skipped = 0

    for contact in salesforce_contacts:
        account_id = contact.account_id
        if account_id and account_id not in valid_account_ids:
            capture_exception(Exception(f"Account with id {account_id} does not exist"))
            skipped += 1
            continue

        synced_ids.append(contact.id)
        records.append(
            Contact(
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
                is_deleted=False,
            )
        )

    with transaction.atomic():
        Contact.all_objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=["id"],
            update_fields=CONTACT_SYNC_FIELDS + ["is_deleted"],
            batch_size=500,
        )
        if full_sync:
            Contact.all_objects.exclude(id__in=synced_ids).update(is_deleted=True)

    logger.info(f"Contacts sync: {len(records)} upserted, {skipped} skipped (full_sync={full_sync})")
    return len(records)


def update_or_create_opportunities(salesforce_opportunities, full_sync=False):
    """
    Bulk upsert opportunities into the local database using ON CONFLICT DO UPDATE.
    Validates FK references to accounts, contacts, and books before insert.
    """
    # Materialize the SF queryset once to avoid re-querying Salesforce
    salesforce_opportunities = list(salesforce_opportunities)

    # Only check FK IDs that are actually referenced in this batch
    ref_account_ids = {o.account_id for o in salesforce_opportunities if o.account_id}
    ref_contact_ids = {o.contact_id for o in salesforce_opportunities if o.contact_id}
    ref_book_ids = {o.book_id for o in salesforce_opportunities if o.book_id}

    valid_account_ids = set(
        Account.all_objects.filter(id__in=ref_account_ids).values_list("id", flat=True)
    ) if ref_account_ids else set()
    valid_contact_ids = set(
        Contact.all_objects.filter(id__in=ref_contact_ids).values_list("id", flat=True)
    ) if ref_contact_ids else set()
    valid_book_ids = set(
        Book.all_objects.filter(id__in=ref_book_ids).values_list("id", flat=True)
    ) if ref_book_ids else set()

    records = []
    synced_ids = []
    skipped = 0

    for opp in salesforce_opportunities:
        account_id = opp.account_id
        contact_id = opp.contact_id
        book_id = opp.book_id

        if account_id and account_id not in valid_account_ids:
            capture_exception(Exception(f"Account with id {account_id} does not exist (opportunity {opp.id})"))
            skipped += 1
            continue
        if contact_id and contact_id not in valid_contact_ids:
            capture_exception(Exception(f"Contact with id {contact_id} does not exist (opportunity {opp.id})"))
            skipped += 1
            continue
        if book_id and book_id not in valid_book_ids:
            capture_exception(Exception(f"Book with id {book_id} does not exist (opportunity {opp.id})"))
            skipped += 1
            continue

        synced_ids.append(opp.id)
        records.append(
            Opportunity(
                id=opp.id,
                account_id=account_id,
                record_type_id=opp.record_type_id,
                name=opp.name,
                description=opp.description,
                stage_name=opp.stage_name,
                amount=opp.amount,
                probability=opp.probability,
                close_date=opp.close_date,
                type=opp.type,
                lead_source=opp.lead_source,
                is_closed=opp.is_closed,
                is_won=opp.is_won,
                owner_id=opp.owner_id,
                created_date=opp.created_date,
                created_by_id=opp.created_by_id,
                last_modified_date=opp.last_modified_date,
                last_modified_by_id=opp.last_modified_by_id,
                system_modstamp=opp.system_modstamp,
                last_activity_date=opp.last_activity_date,
                last_activity_in_days=opp.last_activity_in_days,
                last_stage_change_date=opp.last_stage_change_date,
                last_stage_change_in_days=opp.last_stage_change_in_days,
                fiscal_year=opp.fiscal_year,
                fiscal=opp.fiscal,
                contact_id=contact_id,
                last_viewed_date=opp.last_viewed_date,
                last_referenced_date=opp.last_referenced_date,
                book_id=book_id,
            )
        )

    with transaction.atomic():
        Opportunity.objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=["id"],
            update_fields=OPPORTUNITY_SYNC_FIELDS,
            batch_size=500,
        )

    logger.info(f"Opportunities sync: {len(records)} upserted, {skipped} skipped (full_sync={full_sync})")
    return len(records)


def update_or_create_adoptions(salesforce_adoptions, full_sync=False):
    """
    Bulk upsert adoptions into the local database using ON CONFLICT DO UPDATE.
    Validates FK references to contacts and opportunities before insert.
    """
    # Materialize the SF queryset once to avoid re-querying Salesforce
    salesforce_adoptions = list(salesforce_adoptions)

    # Only check FK IDs that are actually referenced in this batch
    ref_contact_ids = {a.contact_id for a in salesforce_adoptions if a.contact_id}
    ref_opportunity_ids = {a.opportunity_id for a in salesforce_adoptions if a.opportunity_id}

    valid_contact_ids = set(
        Contact.all_objects.filter(id__in=ref_contact_ids).values_list("id", flat=True)
    ) if ref_contact_ids else set()
    valid_opportunity_ids = set(
        Opportunity.objects.filter(id__in=ref_opportunity_ids).values_list("id", flat=True)
    ) if ref_opportunity_ids else set()

    records = []
    synced_ids = []
    skipped = 0

    for adoption in salesforce_adoptions:
        contact_id = adoption.contact_id
        opportunity_id = adoption.opportunity_id

        if contact_id and contact_id not in valid_contact_ids:
            capture_exception(Exception(f"Contact with id {contact_id} does not exist (adoption {adoption.id})"))
            skipped += 1
            continue
        if opportunity_id and opportunity_id not in valid_opportunity_ids:
            capture_exception(
                Exception(f"Opportunity with id {opportunity_id} does not exist (adoption {adoption.id})")
            )
            skipped += 1
            continue

        synced_ids.append(adoption.id)
        records.append(
            Adoption(
                id=adoption.id,
                contact_id=contact_id,
                adoption_number=adoption.adoption_number,
                created_date=adoption.created_date,
                last_modified_date=adoption.last_modified_date,
                system_modstamp=adoption.system_modstamp,
                last_activity_date=adoption.last_activity_date,
                class_start_date=adoption.class_start_date,
                opportunity_id=opportunity_id,
                confirmation_date=adoption.confirmation_date,
                name=adoption.name,
                base_year=adoption.base_year,
                adoption_type=adoption.adoption_type,
                students=adoption.students,
                school_year=adoption.school_year,
                terms_used=adoption.terms_used,
                confirmation_type=adoption.confirmation_type,
                how_using=adoption.how_using,
                savings=adoption.savings,
            )
        )

    with transaction.atomic():
        Adoption.objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=["id"],
            update_fields=ADOPTION_SYNC_FIELDS,
            batch_size=500,
        )

    logger.info(f"Adoptions sync: {len(records)} upserted, {skipped} skipped (full_sync={full_sync})")
    return len(records)


def update_or_create_books(salesforce_books, full_sync=False):
    """
    Bulk upsert books into the local database using ON CONFLICT DO UPDATE.
    On full sync, marks records not in the batch as soft-deleted.
    """
    records = []
    synced_ids = []
    for book in salesforce_books:
        synced_ids.append(book.id)
        records.append(
            Book(
                id=book.id,
                name=book.name,
                official_name=book.official_name,
                type=book.type,
                subject_areas=book.subject_areas,
                website_url=book.website_url,
                is_deleted=False,
            )
        )

    with transaction.atomic():
        Book.all_objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=["id"],
            update_fields=BOOK_SYNC_FIELDS + ["is_deleted"],
            batch_size=500,
        )
        if full_sync:
            Book.all_objects.exclude(id__in=synced_ids).update(is_deleted=True)

    logger.info(f"Books sync: {len(records)} upserted (full_sync={full_sync})")
    return len(records)
