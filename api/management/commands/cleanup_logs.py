from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import RequestLog, FieldChangeLog


class Command(BaseCommand):
    help = 'Clean up old audit logs. Prunes request logs older than 90 days and field change logs older than 1 year.'

    def add_arguments(self, parser):
        parser.add_argument('--request-days', type=int, default=90, help='Delete request logs older than N days (default: 90)')
        parser.add_argument('--change-days', type=int, default=365, help='Delete field change logs older than N days (default: 365)')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting')

    def handle(self, *args, **options):
        request_cutoff = timezone.now() - timedelta(days=options['request_days'])
        change_cutoff = timezone.now() - timedelta(days=options['change_days'])

        request_count = RequestLog.objects.filter(timestamp__lt=request_cutoff).count()
        change_count = FieldChangeLog.objects.filter(timestamp__lt=change_cutoff).count()

        if options['dry_run']:
            self.stdout.write(f"Would delete {request_count} request logs older than {options['request_days']} days")
            self.stdout.write(f"Would delete {change_count} field change logs older than {options['change_days']} days")
            return

        if request_count:
            RequestLog.objects.filter(timestamp__lt=request_cutoff).delete()
        if change_count:
            FieldChangeLog.objects.filter(timestamp__lt=change_cutoff).delete()

        self.stdout.write(self.style.SUCCESS(
            f"Cleaned up {request_count} request logs and {change_count} field change logs"
        ))
