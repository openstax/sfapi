import logging
import uuid

from django.test import TestCase
from django.utils import timezone

from db.functions import update_or_create_accounts
from db.models import Account as DBAccount
from sf.models.account import Account
from sf.models.contact import Contact

logging.disable(logging.CRITICAL)


class ContactTest(TestCase):
    databases = {'default'}

    def test_contact_create(self):
        faux_account_id = uuid.uuid4()
        contact = Contact.objects.create(
            email="test@openstax.org",
            first_name="Test",
            last_name="User",
            accounts_uuid=faux_account_id,
            signup_date=timezone.now()
        )
        self.assertEqual(contact.email, "test@openstax.org")
        self.assertEqual(contact.first_name, "Test")
        self.assertEqual(contact.last_name, "User")
        self.assertEqual(contact.accounts_uuid, faux_account_id)


class AccountTest(TestCase):
    databases = {'default', 'salesforce'}

    def test_account_create(self):
        account = Account.objects.create(
            name="Test Account",
            type="Customer - Direct",
            city="Houston",
            state="TX",
            country="USA"
        )
        self.assertEqual(account.name, "Test Account")
        self.assertEqual(account.type, "Customer - Direct")
        self.assertEqual(account.city, "Houston")
        self.assertEqual(account.state, "TX")
        self.assertEqual(account.country, "USA")


class BulkSyncTest(TestCase):
    """Test bulk sync functions."""

    def _make_mock_account(self, id, name='Test School', **kwargs):
        """Create a mock SF account object."""
        class MockAccount:
            pass
        acct = MockAccount()
        acct.id = id
        acct.name = name
        acct.type = kwargs.get('type', 'College/University (4)')
        acct.country = kwargs.get('country', 'US')
        acct.state = kwargs.get('state', 'TX')
        acct.city = kwargs.get('city', 'Houston')
        acct.country_code = 'US'
        acct.state_code = 'TX'
        acct.created_date = timezone.now()
        acct.last_modified_date = timezone.now()
        acct.last_activity_date = None
        acct.lms = None
        acct.books_adopted = None
        acct.sheer_id_school_name = None
        acct.ipeds_id = None
        acct.nces_id = None
        return acct

    def test_bulk_create_accounts(self):
        accounts = [
            self._make_mock_account(f'001{i:015d}', f'School {i}')
            for i in range(10)
        ]
        count = update_or_create_accounts(accounts)
        self.assertEqual(count, 10)
        self.assertEqual(DBAccount.objects.count(), 10)

    def test_bulk_update_accounts(self):
        # First create them
        accounts = [
            self._make_mock_account(f'001{i:015d}', f'School {i}')
            for i in range(5)
        ]
        update_or_create_accounts(accounts)

        # Now update them (upsert returns total count, not just created)
        for acct in accounts:
            acct.name = f'Updated {acct.name}'
        count = update_or_create_accounts(accounts)
        self.assertEqual(count, 5)
        self.assertEqual(DBAccount.objects.get(id='001000000000000000').name, 'Updated School 0')

    def test_bulk_mixed_create_update(self):
        # Create 3 accounts
        accounts = [
            self._make_mock_account(f'001{i:015d}', f'School {i}')
            for i in range(3)
        ]
        update_or_create_accounts(accounts)

        # Add 2 new + update 3 existing (upsert returns total count)
        accounts.extend([
            self._make_mock_account(f'001{i:015d}', f'School {i}')
            for i in range(3, 5)
        ])
        count = update_or_create_accounts(accounts)
        self.assertEqual(count, 5)
        self.assertEqual(DBAccount.objects.count(), 5)
