from django.core.management.base import BaseCommand
from sf.models.account import Account as SFAccount
from db.models import Account
from db.functions import update_or_create_accounts
from django.utils import timezone

class Command(BaseCommand):
    help = "sync accounts (schools) with the local database, only fetch accounts that have been modified since the last sync"
    # TODO: this needs to know if an account was deleted in salesforce and delete it in the local db

    def add_arguments(self, parser):
        parser.add_argument('labels', nargs='*', type=str)
        parser.add_argument('--force', action='store_true', help='Force a full sync of all accounts')
        parser.add_argument('--forcedelete', action='store_true', help='Force a full sync of and delete all accounts')

    def handle(self, *labels, **options):
        if Account.objects.count() < 100 or options['force'] or options['forcedelete']:
            salesforce_accounts = SFAccount.objects.all()
            self.stdout.write(f"Full sync, fetching all accounts ({salesforce_accounts.count()} total)")
            if options['force-and-delete']:
                Account.objects.all().delete()
        else:
            last_sync_object = Account.objects.latest('last_modified_date')
            delta = last_sync_object.last_modified_date - timezone.timedelta(1)
            salesforce_accounts = SFAccount.objects.order_by('last_modified_date').filter(last_modified_date__gte=delta)
            self.stdout.write(f"Incremental Sync, fetching {salesforce_accounts.count()}")
        created_count = update_or_create_accounts(salesforce_accounts)

        self.stdout.write(self.style.SUCCESS(f"Accounts synced successfully! {created_count} created."))

