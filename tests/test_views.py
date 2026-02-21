from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from sf.views import info, release_information, sf_api_usage


class ReleaseInformationTest(TestCase):
    def test_release_information(self):
        result = release_information()
        self.assertIn("sfapi_version", result)
        self.assertIn("environment", result)


class SfApiUsageTest(TestCase):
    @patch("sf.views.connections")
    def test_usage_not_available(self, mock_connections):
        # Simulate no connection (AttributeError)
        mock_connections.__getitem__.return_value.connection = MagicMock(spec=[])
        result = sf_api_usage()
        self.assertIn("error", result)

    @patch("sf.views.connections")
    def test_usage_available(self, mock_connections):
        mock_conn = mock_connections.__getitem__.return_value
        mock_conn.connection.api_usage.api_usage = 1000
        mock_conn.connection.api_usage.api_limit = 15000
        result = sf_api_usage()
        self.assertEqual(result["api_usage"], 1000)
        self.assertEqual(result["api_limit"], 15000)


class InfoViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("sf.views.has_super_auth", return_value=False)
    def test_unauthorized(self, mock_auth):
        request = self.factory.get("/info/")
        response = info(request)
        self.assertEqual(response.status_code, 401)

    @patch("sf.views.has_super_auth", return_value=True)
    def test_authorized(self, mock_auth):
        request = self.factory.get("/info/")
        response = info(request)
        self.assertEqual(response.status_code, 200)
