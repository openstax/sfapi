from .models import Contact, Account
from sentry_sdk import capture_exception

def update_or_create_contacts(salesforce_contacts):
    """
    Update or create contacts in the local database from a list of salesforce contacts
    :param salesforce_contacts:
    :return created: number of contacts created
    """
    created_count = 0
    for contact in salesforce_contacts:
        try:
            account = Account.objects.get(id=contact.account.id)
        except Account.DoesNotExist:
            capture_exception(Exception(f"Account with id {contact.accounts_id} does not exist"))
            continue

        db_contact, created = Contact.objects.update_or_create(
            id=contact.id,
            defaults={
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "full_name": contact.full_name,
                "email": contact.email,
                "role": contact.role,
                "position": contact.position,
                "title": contact.title,
                "account": account,
                "adoption_status": contact.adoption_status,
                "verification_status": contact.verification_status,
                "accounts_uuid": contact.accounts_uuid,
                "accounts_id": contact.accounts_id,
                "signup_date": contact.signup_date,
                "lead_source": contact.lead_source,
                "lms": contact.lms,
                "last_modified_date": contact.last_modified_date
            },
        )
        if created:
            created_count += 1
    return created_count


def update_or_create_accounts(salesforce_accounts):
    """
    Update or create accounts in the local database from a list of salesforce accounts
    :param salesforce_accounts:
    :return created: number of accounts created
    """
    created_count = 0
    for account in salesforce_accounts:
        db_account, created = Account.objects.update_or_create(
            id=account.id,
            defaults={
                "name": account.name,
                "type": account.type,
                "country": account.country,
                "state": account.state,
                "city": account.city,
                "country_code": account.country_code,
                "state_code": account.state_code,
                "created_date": account.created_date,
                "last_modified_date": account.last_modified_date,
                "last_activity_date": account.last_activity_date,
                "lms": account.lms,
                "books_adopted": account.books_adopted,
                "sheer_id_school_name": account.sheer_id_school_name,
                "ipeds_id": account.ipeds_id,
                "nces_id": account.nces_id,
            },
        )
        if created:
            created_count += 1
    return created_count
