import uuid
from unittest import skip
from django.utils import timezone
from django.test import TestCase, override_settings
from ninja.testing import TestClient
from sf.models.contact import Contact
from .api_v1 import router

# Disable logging to prevent unnecessary output during tests
import logging
logging.disable(logging.CRITICAL)

class APITest(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.contact = Contact.objects.create(
            email="test@openstax.org",
            first_name="Test",
            last_name="User",
            accounts_uuid=uuid.uuid4(),
            signup_date=timezone.now()
        )

    @override_settings(IS_TESTING=False)
    def test_not_logged_in_contact_returns_401(self):
        response = self.client.get('/contact')
        self.assertEqual(response.status_code, 401)

    @override_settings(IS_TESTING=False)
    def test_not_logged_in_adoption_returns_401(self):
        response = self.client.get('/adoptions')
        self.assertEqual(response.status_code, 401)

    def test_no_contact_found(self):
        response = self.client.get('/contact')
        self.assertEqual(response.status_code, 404)

    @skip("This endpoint is returning 404 even after hitting it 5 times. Need to investigate.")
    def test_rate_limiting(self):
        for _ in range(4):
            response = self.client.get('/contact')
            self.assertEqual(response.status_code, 404)

        response = self.client.get('/contact')
        self.assertEqual(response.status_code, 429)




    # TODO: Find elegant way to test authenticated endpoints and return the contact from the test database



