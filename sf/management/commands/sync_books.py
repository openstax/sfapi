from django.core.management.base import BaseCommand

from sf.models.book import Book as SFBook
from db.models import Book


class Command(BaseCommand):
    help = "sync books with the local database"

    def handle(self, *labels, **options):
        salesforce_books = SFBook.objects.all()
        for book in salesforce_books:
            Book.objects.update_or_create(
                id=book.id,
                defaults={
                    "name": book.name,
                    "official_name": book.official_name,
                    "type": book.type,
                    "subject_areas": book.subject_areas,
                    "website_url": book.website_url,
                },
            )
        self.stdout.write(self.style.SUCCESS("Books synced successfully!"))
