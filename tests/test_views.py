from unittest.mock import MagicMock, patch

from django.test import TestCase

from api.models import SuperUser


class InfoEndpointTest(TestCase):
    def setUp(self):
        self.super_uuid = "f8a6b8b8-32f7-4b4d-b6f9-054ab6fb5623"
        SuperUser.objects.create(accounts_uuid=self.super_uuid, name="Test Super User")

    @patch("api.auth.get_logged_in_user_uuid", return_value=None)
    def test_unauthorized_no_auth(self, mock_uuid):
        response = self.client.get("/api/v1/info")
        self.assertEqual(response.status_code, 401)

    @patch("api.api_v1.get_logged_in_user_uuid", return_value="not-a-super-user")
    @patch("api.auth.get_logged_in_user_uuid", return_value="not-a-super-user")
    def test_unauthorized_not_super_user(self, mock_auth_uuid, mock_api_uuid):
        response = self.client.get("/api/v1/info")
        self.assertEqual(response.status_code, 401)

    @patch("api.api_v1.connections")
    @patch("api.api_v1.get_logged_in_user_uuid")
    @patch("api.auth.get_logged_in_user_uuid")
    def test_authorized_super_user(self, mock_auth_uuid, mock_api_uuid, mock_connections):
        mock_auth_uuid.return_value = self.super_uuid
        mock_api_uuid.return_value = self.super_uuid
        mock_conn = mock_connections.__getitem__.return_value
        mock_conn.connection.api_usage.api_usage = 1000
        mock_conn.connection.api_usage.api_limit = 15000
        response = self.client.get("/api/v1/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("release_information", data)
        self.assertIn("api_usage", data)
        self.assertEqual(data["api_usage"]["api_usage"], 1000)

    @patch("api.api_v1.connections")
    @patch("api.api_v1.get_logged_in_user_uuid")
    @patch("api.auth.get_logged_in_user_uuid")
    def test_sf_api_usage_not_available(self, mock_auth_uuid, mock_api_uuid, mock_connections):
        mock_auth_uuid.return_value = self.super_uuid
        mock_api_uuid.return_value = self.super_uuid
        mock_connections.__getitem__.return_value.connection = MagicMock(spec=[])
        response = self.client.get("/api/v1/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("error", data["api_usage"])
