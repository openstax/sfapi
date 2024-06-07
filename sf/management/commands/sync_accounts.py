from django.core.management.base import BaseCommand

from sf.models.account import Account as SFAccount
from db.models import Account
from django.utils import timezone

class Command(BaseCommand):
    help = "sync books with the local database"

    def update_or_create_account(self, salesforce_accounts):
        for account in salesforce_accounts:
            Account.objects.update_or_create(
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

    def handle(self, *labels, **options):
        # we only need to update accounts that have been changed in the last 30 days
        # TODO: daily cron should be even less delta
        if Account.objects.count() == 0:
            salesforce_accounts = SFAccount.objects.all()
            self.stdout.write(f"First sync, fetching all accounts ({salesforce_accounts.count()} total)")
        else:
            delta = timezone.now() - timezone.timedelta(30)
            salesforce_accounts = SFAccount.objects.order_by('last_modified_date').filter(last_modified_date__gte=delta)
            self.stdout.write(f"Incremental Sync, fetching {salesforce_accounts.count()}")
        self.update_or_create_account(salesforce_accounts)

        self.stdout.write(self.style.SUCCESS("Accounts synced successfully!"))

