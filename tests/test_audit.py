from django.test import TestCase

from api.models import FieldChangeLog, RequestLog
from db.models import Account


class RequestLogTest(TestCase):
    def test_create_request_log(self):
        log = RequestLog.objects.create(
            method='GET',
            path='/api/v1/contact',
            query_params={},
            auth_type='sso',
            auth_identifier='test-uuid',
            status_code=200,
            duration_ms=42,
            ip_address='127.0.0.1',
            user_agent='TestAgent/1.0',
        )
        self.assertEqual(RequestLog.objects.count(), 1)
        self.assertEqual(log.method, 'GET')
        self.assertEqual(log.status_code, 200)

    def test_request_log_ordering(self):
        RequestLog.objects.create(method='GET', path='/a', status_code=200, duration_ms=10)
        RequestLog.objects.create(method='GET', path='/b', status_code=200, duration_ms=20)
        logs = RequestLog.objects.all()
        # Most recent first
        self.assertEqual(logs[0].path, '/b')


class FieldChangeLogTest(TestCase):
    def test_create_field_change_log(self):
        log = FieldChangeLog.objects.create(
            model_name='Account',
            record_id='001000000000001',
            field_name='name',
            old_value='Old Name',
            new_value='New Name',
            change_source='api',
            changed_by='test-uuid',
        )
        self.assertEqual(FieldChangeLog.objects.count(), 1)
        self.assertEqual(log.old_value, 'Old Name')
        self.assertEqual(log.new_value, 'New Name')


class ChangeTrackingTest(TestCase):
    """Test that the ChangeTrackingMixin logs field changes on save()."""

    def test_account_update_creates_change_log(self):
        account = Account.objects.create(
            id='001000000000001',
            name='Old University',
        )
        account.name = 'New University'
        account._change_source = 'api'
        account._changed_by = 'test-user'
        account.save()

        logs = FieldChangeLog.objects.filter(model_name='Account', record_id='001000000000001')
        self.assertTrue(logs.exists())
        name_log = logs.filter(field_name='name').first()
        self.assertIsNotNone(name_log)
        self.assertEqual(name_log.old_value, 'Old University')
        self.assertEqual(name_log.new_value, 'New University')
        self.assertEqual(name_log.change_source, 'api')

    def test_no_change_no_log(self):
        account = Account.objects.create(
            id='001000000000001',
            name='Same University',
        )
        account.save()  # No actual change

        logs = FieldChangeLog.objects.filter(model_name='Account', record_id='001000000000001')
        self.assertFalse(logs.exists())
