from django.core.management.base import BaseCommand

from sf.models.account import Account as SFAccount
from db.models import Account


class Command(BaseCommand):
    help = "sync books with the local database"

    def handle(self, *labels, **options):
        salesforce_accounts = SFAccount.objects.all()
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
        self.stdout.write(self.style.SUCCESS("Accounts synced successfully!"))

