import datetime
import time
from django.core.management.base import BaseCommand
from sf.models.opportunity import Opportunity as SFOpportunity
from db.models import Opportunity
from db.functions import update_or_create_opportunities


class Command(BaseCommand):
    help = "sync opportunities with the database, only fetch opportunities that have been modified since the last sync"

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force a full sync of all opportunities')
        parser.add_argument('--forcedelete', action='store_true', help='Force a full sync and delete all opportunities')

    def handle(self, *args, **options):
        start_time = time.time()

        full_sync = False
        if Opportunity.objects.count() < 100 or options['force'] or options['forcedelete']:
            salesforce_opportunities = SFOpportunity.objects.all()
            full_sync = True
            self.stdout.write("Full sync, fetching all opportunities")
            if options['forcedelete']:
                Opportunity.objects.all().delete()
                self.stdout.write("Deleted all local opportunities")
        else:
            last_sync_object = Opportunity.objects.latest('last_modified_date')
            # Use 2-hour lookback buffer to avoid missing records due to clock skew
            delta = last_sync_object.last_modified_date - datetime.timedelta(hours=2)
            salesforce_opportunities = SFOpportunity.objects.order_by('last_modified_date').filter(last_modified_date__gte=delta)
            self.stdout.write(f"Incremental sync from {delta.isoformat()}")

        count = update_or_create_opportunities(salesforce_opportunities, full_sync=full_sync)
        duration = time.time() - start_time

        self.stdout.write(self.style.SUCCESS(
            f"Opportunities synced successfully! {count} upserted. Duration: {duration:.1f}s"
        ))
