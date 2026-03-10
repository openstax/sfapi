import time

from django.core.management.base import BaseCommand

from db.functions import BOOK_SYNC_FIELDS, update_or_create_books
from sf.api_usage import should_sync
from sf.models.book import Book as SFBook

SF_ONLY_FIELDS = ["id"] + BOOK_SYNC_FIELDS


class Command(BaseCommand):
    help = "sync books with the local database"

    def handle(self, *args, **options):
        allowed, reason = should_sync(command=self)
        if not allowed:
            return

        start_time = time.time()

        salesforce_books = SFBook.objects.only(*SF_ONLY_FIELDS).all()
        count = update_or_create_books(salesforce_books, full_sync=True)

        duration = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"Books synced successfully! {count} upserted. Duration: {duration:.1f}s"))
