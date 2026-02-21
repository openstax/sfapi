import datetime
import time
from django.core.management.base import BaseCommand
from sf.models.adoption import Adoption as SFAdoption
from db.models import Adoption
from db.functions import update_or_create_adoptions


class Command(BaseCommand):
    help = "sync adoptions with the database, only fetch adoptions that have been modified since the last sync"

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force a full sync of all adoptions')
        parser.add_argument('--forcedelete', action='store_true', help='Force a full sync and delete all adoptions')

    def handle(self, *args, **options):
        start_time = time.time()

        full_sync = False
        if Adoption.objects.count() < 100 or options['force'] or options['forcedelete']:
            salesforce_adoptions = SFAdoption.objects.all()
            full_sync = True
            self.stdout.write("Full sync, fetching all adoptions")
            if options['forcedelete']:
                Adoption.objects.all().delete()
                self.stdout.write("Deleted all local adoptions")
        else:
            last_sync_object = Adoption.objects.latest('last_modified_date')
            # Use 2-hour lookback buffer to avoid missing records due to clock skew
            delta = last_sync_object.last_modified_date - datetime.timedelta(hours=2)
            salesforce_adoptions = SFAdoption.objects.order_by('last_modified_date').filter(last_modified_date__gte=delta)
            self.stdout.write(f"Incremental sync from {delta.isoformat()}")

        count = update_or_create_adoptions(salesforce_adoptions, full_sync=full_sync)
        duration = time.time() - start_time

        self.stdout.write(self.style.SUCCESS(
            f"Adoptions synced successfully! {count} upserted. Duration: {duration:.1f}s"
        ))
