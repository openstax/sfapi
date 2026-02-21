import time

from django.utils.deprecation import MiddlewareMixin


class AuditLogMiddleware(MiddlewareMixin):
    """Logs all /api/ requests to the RequestLog model after response."""

    def process_request(self, request):
        request._audit_start_time = time.monotonic()

    def process_response(self, request, response):
        if not hasattr(request, "_audit_start_time"):
            return response

        # Only log API requests
        if not request.path.startswith("/api/"):
            return response

        duration_ms = int((time.monotonic() - request._audit_start_time) * 1000)

        try:
            from api.models import RequestLog

            RequestLog.objects.create(
                method=request.method,
                path=request.path,
                query_params=dict(request.GET),
                auth_type=getattr(request, "auth_type", ""),
                auth_identifier=self._get_auth_identifier(request),
                status_code=response.status_code,
                duration_ms=duration_ms,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:512],
            )
        except Exception:  # noqa: S110
            pass  # Never let audit logging break the response

        return response

    def _get_auth_identifier(self, request):
        auth_type = getattr(request, "auth_type", "")
        if auth_type == "sso":
            return getattr(request, "auth_uuid", "")
        if auth_type == "api_key":
            return getattr(request, "auth_key_name", "")
        return ""

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
