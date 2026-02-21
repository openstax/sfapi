from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.auth import APIKey


class Command(BaseCommand):
    help = 'Create a new API key for service-to-service authentication'

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True, help='Human-readable name for the key (e.g. "kinetic-service")')
        parser.add_argument('--scopes', required=True, help='Comma-separated scopes (e.g. "read:books,write:cases")')
        parser.add_argument('--expires-days', type=int, default=None, help='Number of days until key expires (default: never)')
        parser.add_argument('--created-by', default='', help='Who is creating this key')

    def handle(self, *args, **options):
        name = options['name']
        scopes = [s.strip() for s in options['scopes'].split(',')]
        expires_at = None
        if options['expires_days']:
            expires_at = timezone.now() + timedelta(days=options['expires_days'])

        api_key, raw_key = APIKey.create_key(
            name=name,
            scopes=scopes,
            expires_at=expires_at,
            created_by=options['created_by'],
        )

        self.stdout.write(self.style.SUCCESS(f'API key created successfully:'))
        self.stdout.write(f'  Name:    {api_key.name}')
        self.stdout.write(f'  Prefix:  {api_key.key_prefix}...')
        self.stdout.write(f'  Scopes:  {", ".join(api_key.scopes)}')
        self.stdout.write(f'  Expires: {api_key.expires_at or "Never"}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('  SAVE THIS KEY - it cannot be retrieved later:'))
        self.stdout.write(f'  {raw_key}')
