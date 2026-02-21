import time
from django.core.management.base import BaseCommand
from sf.models.book import Book as SFBook
from db.functions import update_or_create_books


class Command(BaseCommand):
    help = "sync books with the local database"

    def handle(self, *labels, **options):
        start_time = time.time()

        salesforce_books = SFBook.objects.all()
        count = update_or_create_books(salesforce_books, full_sync=True)

        duration = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f"Books synced successfully! {count} upserted. Duration: {duration:.1f}s"
        ))
