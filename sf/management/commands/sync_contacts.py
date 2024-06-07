from django.core.management.base import BaseCommand

from sf.models.contact import Contact as SFContact
from db.models import Contact
from django.utils import timezone

from sf.utils import lazy_bulk_fetch

class Command(BaseCommand):
    help = "sync books with the local database"

    def update_or_create_contact(self, salesforce_contacts):
        for contact in salesforce_contacts:
            Contact.objects.update_or_create(
                id=contact.id,
                defaults={
                    "first_name": contact.first_name,
                    "last_name": contact.last_name,
                    "full_name": contact.full_name,
                    "email": contact.email,
                    "role": contact.role,
                    "position": contact.position,
                    "title": contact.title,
                    "account": contact.account,
                    "adoption_status": contact.adoption_status,
                    "verification_status": contact.verification_status,
                    "accounts_uuid": contact.accounts_uuid,
                    "accounts_id": contact.accounts_id,
                    "signup_date": contact.signup_date,
                    "lead_source": contact.lead_source,
                    "lms": contact.lms,
                    "last_modified_date": contact.last_modified_date,
                    "subject_interest": contact.subject_interest,
                },
            )

    def handle(self, *labels, **options):
        # we only need to update contacts that have been changed in the last 30 days
        # TODO: daily cron should be even less delta
        if Contact.objects.count() == 0:  # the first sync needs to grab them all
            salesforce_contacts = SFContact.objects.filter(verification_status__isnull=False)
            self.stdout.write(f"First sync, fetching all contacts ({salesforce_contacts.count()} total)")
        else:
            salesforce_contacts = SFContact.objects.order_by('last_modified_date').filter(verification_status__isnull=False, last_modified_date__gte=timezone.now() - timezone.timedelta(30))
            self.stdout.write(f"Incremental Sync, fetching {salesforce_contacts.count()}")
        self.update_or_create_contact(salesforce_contacts)

        self.stdout.write(self.style.SUCCESS("Contacts synced successfully!"))

