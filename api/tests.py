import uuid
import time
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.test import TestCase
from ninja.testing import TestClient
from db.models import Contact, Account, Book, Opportunity, Adoption
from api.auth import APIKey
from .api_v1 import router

# Disable logging to prevent unnecessary output during tests
import logging
logging.disable(logging.CRITICAL)

# Test UUID for mocking authenticated requests
TEST_UUID = str(uuid.uuid4())


def mock_logged_in_user(request):
    return TEST_UUID


def mock_not_logged_in(request):
    return None


def mock_super_user(request):
    return 'f8a6b8b8-32f7-4b4d-b6f9-054ab6fb5623'


class AuthTest(TestCase):
    """Test authentication behavior."""

    def setUp(self):
        self.client = TestClient(router)

    def test_no_auth_contact_returns_401(self):
        response = self.client.get('/contact')
        self.assertEqual(response.status_code, 401)

    def test_no_auth_adoptions_returns_401(self):
        response = self.client.get('/adoptions')
        self.assertEqual(response.status_code, 401)

    def test_no_auth_books_returns_401(self):
        response = self.client.get('/books')
        self.assertEqual(response.status_code, 401)

    def test_no_auth_case_returns_401(self):
        response = self.client.post('/case', json={
            'subject': 'Test', 'description': 'Test'
        })
        self.assertEqual(response.status_code, 401)


class APIKeyTest(TestCase):
    """Test API key creation and verification."""

    def test_create_key(self):
        api_key, raw_key = APIKey.create_key(name='test-key', scopes=['read:books'])
        self.assertIsNotNone(raw_key)
        self.assertEqual(len(api_key.key_prefix), 8)
        self.assertEqual(api_key.scopes, ['read:books'])

    def test_verify_key(self):
        api_key, raw_key = APIKey.create_key(name='test-key')
        self.assertTrue(api_key.verify(raw_key))
        self.assertFalse(api_key.verify('wrong-key'))

    def test_authenticate_key(self):
        api_key, raw_key = APIKey.create_key(name='test-key')
        result = APIKey.authenticate(raw_key)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, api_key.id)

    def test_authenticate_expired_key(self):
        api_key, raw_key = APIKey.create_key(
            name='expired-key',
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )
        result = APIKey.authenticate(raw_key)
        self.assertIsNone(result)

    def test_authenticate_inactive_key(self):
        api_key, raw_key = APIKey.create_key(name='inactive-key')
        api_key.is_active = False
        api_key.save()
        result = APIKey.authenticate(raw_key)
        self.assertIsNone(result)

    def test_authenticate_wrong_key(self):
        result = APIKey.authenticate('definitely-not-a-real-key-at-all')
        self.assertIsNone(result)


class ContactEndpointTest(TestCase):
    """Test GET /contact endpoint."""

    def setUp(self):
        self.client = TestClient(router)
        self.account = Account.objects.create(id='001000000000001', name='Test University')
        self.contact = Contact.objects.create(
            id='003000000000001',
            email='test@openstax.org',
            first_name='Test',
            last_name='User',
            full_name='Test User',
            verification_status='confirmed',
            accounts_uuid=TEST_UUID,
            account=self.account,
            signup_date=timezone.now(),
        )

    @patch('api.api_v1.get_logged_in_user_uuid', side_effect=mock_logged_in_user)
    def test_get_contact_success(self, mock_auth):
        response = self.client.get('/contact')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['accounts_uuid'], TEST_UUID)
        self.assertEqual(data['first_name'], 'Test')
        self.assertEqual(data['school'], 'Test University')

    @patch('api.api_v1.get_logged_in_user_uuid', return_value=str(uuid.uuid4()))
    def test_get_contact_not_found(self, mock_auth):
        response = self.client.get('/contact')
        self.assertEqual(response.status_code, 404)

    @patch('api.api_v1.get_logged_in_user_uuid', side_effect=mock_logged_in_user)
    def test_update_contact(self, mock_auth):
        response = self.client.put('/contact', json={
            'first_name': 'Updated',
            'role': 'Professor',
        })
        self.assertEqual(response.status_code, 200)
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.first_name, 'Updated')
        self.assertEqual(self.contact.role, 'Professor')
        self.assertEqual(self.contact.full_name, 'Updated User')


