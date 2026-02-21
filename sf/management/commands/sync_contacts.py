import datetime
import time
from django.core.management.base import BaseCommand
from sf.models.contact import Contact as SFContact
from db.models import Contact
from db.functions import update_or_create_contacts


class Command(BaseCommand):
    help = "sync contacts with the database, only fetch contacts that have been modified since the last sync"

    def add_arguments(self, parser):
        parser.add_argument('--force', action="store_true", help='Force a full sync of all contacts')
        parser.add_argument('--forcedelete', action="store_true", help='Force a full sync of and delete all contacts')

    def handle(self, *args, **options):
        start_time = time.time()

        full_sync = False
        if Contact.all_objects.count() < 100 or options['force'] or options['forcedelete']:
            salesforce_contacts = SFContact.objects.filter(verification_status__isnull=False,
                                                           accounts_uuid__isnull=False)
            full_sync = True
            self.stdout.write("Full sync, fetching all contacts")
            if options['forcedelete']:
                Contact.all_objects.all().delete()
                self.stdout.write("Deleted all local contacts")
        else:
            last_sync_object = Contact.all_objects.latest('last_modified_date')
            # Use 2-hour lookback buffer to avoid missing records due to clock skew
            delta = last_sync_object.last_modified_date - datetime.timedelta(hours=2)
            salesforce_contacts = (SFContact.objects.order_by('last_modified_date')
                                   .filter(verification_status__isnull=False,
                                           accounts_uuid__isnull=False,
                                           last_modified_date__gte=delta)
                                   )
            self.stdout.write(f"Incremental sync from {delta.isoformat()}")

        count = update_or_create_contacts(salesforce_contacts, full_sync=full_sync)
        duration = time.time() - start_time

        self.stdout.write(self.style.SUCCESS(
            f"Contacts synced successfully! {count} upserted. Duration: {duration:.1f}s"
        ))
