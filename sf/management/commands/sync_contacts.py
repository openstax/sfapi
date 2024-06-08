from django.core.management.base import BaseCommand

from sf.models.contact import Contact as SFContact
from db.models import Contact, Account
from db.functions import update_or_create_contacts
from django.utils import timezone
from sentry_sdk import capture_exception

class Command(BaseCommand):
    help = "sync contacts with the local database, only fetch contacts that have been modified 1 day prior to the last sync"
    # TODO: this needs to know if a contact was deleted in salesforce and delete it in the local db

    def handle(self, *labels, **options):
        last_sync_object = Contact.objects.latest('last_modified_date')

        if Contact.objects.count() < 100:  # the first sync needs to grab them all
            salesforce_contacts = SFContact.objects.filter(verification_status__isnull=False, accounts_uuid__isnull=False)
            self.stdout.write(f"First sync, fetching all contacts ({salesforce_contacts.count()} total)")
        else:
            delta = last_sync_object.last_modified_date - timezone.timedelta(1)
            salesforce_contacts = (SFContact.objects.order_by('last_modified_date')
                                   .filter(verification_status__isnull=False,
                                           accounts_uuid__isnull=False,
                                           last_modified_date__gte=delta)
                                   )
            self.stdout.write(f"Incremental Sync, fetching {salesforce_contacts.count()}")
        created_count = update_or_create_contacts(salesforce_contacts)

        self.stdout.write(self.style.SUCCESS(f"Contacts synced successfully! {created_count} created."))

