import hashlib
import secrets
from django.db import models
from django.utils import timezone
from ninja.security import APIKeyCookie, HttpBearer
from openstax_accounts.functions import get_logged_in_user_uuid


class APIKey(models.Model):
    name = models.CharField(max_length=100, help_text="Human-readable name for this key.")
    key_prefix = models.CharField(max_length=8, help_text="First 8 chars of the key for identification.")
    key_hash = models.CharField(max_length=64, help_text="SHA-256 hash of the full key.")
    scopes = models.JSONField(default=list, help_text="List of permission scopes, e.g. ['read:books', 'write:cases'].")
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=255, blank=True, help_text="Who created this key.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'

    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"

    @classmethod
    def create_key(cls, name, scopes=None, expires_at=None, created_by=''):
        """Create a new API key. Returns (api_key_instance, raw_key).
        The raw key is only available at creation time."""
        raw_key = secrets.token_urlsafe(48)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:8]

        api_key = cls.objects.create(
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=scopes or [],
            expires_at=expires_at,
            created_by=created_by,
        )
        return api_key, raw_key

    def verify(self, raw_key):
        """Verify a raw key against this key's hash."""
        return hashlib.sha256(raw_key.encode()).hexdigest() == self.key_hash

    @property
    def is_expired(self):
        if self.expires_at is None:
            return False
        return timezone.now() >= self.expires_at

    @classmethod
    def authenticate(cls, raw_key):
        """Look up and validate an API key. Returns the APIKey instance or None."""
        prefix = raw_key[:8]
        try:
            api_key = cls.objects.get(key_prefix=prefix, is_active=True)
        except (cls.DoesNotExist, cls.MultipleObjectsReturned):
            return None

        if not api_key.verify(raw_key):
            return None
        if api_key.is_expired:
            return None

        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=['last_used_at'])
        return api_key


class SSOAuth(APIKeyCookie):
    """Authenticates via OpenStax Accounts SSO cookie."""
    param_name = "oxa"

    def authenticate(self, request, key):
        user_uuid = get_logged_in_user_uuid(request)
        if user_uuid is not None:
            request.auth_uuid = user_uuid
            request.auth_type = 'sso'
            request.auth_scopes = None
            return user_uuid
        return None


class ServiceAuth(HttpBearer):
    """Authenticates via API key in Authorization: Bearer header."""

    def authenticate(self, request, token):
        api_key = APIKey.authenticate(token)
        if api_key is not None:
            request.auth_type = 'api_key'
            request.auth_scopes = api_key.scopes
            request.auth_uuid = None
            request.auth_key_name = api_key.name
            return api_key
        return None


# Combined auth: tries SSO first, then API key
combined_auth = [SSOAuth(), ServiceAuth()]


def has_scope(request, scope):
    """Check if the request has a specific scope.
    SSO users with super auth have all scopes.
    API key users must have the scope in their key."""
    if getattr(request, 'auth_type', None) == 'sso':
        from django.conf import settings
        return getattr(request, 'auth_uuid', None) in settings.SUPER_USERS
    if getattr(request, 'auth_type', None) == 'api_key':
        return scope in getattr(request, 'auth_scopes', [])
    return False
