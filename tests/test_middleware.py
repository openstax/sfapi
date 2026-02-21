from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from api.middleware import AuditLogMiddleware
from api.models import RequestLog


class AuditLogMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = AuditLogMiddleware(get_response=lambda r: HttpResponse())

    def test_logs_api_request(self):
        request = self.factory.get("/api/v1/schools?name=rice")
        self.middleware.process_request(request)
        response = HttpResponse(status=200)
        self.middleware.process_response(request, response)
        self.assertEqual(RequestLog.objects.count(), 1)
        log = RequestLog.objects.first()
        self.assertEqual(log.method, "GET")
        self.assertEqual(log.path, "/api/v1/schools")
        self.assertEqual(log.status_code, 200)

    def test_skips_non_api_request(self):
        request = self.factory.get("/admin/")
        self.middleware.process_request(request)
        response = HttpResponse(status=200)
        self.middleware.process_response(request, response)
        self.assertEqual(RequestLog.objects.count(), 0)

    def test_skips_without_start_time(self):
        request = self.factory.get("/api/v1/contact")
        # Don't call process_request — no _audit_start_time
        response = HttpResponse(status=200)
        result = self.middleware.process_response(request, response)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(RequestLog.objects.count(), 0)

    def test_sso_auth_identifier(self):
        request = self.factory.get("/api/v1/contact")
        request.auth_type = "sso"
        request.auth_uuid = "test-uuid-123"
        self.middleware.process_request(request)
        self.middleware.process_response(request, HttpResponse(status=200))
        log = RequestLog.objects.first()
        self.assertEqual(log.auth_type, "sso")
        self.assertEqual(log.auth_identifier, "test-uuid-123")

    def test_api_key_auth_identifier(self):
        request = self.factory.get("/api/v1/books")
        request.auth_type = "api_key"
        request.auth_key_name = "test-service"
        self.middleware.process_request(request)
        self.middleware.process_response(request, HttpResponse(status=200))
        log = RequestLog.objects.first()
        self.assertEqual(log.auth_identifier, "test-service")

    def test_x_forwarded_for_ip(self):
        request = self.factory.get("/api/v1/schools", HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8")
        self.middleware.process_request(request)
        self.middleware.process_response(request, HttpResponse(status=200))
        log = RequestLog.objects.first()
        self.assertEqual(log.ip_address, "1.2.3.4")

    def test_remote_addr_fallback(self):
        request = self.factory.get("/api/v1/schools")
        self.middleware.process_request(request)
        self.middleware.process_response(request, HttpResponse(status=200))
        log = RequestLog.objects.first()
        self.assertEqual(log.ip_address, "127.0.0.1")
