import time

from django.core.management import call_command
from django.core.management.base import BaseCommand

from sf.api_usage import should_sync


class Command(BaseCommand):
    help = (
        "Run all interdependent syncs in order: accounts → contacts → opportunities → adoptions. "
        "Ensures FK dependencies are satisfied and applies the kill switch / API usage check once."
    )

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Force a full sync of all objects")
        parser.add_argument("--forcedelete", action="store_true", help="Force a full sync and delete all objects")

    def handle(self, *args, **options):
        allowed, reason = should_sync(command=self)
        if not allowed:
            return

        start_time = time.time()
        force = options["force"]
        forcedelete = options["forcedelete"]

        # Build args to pass through to sub-commands
        sub_args = []
        if force:
            sub_args.append("--force")
        if forcedelete:
            sub_args.append("--forcedelete")

        # Each sub-command tracks its own SF API calls via track_sf_calls.
        # We don't wrap them here to avoid double-counting from nested execute_wrappers.
        steps = ["sync_accounts", "sync_contacts", "sync_opportunities", "sync_adoptions"]

        for step in steps:
            self.stdout.write(self.style.MIGRATE_HEADING(f"--- {step} ---"))
            call_command(step, *sub_args, "--skip-usage-check", stdout=self.stdout, stderr=self.stderr)

        duration = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(f"\nAll syncs complete! Duration: {duration:.1f}s")
        )
