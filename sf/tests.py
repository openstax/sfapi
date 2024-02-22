import uuid
from django.utils import timezone
from django.test import TestCase
from sf.models.contact import Contact
from sf.models.account import Account


class ContactTest(TestCase):
    databases = {'default', 'salesforce'}

    def test_contact_create(self):
        # Then override the LOGIN_URL setting
        #with self.settings(SALESFORCE_DB_ALIAS="salesforce"):
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
            billing_city="Houston",
            billing_state="TX",
            billing_country="USA"
        )
        self.assertEqual(account.name, "Test Account")
        self.assertEqual(account.type, "Customer - Direct")
        self.assertEqual(account.billing_city, "Houston")
        self.assertEqual(account.billing_state, "TX")
        self.assertEqual(account.billing_country, "USA")


