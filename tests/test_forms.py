from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import TestCase

from api.forms.pipeline import FormPipeline
from api.forms.processors import PROCESSORS, process_submission
from api.models import FormSubmission


class FormPipelineTest(TestCase):
    def _payload(self, **kwargs):
        defaults = {
            "form_type": "contact_us",
            "data": {"message": "hello"},
            "honeypot": "",
            "submitted_at": None,
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_valid_submission(self):
        is_valid, errors = FormPipeline().validate(self._payload())
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_honeypot_detected(self):
        is_valid, errors = FormPipeline().validate(self._payload(honeypot="bot"))
        self.assertFalse(is_valid)
        self.assertEqual(errors, ["spam"])

    def test_fast_submission_detected(self):
        import time

        # submitted_at is 0.5 seconds ago (in JS millis)
        payload = self._payload(submitted_at=(time.time() - 0.5) * 1000)
        is_valid, errors = FormPipeline().validate(payload)
        self.assertFalse(is_valid)
        self.assertEqual(errors, ["spam"])

    def test_disposable_email_detected(self):
        payload = self._payload(data={"email": "bot@mailinator.com"})
        is_valid, errors = FormPipeline().validate(payload)
        self.assertFalse(is_valid)
        self.assertEqual(errors, ["spam"])

    def test_missing_form_type(self):
        is_valid, errors = FormPipeline().validate(self._payload(form_type=""))
        self.assertFalse(is_valid)
        self.assertIn("form_type is required", errors)

    def test_missing_data(self):
        is_valid, errors = FormPipeline().validate(self._payload(data={}))
        self.assertFalse(is_valid)
        self.assertIn("data is required", errors)


class FormProcessorTest(TestCase):
    def test_processors_registered(self):
        self.assertIn("web_to_case", PROCESSORS)
        self.assertIn("contact_us", PROCESSORS)

    def test_unknown_form_type(self):
        submission = FormSubmission.objects.create(
            form_type="unknown_type",
            data={"foo": "bar"},
            status="pending",
            auth_type="sso",
            auth_identifier="test",
        )
        process_submission(submission)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "failed")
        self.assertIn("Unknown form type", submission.error_message)

    @patch("api.forms.processors.Case")
    def test_web_to_case_success(self, mock_case):
        mock_case.objects.create.return_value = MagicMock(pk="500000000000001")
        submission = FormSubmission.objects.create(
            form_type="web_to_case",
            data={"subject": "Help", "description": "Need help"},
            status="pending",
            auth_type="sso",
            auth_identifier="test",
        )
        process_submission(submission)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "completed")
        self.assertEqual(submission.sf_record_id, "500000000000001")

    @patch("api.forms.processors.Case")
    def test_contact_us_success(self, mock_case):
        mock_case.objects.create.return_value = MagicMock(pk="500000000000002")
        submission = FormSubmission.objects.create(
            form_type="contact_us",
            data={"subject": "Question", "message": "Hi"},
            status="pending",
            auth_type="sso",
            auth_identifier="test",
        )
        process_submission(submission)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "completed")

    @patch("api.forms.processors.Case")
    def test_processor_exception(self, mock_case):
        mock_case.objects.create.side_effect = Exception("SF connection failed")
        submission = FormSubmission.objects.create(
            form_type="web_to_case",
            data={"subject": "Help"},
            status="pending",
            auth_type="sso",
            auth_identifier="test",
        )
        process_submission(submission)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "failed")
        self.assertIn("SF connection failed", submission.error_message)
