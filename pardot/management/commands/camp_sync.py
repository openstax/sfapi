"""
Django management command for Camp Campaign sync operations.

Usage:
    manage.py camp_sync                         # Tier 1: assets + SF health
    manage.py camp_sync --scout                 # Tier 2: + top prospects
    manage.py camp_sync --survey                # Tier 3: full sync (prompts)
    manage.py camp_sync --entities forms,lists  # Selective sync
    manage.py camp_sync --entities sf_health    # Just SF health
    manage.py camp_sync --full                  # Force full re-sync
    manage.py camp_sync --days 7               # Activity window
"""

import logging

from django.core.management.base import BaseCommand

log = logging.getLogger("camp.sync")


class Command(BaseCommand):
    help = "Sync Pardot/SF data for Camp Campaign health tracking"

    def add_arguments(self, parser):
        parser.add_argument("--scout", action="store_true", help="Tier 2: include top 500 prospects")
        parser.add_argument("--survey", action="store_true", help="Tier 3: full prospect + activity sync")
        parser.add_argument("--entities", type=str, help="Comma-separated entity types to sync")
        parser.add_argument("--full", action="store_true", help="Force full re-sync")
        parser.add_argument("--skip-assets", action="store_true", help="Skip asset sync (survey only)")
        parser.add_argument("--force-assets", action="store_true", help="Force asset re-sync")
        parser.add_argument("--days", type=int, default=30, help="Activity lookback days")
        parser.add_argument("--debug", action="store_true", help="Debug logging")

    def handle(self, *args, **options):
        if options["debug"]:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        from pardot.pardot_client import PardotClient, get_sf_client
        from pardot.sync import SyncEngine

        pardot = PardotClient()
        conn = None  # Django manages connections

        # Selective sync
        if options["entities"]:
            entities = []
            for raw in options["entities"].split(","):
                name = raw.strip()
                name = SyncEngine.ENTITY_ALIASES.get(name, name)
                if name in SyncEngine.ENTITY_GROUPS:
                    entities.extend(SyncEngine.ENTITY_GROUPS[name])
                else:
                    entities.append(name)

            sf = None
            sf_entities = {
                "sf_health",
                "sf_campaign_dates",
                "scoring_categories",
                "campaign_member_counts",
                "campaign_members",
            }
            if any(e in sf_entities for e in entities):
                sf = get_sf_client()

            engine = SyncEngine(pardot, conn)
            for entity in entities:
                try:
                    count = engine.sync_one(entity, force_full=options["full"], sf=sf, days=options["days"])
                    self.stdout.write(f"  {entity}: {count} records")
                except Exception as e:
                    self.stderr.write(f"  {entity}: FAILED — {e}")
            return

        sf = get_sf_client()
        engine = SyncEngine(pardot, conn)

        # Tier 3: Full Survey
        if options["survey"]:
            if not options["full"]:
                self.stdout.write("Tier 3 Full Survey — this will make ~2500+ API calls.")
                confirm = input("Continue? [y/N] ")
                if confirm.lower() != "y":
                    self.stdout.write("Aborted.")
                    return

            if not options["skip_assets"]:
                engine.sync_assets(force_full=options["force_assets"])
                engine.sync_tags()
                SyncEngine.sync_sf_health(sf, conn)
                SyncEngine.sync_sf_campaign_dates(sf, conn)
                SyncEngine.sync_campaign_member_counts(sf, conn)

            engine.sync_prospects(force_full=options["full"])
            engine.sync_activities(days=options["days"], force_full=options["full"])
            SyncEngine.sync_scoring_categories(sf, conn)
            SyncEngine.sync_campaign_members(sf, conn)
            SyncEngine.save_daily_snapshot(conn, tier=3)
            self.stdout.write(self.style.SUCCESS("Tier 3 Full Survey complete."))
            return

        # Tier 2: Scout
        if options["scout"]:
            engine.sync_assets(force_full=options["force_assets"])
            engine.sync_tags()
            SyncEngine.sync_sf_health(sf, conn)
            SyncEngine.sync_sf_campaign_dates(sf, conn)
            SyncEngine.sync_campaign_member_counts(sf, conn)
            engine.sync_top_prospects(limit=500)
            SyncEngine.sync_scoring_categories(sf, conn)
            SyncEngine.sync_campaign_members(sf, conn)
            SyncEngine.save_daily_snapshot(conn, tier=2)
            self.stdout.write(self.style.SUCCESS("Tier 2 Scout complete."))
            return

        # Tier 1: Set Up Camp (default)
        engine.sync_assets(force_full=options["full"])
        engine.sync_tags()
        SyncEngine.sync_sf_health(sf, conn)
        SyncEngine.sync_sf_campaign_dates(sf, conn)
        SyncEngine.sync_campaign_member_counts(sf, conn)
        SyncEngine.save_daily_snapshot(conn, tier=1)
        self.stdout.write(self.style.SUCCESS("Tier 1 Set Up Camp complete."))
