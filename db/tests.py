from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from db.functions import (
    update_or_create_accounts,
    update_or_create_adoptions,
    update_or_create_books,
    update_or_create_contacts,
    update_or_create_opportunities,
)
from db.models import Account, Adoption, Book, Contact, Opportunity


def _make_account(id="001000000000001", name="Test U", **kwargs):
    Account.all_objects.create(
        id=id,
        name=name,
        type=kwargs.get("type", "College/University (4)"),
        last_modified_date=timezone.now(),
        is_deleted=kwargs.get("is_deleted", False),
    )
    return Account.all_objects.get(id=id)


def _make_contact(id="003000000000001", account=None, **kwargs):
    return Contact.all_objects.create(
        id=id,
        first_name=kwargs.get("first_name", "Test"),
        last_name=kwargs.get("last_name", "User"),
        full_name=kwargs.get("full_name", "Test User"),
        email=kwargs.get("email", "test@example.com"),
        verification_status="confirmed",
        accounts_uuid=kwargs.get("accounts_uuid", "uuid-1"),
        account=account,
        signup_date=timezone.now(),
        last_modified_date=timezone.now(),
    )


def _make_book(id="a0B000000000001", **kwargs):
    return Book.all_objects.create(
        id=id,
        name=kwargs.get("name", "Physics"),
        official_name=kwargs.get("official_name", "College Physics"),
        type="Textbook",
    )


def _make_opportunity(id="006000000000001", account=None, contact=None, book=None):
    return Opportunity.objects.create(
        id=id,
        account=account,
        name="Test Opp",
        stage_name="Confirmed Adoption Won",
        close_date=timezone.now().date(),
        owner_id="005000000000001",
        created_date=timezone.now(),
        created_by_id="005000000000001",
        last_modified_date=timezone.now(),
        last_modified_by_id="005000000000001",
        system_modstamp=timezone.now(),
        contact=contact,
        book=book,
    )


# -- Mock SF objects for sync functions --


def _mock_sf_contact(id, account_id=None):
    now = timezone.now()
    account = SimpleNamespace(id=account_id) if account_id else None
    return SimpleNamespace(
        id=id,
        account=account,
        first_name="Test",
        last_name="User",
        full_name="Test User",
        email="test@example.com",
        role=None,
        position=None,
        title=None,
        adoption_status=None,
        verification_status="confirmed",
        accounts_uuid="test-uuid",
        accounts_id=None,
        signup_date=now,
        lead_source=None,
        lms=None,
        last_modified_date=now,
        subject_interest=None,
    )


def _mock_sf_opportunity(id, account_id=None, contact_id=None, book_id=None):
    now = timezone.now()
    return SimpleNamespace(
        id=id,
        account=SimpleNamespace(id=account_id) if account_id else None,
        contact=SimpleNamespace(id=contact_id) if contact_id else None,
        book=SimpleNamespace(id=book_id) if book_id else None,
        record_type_id=None,
        name="Test Opp",
        description=None,
        stage_name="Confirmed Adoption Won",
        amount=None,
        probability=None,
        close_date=now.date(),
        type="New Business",
        lead_source=None,
        is_closed=False,
        is_won=False,
        owner_id="005000000000001",
        created_date=now,
        created_by_id="005000000000001",
        last_modified_date=now,
        last_modified_by_id="005000000000001",
        system_modstamp=now,
        last_activity_date=None,
        last_activity_in_days=None,
        last_stage_change_date=None,
        last_stage_change_in_days=None,
        fiscal_year=None,
        fiscal=None,
        last_viewed_date=None,
        last_referenced_date=None,
    )


