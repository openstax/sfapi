from os import environ

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.utils import OperationalError

class Command(BaseCommand):
    help = 'Creates the application user role and the database or migrates the database'

    def handle(self, *args, **options):
        for variable in ('RDS_SUPERUSER_USERNAME', 'RDS_SUPERUSER_PASSWORD'):
            if not environ.get(variable):
                raise CommandError(f"{variable} environment variable missing")

        default_db = settings.DATABASES['default']

        # Save for later use
        user = default_db['USER']
        password = default_db['PASSWORD']

        # We need to overwrite the default DB rather than creating a new entry
        # because some migrations fail to use the correct DB
        # when specified in the migrate command and get deadlocked
        default_db['USER'] = environ['RDS_SUPERUSER_USERNAME']
        default_db['PASSWORD'] = environ['RDS_SUPERUSER_PASSWORD']

        try:
            # Migrate as the superuser
            call_command('migrate', interactive=False)
        except OperationalError as err:
            if not f"database \"{default_db['NAME']}\" does not exist" in str(err):
                raise

            # Database does not exist, so attempt to connect to postgres DB and create it
            settings.DATABASES['postgres'] = default_db.copy()
            settings.DATABASES['postgres']['NAME'] = 'postgres'
            with connections['postgres'].schema_editor(atomic=False) as schema_editor:
                schema_editor.execute(f"CREATE DATABASE {default_db['NAME']} ENCODING 'UTF8'")

            # Create the database user and grant permissions
            with connections['default'].schema_editor() as schema_editor:
                schema_editor.execute(f"CREATE USER {user} PASSWORD '{password}'")
                schema_editor.execute(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public " \
                    f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {user}"
                )
                schema_editor.execute(
                    f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO {user}"
                )
                schema_editor.execute(
                    f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {user}"
                )
                schema_editor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {user}")

            # Attempt to migrate again as the superuser
            call_command('migrate', interactive=False)
