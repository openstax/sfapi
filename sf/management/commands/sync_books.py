import time
from django.core.management.base import BaseCommand
from django.db import transaction
from sf.models.book import Book as SFBook
from db.models import Book


class Command(BaseCommand):
    help = "sync books with the local database"

    def handle(self, *labels, **options):
        start_time = time.time()

        salesforce_books = SFBook.objects.all()
        existing_ids = set(Book.objects.values_list('id', flat=True))
        to_create = []
        to_update = []

        for book in salesforce_books:
            db_book = Book(
                id=book.id,
                name=book.name,
                official_name=book.official_name,
                type=book.type,
                subject_areas=book.subject_areas,
                website_url=book.website_url,
            )
            if book.id in existing_ids:
                to_update.append(db_book)
            else:
                to_create.append(db_book)

        with transaction.atomic():
            if to_create:
                Book.objects.bulk_create(to_create, batch_size=500)
            if to_update:
                Book.objects.bulk_update(
                    to_update,
                    fields=['name', 'official_name', 'type', 'subject_areas', 'website_url'],
                    batch_size=500,
                )

        duration = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f"Books synced successfully! {len(to_create)} created, {len(to_update)} updated. Duration: {duration:.1f}s"
        ))
