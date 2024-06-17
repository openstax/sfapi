from django.core.management.base import BaseCommand, CommandError
from sf.models.contact import Contact as SFContact
from db.models import Contact
from db.functions import update_or_create_contacts
from django.utils import timezone

class Command(BaseCommand):
    help = "sync contacts with the database, only fetch contacts that have been modified 1 day prior to the last sync"
    # TODO: this needs to know if a contact was deleted in salesforce and delete it in the local db

    def add_arguments(self, parser):
        parser.add_argument('--force', action="store_true", help='Force a full sync of all contacts')
        parser.add_argument('--forcedelete', action="store_true", help='Force a full sync of and delete all contacts')

    def handle(self, *args, **options):
        if Contact.objects.count() < 100 or options['force'] or options['forcedelete']:
            salesforce_contacts = SFContact.objects.filter(verification_status__isnull=False,
                                                           accounts_uuid__isnull=False)
            self.stdout.write(f"Full sync, fetching all contacts ({salesforce_contacts.count()} total)")
            if options['forcedelete']:
                Contact.objects.all().delete()
        else:
            last_sync_object = Contact.objects.latest('last_modified_date')
            # TODO: we only need the delta if we are being more smart about the number of contacts we are fetching
            # TODO: for example, modify to ignore records updated by B2BMA
            delta = last_sync_object.last_modified_date  # - timezone.timedelta(1)
            salesforce_contacts = (SFContact.objects.order_by('last_modified_date')
                                   .filter(verification_status__isnull=False,
                                           accounts_uuid__isnull=False,
                                           last_modified_date__gte=delta)
                                   )
            self.stdout.write(f"Incremental Sync, fetching {salesforce_contacts.count()}")
        created_count = update_or_create_contacts(salesforce_contacts)

        self.stdout.write(self.style.SUCCESS(f"Contacts synced successfully! {created_count} created."))