def _mock_sf_adoption(id, contact_id=None, opportunity_id=None):
    now = timezone.now()
    return SimpleNamespace(
        id=id,
        contact=SimpleNamespace(id=contact_id) if contact_id else None,
        opportunity=SimpleNamespace(id=opportunity_id) if opportunity_id else None,
        adoption_number="ADO-000001",
        created_date=now,
        last_modified_date=now,
        system_modstamp=now,
        last_activity_date=None,
        class_start_date=None,
        confirmation_date=None,
        name="Test Adoption",
        base_year=2024,
        adoption_type="Faculty/Teacher Adoption",
        students=50,
        school_year="2024-2025",
        terms_used="Both",
        confirmation_type="OpenStax Confirmed Adoption",
        how_using=None,
        savings=5000,
    )


def _mock_sf_book(id, name="Test Book"):
    return SimpleNamespace(
        id=id,
        name=name,
        official_name=f"Official {name}",
        type="Textbook",
        subject_areas="Science",
        website_url="https://openstax.org",
    )


class ActiveManagerTest(TestCase):
    def test_excludes_deleted_accounts(self):
        _make_account("001000000000001", is_deleted=False)
        _make_account("001000000000002", name="Deleted", is_deleted=True)
        self.assertEqual(Account.objects.count(), 1)
        self.assertEqual(Account.all_objects.count(), 2)

    def test_excludes_deleted_books(self):
        _make_book("a0B000000000001")
        Book.all_objects.create(id="a0B000000000002", name="Del", official_name="Del", type="T", is_deleted=True)
        self.assertEqual(Book.objects.count(), 1)
        self.assertEqual(Book.all_objects.count(), 2)

    def test_model_str(self):
        acct = _make_account("001000000000001", name="Rice")
        self.assertEqual(str(acct), "Rice")
        book = _make_book("a0B000000000001", official_name="Physics")
        self.assertEqual(str(book), "Physics")
        contact = _make_contact("003000000000001", account=acct, full_name="John Doe")
        self.assertEqual(str(contact), "John Doe")
        opp = _make_opportunity("006000000000001", account=acct, contact=contact, book=book)
        self.assertEqual(str(opp), "Test Opp")
        adoption = Adoption.objects.create(
            id="a0A000000000001",
            contact=contact,
            adoption_number="ADO-1",
            created_date=timezone.now(),
            last_modified_date=timezone.now(),
            system_modstamp=timezone.now(),
            opportunity=opp,
            base_year=2024,
            adoption_type="Faculty/Teacher Adoption",
            school_year="2024-2025",
            name="Test Adoption",
        )
        self.assertEqual(str(adoption), "Test Adoption")


class ContactSyncTest(TestCase):
    @patch("db.functions.capture_exception")
    def test_upsert_contacts(self, mock_sentry):
        _make_account("001000000000001")
        contacts = [
            _mock_sf_contact("003000000000001", account_id="001000000000001"),
            _mock_sf_contact("003000000000002", account_id="001000000000001"),
        ]
        count = update_or_create_contacts(contacts)
        self.assertEqual(count, 2)
        self.assertEqual(Contact.objects.count(), 2)

    @patch("db.functions.capture_exception")
    def test_skip_invalid_account_fk(self, mock_sentry):
        count = update_or_create_contacts([_mock_sf_contact("003000000000001", "001NONEXISTENT")])
        self.assertEqual(count, 0)
        mock_sentry.assert_called_once()

    @patch("db.functions.capture_exception")
    def test_null_account_allowed(self, mock_sentry):
        count = update_or_create_contacts([_mock_sf_contact("003000000000001")])
        self.assertEqual(count, 1)

    @patch("db.functions.capture_exception")
    def test_full_sync_soft_deletes(self, mock_sentry):
        _make_account("001000000000001")
        contacts = [
            _mock_sf_contact("003000000000001", "001000000000001"),
            _mock_sf_contact("003000000000002", "001000000000001"),
        ]
        update_or_create_contacts(contacts)
        update_or_create_contacts(contacts[:1], full_sync=True)
        self.assertTrue(Contact.all_objects.get(id="003000000000002").is_deleted)


