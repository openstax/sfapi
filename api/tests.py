import uuid
from django.utils import timezone
from django.test import TestCase, Client
from sf.models.contact import Contact


class APITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.contact = Contact.objects.create(
            email="test@openstax.org",
            first_name="Test",
            last_name="User",
            accounts_uuid=uuid.uuid4(),
            signup_date=timezone.now()
        )

    def test_contact_get(self):
        response = self.client.get('/api/v1/contact/')
        self.assertEqual(response.status_code, 404)

    def test_adoption_get(self):
        response = self.client.get('/api/v1/adoption/')
        self.assertEqual(response.status_code, 404)

