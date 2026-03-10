import datetime
import time

from django.core.management.base import BaseCommand

from db.functions import ADOPTION_SYNC_FIELDS, update_or_create_adoptions
from db.models import Adoption
from sf.api_usage import should_sync, track_sf_calls
from sf.models.adoption import Adoption as SFAdoption

# Only fetch the fields we actually sync (plus id)
# contact_id/opportunity_id in ADOPTION_SYNC_FIELDS map to FK field names on the SF model
SF_ONLY_FIELDS = ["id"] + [f.removesuffix("_id") if f.endswith("_id") else f for f in ADOPTION_SYNC_FIELDS]


class Command(BaseCommand):
    help = "sync adoptions with the database, only fetch adoptions that have been modified since the last sync"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Force a full sync of all adoptions")
        parser.add_argument("--forcedelete", action="store_true", help="Force a full sync and delete all adoptions")
        parser.add_argument(
            "--skip-usage-check", action="store_true", help="Skip the API usage/kill switch check (used by sync_all)"
        )

    def handle(self, *args, **options):
        if not options.get("skip_usage_check"):
            allowed, reason = should_sync(command=self)
            if not allowed:
                return

        start_time = time.time()

        full_sync = False
        if Adoption.objects.count() < 100 or options["force"] or options["forcedelete"]:
            salesforce_adoptions = SFAdoption.objects.only(*SF_ONLY_FIELDS).all()
            full_sync = True
            self.stdout.write("Full sync, fetching all adoptions")
            if options["forcedelete"]:
                Adoption.objects.all().delete()
                self.stdout.write("Deleted all local adoptions")
        else:
            last_sync_object = Adoption.objects.latest("last_modified_date")
            # Use 2-hour lookback buffer to avoid missing records due to clock skew
            delta = last_sync_object.last_modified_date - datetime.timedelta(hours=2)
            salesforce_adoptions = (
                SFAdoption.objects.only(*SF_ONLY_FIELDS)
                .order_by("last_modified_date")
                .filter(last_modified_date__gte=delta)
            )
            self.stdout.write(f"Incremental sync from {delta.isoformat()}")

        with track_sf_calls("sync_adoptions") as counter:
            count = update_or_create_adoptions(salesforce_adoptions, full_sync=full_sync)
        duration = time.time() - start_time

        self.stdout.write(
            self.style.SUCCESS(
                f"Adoptions synced successfully! {count} upserted, {counter[0]} SF API calls. Duration: {duration:.1f}s"
            )
        )
