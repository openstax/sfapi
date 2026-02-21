import datetime
import time
from django.core.management.base import BaseCommand
from sf.models.account import Account as SFAccount
from db.models import Account
from db.functions import update_or_create_accounts


class Command(BaseCommand):
    help = "sync accounts (schools) with the database, only fetch accounts that have been modified since the last sync"

    def add_arguments(self, parser):
        parser.add_argument('labels', nargs='*', type=str)
        parser.add_argument('--force', action='store_true', help='Force a full sync of all accounts')
        parser.add_argument('--forcedelete', action='store_true', help='Force a full sync of and delete all accounts')

    def handle(self, *labels, **options):
        start_time = time.time()

        full_sync = False
        if Account.all_objects.count() < 100 or options['force'] or options['forcedelete']:
            salesforce_accounts = SFAccount.objects.all()
            full_sync = True
            self.stdout.write("Full sync, fetching all accounts")
            if options['forcedelete']:
                Account.all_objects.all().delete()
                self.stdout.write("Deleted all local accounts")
        else:
            last_sync_object = Account.all_objects.latest('last_modified_date')
            # Use 2-hour lookback buffer to avoid missing records due to clock skew
            delta = last_sync_object.last_modified_date - datetime.timedelta(hours=2)
            salesforce_accounts = SFAccount.objects.order_by('last_modified_date').filter(last_modified_date__gte=delta)
            self.stdout.write(f"Incremental sync from {delta.isoformat()}")

        count = update_or_create_accounts(salesforce_accounts, full_sync=full_sync)
        duration = time.time() - start_time

        self.stdout.write(self.style.SUCCESS(
            f"Accounts synced successfully! {count} upserted. Duration: {duration:.1f}s"
        ))