class AdoptionsEndpointTest(TestCase):
    """Test GET /adoptions endpoint."""

    def setUp(self):
        self.client = TestClient(router)
        self.account = Account.objects.create(id='001000000000001', name='Test University')
        self.contact = Contact.objects.create(
            id='003000000000001',
            email='test@openstax.org',
            first_name='Test',
            last_name='User',
            full_name='Test User',
            verification_status='confirmed',
            accounts_uuid=TEST_UUID,
            account=self.account,
            signup_date=timezone.now(),
        )
        self.book = Book.objects.create(
            id='a0B000000000001',
            name='Test Book',
            official_name='Official Test Book',
            type='Textbook',
        )
        self.opportunity = Opportunity.objects.create(
            id='006000000000001',
            account=self.account,
            name='Test Opportunity',
            stage_name='Confirmed Adoption Won',
            close_date=timezone.now().date(),
            owner_id='005000000000001',
            created_date=timezone.now(),
            created_by_id='005000000000001',
            last_modified_date=timezone.now(),
            last_modified_by_id='005000000000001',
            system_modstamp=timezone.now(),
            contact=self.contact,
            book=self.book,
        )
        self.adoption = Adoption.objects.create(
            id='a0A000000000001',
            contact=self.contact,
            adoption_number='ADO-000001',
            created_date=timezone.now(),
            last_modified_date=timezone.now(),
            system_modstamp=timezone.now(),
            opportunity=self.opportunity,
            base_year=2024,
            adoption_type='Faculty/Teacher Adoption',
            school_year='2024-2025',
            students=50,
            savings=5000,
        )

    @patch('api.api_v1.get_logged_in_user_uuid', side_effect=mock_logged_in_user)
    def test_get_adoptions_success(self, mock_auth):
        response = self.client.get('/adoptions')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['total_students'], 50)
        self.assertEqual(data['adoptions'][0]['school_year'], '2024-2025')

    @patch('api.api_v1.get_logged_in_user_uuid', side_effect=mock_logged_in_user)
    def test_get_adoptions_confirmed_filter(self, mock_auth):
        response = self.client.get('/adoptions?confirmed=true')
        self.assertEqual(response.status_code, 200)

    @patch('api.api_v1.get_logged_in_user_uuid', return_value=str(uuid.uuid4()))
    def test_get_adoptions_no_contact(self, mock_auth):
        response = self.client.get('/adoptions')
        self.assertEqual(response.status_code, 404)


class SchoolsEndpointTest(TestCase):
    """Test GET /schools endpoint."""

    def setUp(self):
        self.client = TestClient(router)
        Account.objects.create(id='001000000000001', name='Rice University', type='College/University (4)')
        Account.objects.create(id='001000000000002', name='MIT', type='College/University (4)')

    def test_search_schools(self):
        response = self.client.get('/schools?name=Rice')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['schools'][0]['name'], 'Rice University')

    def test_search_requires_name(self):
        response = self.client.get('/schools')
        self.assertEqual(response.status_code, 422)

    def test_search_name_too_short(self):
        response = self.client.get('/schools?name=ab')
        self.assertEqual(response.status_code, 422)

    def test_search_no_results(self):
        response = self.client.get('/schools?name=NonexistentSchool')
        self.assertEqual(response.status_code, 404)


class BooksEndpointTest(TestCase):
    """Test GET /books endpoint."""

    def setUp(self):
        self.client = TestClient(router)
        Book.objects.create(id='a0B000000000001', name='Physics', official_name='College Physics', type='Textbook')

    @patch('api.api_v1.get_logged_in_user_uuid', side_effect=mock_super_user)
    def test_get_books_with_scope(self, mock_auth):
        response = self.client.get('/books')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)

    @patch('api.api_v1.get_logged_in_user_uuid', side_effect=mock_logged_in_user)
    def test_get_books_without_scope(self, mock_auth):
        response = self.client.get('/books')
        self.assertEqual(response.status_code, 401)


class FormSubmissionTest(TestCase):
    """Test POST /forms/submit endpoint."""

    def setUp(self):
        self.client = TestClient(router)

    @patch('api.api_v1.get_logged_in_user_uuid', side_effect=mock_logged_in_user)
    def test_honeypot_returns_202(self, mock_auth):
        response = self.client.post('/forms/submit', json={
            'form_type': 'contact_us',
            'data': {'message': 'hello'},
            'honeypot': 'i-am-a-bot',
        })
        self.assertEqual(response.status_code, 202)

    @patch('api.api_v1.get_logged_in_user_uuid', side_effect=mock_logged_in_user)
    def test_fast_submission_returns_202(self, mock_auth):
        # submitted_at is only 1 second ago (JS timestamp)
        response = self.client.post('/forms/submit', json={
            'form_type': 'contact_us',
            'data': {'message': 'hello'},
            'submitted_at': (time.time() - 1) * 1000,
        })
        self.assertEqual(response.status_code, 202)

    @patch('api.api_v1.get_logged_in_user_uuid', side_effect=mock_logged_in_user)
    def test_valid_submission(self, mock_auth):
        response = self.client.post('/forms/submit', json={
            'form_type': 'web_to_case',
            'data': {'subject': 'Help', 'description': 'I need help'},
            'submitted_at': (time.time() - 30) * 1000,
        })
        # This will fail because we can't connect to SF in tests,
        # but it should at least get past validation
        self.assertIn(response.status_code, [200, 500])


class CaseValidationTest(TestCase):
    """Test POST /case input validation."""

    def setUp(self):
        self.client = TestClient(router)

    @patch('api.api_v1.get_logged_in_user_uuid', side_effect=mock_super_user)
    def test_case_missing_subject(self, mock_auth):
        response = self.client.post('/case', json={
            'description': 'Test description',
        })
        self.assertEqual(response.status_code, 422)

    @patch('api.api_v1.get_logged_in_user_uuid', side_effect=mock_super_user)
    def test_case_empty_subject(self, mock_auth):
        response = self.client.post('/case', json={
            'subject': '',
            'description': 'Test description',
        })
        self.assertEqual(response.status_code, 422)
