from datetime import timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from api.models import RequestLog
from db.models import Account, Contact


class CleanupLogsCommandTest(TestCase):
    def _create_old_request_log(self, days_old=100):
        log = RequestLog.objects.create(method="GET", path="/api/v1/schools", status_code=200, duration_ms=10)
        # auto_now_add prevents setting timestamp on create; update it directly
        RequestLog.objects.filter(pk=log.pk).update(timestamp=timezone.now() - timedelta(days=days_old))
        return log

    def test_dry_run(self):
        self._create_old_request_log(100)
        out = StringIO()
        call_command("cleanup_logs", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("Would delete 1 request logs", output)
        self.assertEqual(RequestLog.objects.count(), 1)  # Not deleted

    def test_cleanup_old_logs(self):
        self._create_old_request_log(100)
        RequestLog.objects.create(method="GET", path="/api/v1/contact", status_code=200, duration_ms=5)
        out = StringIO()
        call_command("cleanup_logs", stdout=out)
        self.assertIn("Cleaned up", out.getvalue())
        self.assertEqual(RequestLog.objects.count(), 1)

    def test_cleanup_no_old_logs(self):
        out = StringIO()
        call_command("cleanup_logs", stdout=out)
        self.assertIn("Cleaned up 0 request logs", out.getvalue())


class CreateApiKeyCommandTest(TestCase):
    def test_create_key(self):
        out = StringIO()
        call_command("create_api_key", "--name=test-key", "--scopes=read:books,write:cases", stdout=out)
        output = out.getvalue()
        self.assertIn("API key created successfully", output)
        self.assertIn("test-key", output)
        self.assertIn("read:books", output)

    def test_create_key_with_expiry(self):
        out = StringIO()
        call_command(
            "create_api_key",
            "--name=expiring-key",
            "--scopes=read:books",
            "--expires-days=30",
            "--created-by=admin",
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn("expiring-key", output)
        self.assertNotIn("Never", output)


MOCK_SHOULD_SYNC = (True, "ok")


class SyncAccountsCommandTest(TestCase):
    @patch("sf.management.commands.sync_accounts.should_sync", return_value=MOCK_SHOULD_SYNC)
    @patch("sf.management.commands.sync_accounts.SFAccount")
    @patch("sf.management.commands.sync_accounts.update_or_create_accounts")
    def test_full_sync_force(self, mock_sync, mock_sf, _):
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_accounts", "--force", stdout=out)
        mock_sync.assert_called_once()
        self.assertTrue(mock_sync.call_args[1]["full_sync"])
        self.assertIn("synced successfully", out.getvalue())

    @patch("sf.management.commands.sync_accounts.should_sync", return_value=MOCK_SHOULD_SYNC)
    @patch("sf.management.commands.sync_accounts.SFAccount")
    @patch("sf.management.commands.sync_accounts.update_or_create_accounts")
    def test_forcedelete(self, mock_sync, mock_sf, _):
        # Create some accounts to be deleted
        Account.all_objects.create(id="001000000000001", name="Test", last_modified_date=timezone.now())
        mock_sf.objects.all.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_accounts", "--forcedelete", stdout=out)
        self.assertIn("Deleted all local accounts", out.getvalue())

    @patch("sf.management.commands.sync_accounts.should_sync", return_value=MOCK_SHOULD_SYNC)
    @patch("sf.management.commands.sync_accounts.SFAccount")
    @patch("sf.management.commands.sync_accounts.update_or_create_accounts")
    def test_incremental_sync(self, mock_sync, mock_sf, _):
        # Create enough accounts to trigger incremental
        for i in range(101):
            Account.all_objects.create(
                id=f"001{i:015d}",
                name=f"School {i}",
                last_modified_date=timezone.now(),
            )
        mock_queryset = MagicMock()
        mock_sf.objects.order_by.return_value.filter.return_value = mock_queryset
        mock_sync.return_value = 5
        out = StringIO()
        call_command("sync_accounts", stdout=out)
        self.assertIn("Incremental sync", out.getvalue())


class SyncContactsCommandTest(TestCase):
    @patch("sf.management.commands.sync_contacts.should_sync", return_value=MOCK_SHOULD_SYNC)
    @patch("sf.management.commands.sync_contacts.SFContact")
    @patch("sf.management.commands.sync_contacts.update_or_create_contacts")
    def test_full_sync_force(self, mock_sync, mock_sf, _):
        mock_sf.objects.filter.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_contacts", "--force", stdout=out)
        mock_sync.assert_called_once()
        self.assertIn("synced successfully", out.getvalue())

    @patch("sf.management.commands.sync_contacts.should_sync", return_value=MOCK_SHOULD_SYNC)
    @patch("sf.management.commands.sync_contacts.SFContact")
    @patch("sf.management.commands.sync_contacts.update_or_create_contacts")
    def test_forcedelete(self, mock_sync, mock_sf, _):
        Contact.all_objects.create(
            id="003000000000001",
            first_name="T",
            last_name="U",
            full_name="T U",
            email="t@t.com",
            verification_status="confirmed",
            accounts_uuid="uuid",
            last_modified_date=timezone.now(),
        )
        mock_sf.objects.filter.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_contacts", "--forcedelete", stdout=out)
        self.assertIn("Deleted all local contacts", out.getvalue())

    @patch("sf.management.commands.sync_contacts.should_sync", return_value=MOCK_SHOULD_SYNC)
    @patch("sf.management.commands.sync_contacts.SFContact")
    @patch("sf.management.commands.sync_contacts.update_or_create_contacts")
    def test_incremental_sync(self, mock_sync, mock_sf, _):
        for i in range(101):
            Contact.all_objects.create(
                id=f"003{i:015d}",
                first_name="T",
                last_name="U",
                full_name="T U",
                email=f"t{i}@t.com",
                verification_status="confirmed",
                accounts_uuid=f"uuid-{i}",
                last_modified_date=timezone.now(),
            )
        mock_queryset = MagicMock()
        mock_sf.objects.order_by.return_value.filter.return_value = mock_queryset
        mock_sync.return_value = 5
        out = StringIO()
        call_command("sync_contacts", stdout=out)
        self.assertIn("Incremental sync", out.getvalue())


class SyncOpportunitiesCommandTest(TestCase):
    @patch("sf.management.commands.sync_opportunities.should_sync", return_value=MOCK_SHOULD_SYNC)
    @patch("sf.management.commands.sync_opportunities.SFOpportunity")
    @patch("sf.management.commands.sync_opportunities.update_or_create_opportunities")
    def test_full_sync_force(self, mock_sync, mock_sf, _):
        mock_sf.objects.all.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_opportunities", "--force", stdout=out)
        mock_sync.assert_called_once()
        self.assertIn("synced successfully", out.getvalue())

    @patch("sf.management.commands.sync_opportunities.should_sync", return_value=MOCK_SHOULD_SYNC)
    @patch("sf.management.commands.sync_opportunities.SFOpportunity")
    @patch("sf.management.commands.sync_opportunities.update_or_create_opportunities")
    def test_forcedelete(self, mock_sync, mock_sf, _):
        mock_sf.objects.all.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_opportunities", "--forcedelete", stdout=out)
        self.assertIn("synced successfully", out.getvalue())


class SyncAdoptionsCommandTest(TestCase):
    @patch("sf.management.commands.sync_adoptions.should_sync", return_value=MOCK_SHOULD_SYNC)
    @patch("sf.management.commands.sync_adoptions.SFAdoption")
    @patch("sf.management.commands.sync_adoptions.update_or_create_adoptions")
    def test_full_sync_force(self, mock_sync, mock_sf, _):
        mock_sf.objects.all.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_adoptions", "--force", stdout=out)
        mock_sync.assert_called_once()
        self.assertIn("synced successfully", out.getvalue())


class SyncBooksCommandTest(TestCase):
    @patch("sf.management.commands.sync_books.should_sync", return_value=MOCK_SHOULD_SYNC)
    @patch("sf.management.commands.sync_books.SFBook")
    @patch("sf.management.commands.sync_books.update_or_create_books")
    def test_sync(self, mock_sync, mock_sf, _):
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_books", stdout=out)
        mock_sync.assert_called_once()
        self.assertIn("synced successfully", out.getvalue())


class SyncConfigTest(TestCase):
    def test_kill_switch_blocks_sync(self):
        """When sync_enabled=False, should_sync returns False."""
        from api.models import SyncConfig

        config = SyncConfig.get()
        config.sync_enabled = False
        config.save()

        from sf.api_usage import should_sync

        allowed, reason = should_sync()
        self.assertFalse(allowed)
        self.assertIn("kill switch", reason)

    @patch("sf.api_usage.get_sf_api_usage", return_value=(250000, 285000))
    def test_threshold_blocks_sync(self, mock_usage):
        """When API usage exceeds threshold, should_sync returns False."""
        from api.models import SyncConfig

        config = SyncConfig.get()
        config.pause_threshold = 0.85
        config.save()

        from sf.api_usage import should_sync

        allowed, reason = should_sync()
        self.assertFalse(allowed)
        self.assertIn("too high", reason)

    @patch("sf.api_usage.get_sf_api_usage", return_value=(100000, 285000))
    def test_below_threshold_allows_sync(self, mock_usage):
        """When API usage is below threshold, should_sync returns True."""
        from sf.api_usage import should_sync

        allowed, reason = should_sync()
        self.assertTrue(allowed)

    @patch("sf.api_usage.get_sf_api_usage", return_value=(None, None))
    def test_unavailable_usage_allows_sync(self, mock_usage):
        """When API usage can't be fetched, allow sync to proceed."""
        from sf.api_usage import should_sync

        allowed, reason = should_sync()
        self.assertTrue(allowed)


class SFAPIUsageLogTest(TestCase):
    def test_increment_creates_and_updates(self):
        from api.models import SFAPIUsageLog

        SFAPIUsageLog.increment("test_source", 5)
        log = SFAPIUsageLog.objects.get(source="test_source")
        self.assertEqual(log.call_count, 5)

        SFAPIUsageLog.increment("test_source", 3)
        log.refresh_from_db()
        self.assertEqual(log.call_count, 8)

    def test_separate_sources_tracked_independently(self):
        from api.models import SFAPIUsageLog

        SFAPIUsageLog.increment("source_a", 10)
        SFAPIUsageLog.increment("source_b", 20)
        self.assertEqual(SFAPIUsageLog.objects.get(source="source_a").call_count, 10)
        self.assertEqual(SFAPIUsageLog.objects.get(source="source_b").call_count, 20)


class SyncAllCommandTest(TestCase):
    @patch("sf.management.commands.sync_all.should_sync", return_value=MOCK_SHOULD_SYNC)
    @patch("sf.management.commands.sync_all.call_command")
    def test_runs_all_syncs_in_order(self, mock_call, mock_should):
        out = StringIO()
        call_command("sync_all", stdout=out)

        # Verify all 4 syncs were called in dependency order
        calls = [c[0][0] for c in mock_call.call_args_list]
        self.assertEqual(calls, ["sync_accounts", "sync_contacts", "sync_opportunities", "sync_adoptions"])

        # Verify --skip-usage-check was passed
        for c in mock_call.call_args_list:
            self.assertIn("--skip-usage-check", c[0])

    @patch("sf.management.commands.sync_all.should_sync", return_value=MOCK_SHOULD_SYNC)
    @patch("sf.management.commands.sync_all.call_command")
    def test_passes_force_flag(self, mock_call, mock_should):
        out = StringIO()
        call_command("sync_all", "--force", stdout=out)

        for c in mock_call.call_args_list:
            self.assertIn("--force", c[0])

    @patch("sf.management.commands.sync_all.call_command")
    @patch(
        "sf.management.commands.sync_all.should_sync", return_value=(False, "Sync is disabled via admin kill switch.")
    )
    def test_kill_switch_stops_all(self, mock_should, mock_call):
        out = StringIO()
        call_command("sync_all", stdout=out)
        # None of the individual syncs should have been called
        mock_call.assert_not_called()
