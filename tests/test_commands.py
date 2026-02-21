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


class SyncAccountsCommandTest(TestCase):
    @patch("sf.management.commands.sync_accounts.SFAccount")
    @patch("sf.management.commands.sync_accounts.update_or_create_accounts")
    def test_full_sync_force(self, mock_sync, mock_sf):
        mock_sf.objects.all.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_accounts", "--force", stdout=out)
        mock_sync.assert_called_once_with([], full_sync=True)
        self.assertIn("synced successfully", out.getvalue())

    @patch("sf.management.commands.sync_accounts.SFAccount")
    @patch("sf.management.commands.sync_accounts.update_or_create_accounts")
    def test_forcedelete(self, mock_sync, mock_sf):
        # Create some accounts to be deleted
        Account.all_objects.create(id="001000000000001", name="Test", last_modified_date=timezone.now())
        mock_sf.objects.all.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_accounts", "--forcedelete", stdout=out)
        self.assertIn("Deleted all local accounts", out.getvalue())

    @patch("sf.management.commands.sync_accounts.SFAccount")
    @patch("sf.management.commands.sync_accounts.update_or_create_accounts")
    def test_incremental_sync(self, mock_sync, mock_sf):
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
    @patch("sf.management.commands.sync_contacts.SFContact")
    @patch("sf.management.commands.sync_contacts.update_or_create_contacts")
    def test_full_sync_force(self, mock_sync, mock_sf):
        mock_sf.objects.filter.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_contacts", "--force", stdout=out)
        mock_sync.assert_called_once()
        self.assertIn("synced successfully", out.getvalue())

    @patch("sf.management.commands.sync_contacts.SFContact")
    @patch("sf.management.commands.sync_contacts.update_or_create_contacts")
    def test_forcedelete(self, mock_sync, mock_sf):
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

    @patch("sf.management.commands.sync_contacts.SFContact")
    @patch("sf.management.commands.sync_contacts.update_or_create_contacts")
    def test_incremental_sync(self, mock_sync, mock_sf):
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
    @patch("sf.management.commands.sync_opportunities.SFOpportunity")
    @patch("sf.management.commands.sync_opportunities.update_or_create_opportunities")
    def test_full_sync_force(self, mock_sync, mock_sf):
        mock_sf.objects.all.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_opportunities", "--force", stdout=out)
        mock_sync.assert_called_once()
        self.assertIn("synced successfully", out.getvalue())

    @patch("sf.management.commands.sync_opportunities.SFOpportunity")
    @patch("sf.management.commands.sync_opportunities.update_or_create_opportunities")
    def test_forcedelete(self, mock_sync, mock_sf):
        mock_sf.objects.all.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_opportunities", "--forcedelete", stdout=out)
        self.assertIn("synced successfully", out.getvalue())


class SyncAdoptionsCommandTest(TestCase):
    @patch("sf.management.commands.sync_adoptions.SFAdoption")
    @patch("sf.management.commands.sync_adoptions.update_or_create_adoptions")
    def test_full_sync_force(self, mock_sync, mock_sf):
        mock_sf.objects.all.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_adoptions", "--force", stdout=out)
        mock_sync.assert_called_once()
        self.assertIn("synced successfully", out.getvalue())


class SyncBooksCommandTest(TestCase):
    @patch("sf.management.commands.sync_books.SFBook")
    @patch("sf.management.commands.sync_books.update_or_create_books")
    def test_sync(self, mock_sync, mock_sf):
        mock_sf.objects.all.return_value = []
        mock_sync.return_value = 0
        out = StringIO()
        call_command("sync_books", stdout=out)
        mock_sync.assert_called_once_with(mock_sf.objects.all.return_value, full_sync=True)
        self.assertIn("synced successfully", out.getvalue())