class OpportunitySyncTest(TestCase):
    @patch("db.functions.capture_exception")
    def test_upsert_opportunities(self, mock_sentry):
        acct = _make_account("001000000000001")
        _make_contact("003000000000001", account=acct)
        _make_book("a0B000000000001")
        opps = [_mock_sf_opportunity("006000000000001", "001000000000001", "003000000000001", "a0B000000000001")]
        count = update_or_create_opportunities(opps)
        self.assertEqual(count, 1)

    @patch("db.functions.capture_exception")
    def test_skip_invalid_account_fk(self, mock_sentry):
        count = update_or_create_opportunities([_mock_sf_opportunity("006000000000001", account_id="001BAD")])
        self.assertEqual(count, 0)
        mock_sentry.assert_called()

    @patch("db.functions.capture_exception")
    def test_skip_invalid_contact_fk(self, mock_sentry):
        _make_account("001000000000001")
        count = update_or_create_opportunities([_mock_sf_opportunity("006000000000001", "001000000000001", "003BAD")])
        self.assertEqual(count, 0)

    @patch("db.functions.capture_exception")
    def test_skip_invalid_book_fk(self, mock_sentry):
        acct = _make_account("001000000000001")
        _make_contact("003000000000001", account=acct)
        count = update_or_create_opportunities(
            [_mock_sf_opportunity("006000000000001", "001000000000001", "003000000000001", "a0BBAD")]
        )
        self.assertEqual(count, 0)

    @patch("db.functions.capture_exception")
    def test_null_fks_allowed(self, mock_sentry):
        count = update_or_create_opportunities([_mock_sf_opportunity("006000000000001")])
        self.assertEqual(count, 1)


class AdoptionSyncTest(TestCase):
    @patch("db.functions.capture_exception")
    def test_upsert_adoptions(self, mock_sentry):
        acct = _make_account("001000000000001")
        contact = _make_contact("003000000000001", account=acct)
        _make_opportunity("006000000000001", account=acct, contact=contact)
        adoptions = [_mock_sf_adoption("a0A000000000001", "003000000000001", "006000000000001")]
        count = update_or_create_adoptions(adoptions)
        self.assertEqual(count, 1)

    @patch("db.functions.capture_exception")
    def test_skip_invalid_contact_fk(self, mock_sentry):
        count = update_or_create_adoptions([_mock_sf_adoption("a0A000000000001", contact_id="003BAD")])
        self.assertEqual(count, 0)
        mock_sentry.assert_called()

    @patch("db.functions.capture_exception")
    def test_skip_invalid_opportunity_fk(self, mock_sentry):
        acct = _make_account("001000000000001")
        _make_contact("003000000000001", account=acct)
        count = update_or_create_adoptions([_mock_sf_adoption("a0A000000000001", "003000000000001", "006BAD")])
        self.assertEqual(count, 0)


class BookSyncTest(TestCase):
    def test_upsert_books(self):
        count = update_or_create_books([_mock_sf_book("a0B000000000001"), _mock_sf_book("a0B000000000002")])
        self.assertEqual(count, 2)
        self.assertEqual(Book.objects.count(), 2)

    def test_full_sync_soft_deletes(self):
        books = [_mock_sf_book("a0B000000000001"), _mock_sf_book("a0B000000000002")]
        update_or_create_books(books)
        update_or_create_books(books[:1], full_sync=True)
        self.assertTrue(Book.all_objects.get(id="a0B000000000002").is_deleted)

    def test_account_full_sync_soft_deletes(self):
        from sf.tests import BulkSyncTest

        helper = BulkSyncTest()
        accounts = [helper._make_mock_account(f"001{i:015d}") for i in range(3)]
        update_or_create_accounts(accounts)
        update_or_create_accounts(accounts[:1], full_sync=True)
        self.assertFalse(Account.all_objects.get(id="001000000000000000").is_deleted)
        self.assertTrue(Account.all_objects.get(id="001000000000000001").is_deleted)
