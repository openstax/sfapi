import uuid

from django.core.exceptions import ValidationError
from django.db import models

from .auth import APIKey  # noqa: F401 — re-export so Django finds it


class SyncConfig(models.Model):
    """Singleton configuration for Salesforce sync behavior. Managed via Django admin."""

    sync_enabled = models.BooleanField(
        default=True,
        help_text="Kill switch: uncheck to pause all sync management commands.",
    )
    api_limit = models.PositiveIntegerField(
        default=285000,
        help_text="Salesforce org's daily API call limit.",
    )
    pause_threshold = models.FloatField(
        default=0.85,
        help_text="Pause syncs when API usage exceeds this fraction of the limit (0.0-1.0).",
    )
    last_usage_check = models.DateTimeField(null=True, blank=True, editable=False)
    last_usage_value = models.PositiveIntegerField(null=True, blank=True, editable=False)
    last_usage_limit = models.PositiveIntegerField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "Sync Configuration"
        verbose_name_plural = "Sync Configuration"

    def __str__(self):
        status = "enabled" if self.sync_enabled else "PAUSED"
        return f"Sync config ({status}, pause at {self.pause_threshold:.0%} of {self.api_limit:,})"

    def save(self, *args, **kwargs):
        # Enforce singleton: always use pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SuperUser(models.Model):
    accounts_uuid = models.UUIDField(unique=True, help_text="OpenStax Accounts UUID for this super user.")
    name = models.CharField(max_length=255, blank=True, help_text="Human-readable name for identification.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Super User"
        verbose_name_plural = "Super Users"

    def __str__(self):
        return f"{self.name} ({self.accounts_uuid})" if self.name else str(self.accounts_uuid)

    @classmethod
    def is_super_user(cls, user_uuid):
        if user_uuid is None:
            return False
        try:
            return cls.objects.filter(accounts_uuid=user_uuid, is_active=True).exists()
        except (ValueError, ValidationError):
            return False


class RequestLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=2048)
    query_params = models.JSONField(default=dict, blank=True)
    auth_type = models.CharField(max_length=20, blank=True)
    auth_identifier = models.CharField(max_length=255, blank=True)
    status_code = models.IntegerField()
    duration_ms = models.IntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)

    class Meta:
        verbose_name = "Request Log"
        verbose_name_plural = "Request Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["path"], name="idx_reqlog_path"),
            models.Index(fields=["auth_type"], name="idx_reqlog_auth_type"),
        ]

    def __str__(self):
        return f"{self.method} {self.path} {self.status_code} ({self.timestamp})"


class FieldChangeLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    model_name = models.CharField(max_length=100)
    record_id = models.CharField(max_length=255)
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    change_source = models.CharField(
        max_length=20,
        choices=[("api", "API"), ("sync", "Sync"), ("admin", "Admin")],
        default="api",
    )
    changed_by = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Field Change Log"
        verbose_name_plural = "Field Change Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["model_name", "record_id"], name="idx_changelog_model_record"),
        ]

    def __str__(self):
        return f"{self.model_name}.{self.field_name} ({self.record_id}) at {self.timestamp}"


class FormSubmission(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("spam", "Spam"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form_type = models.CharField(max_length=50)
    data = models.JSONField()
    source_url = models.CharField(max_length=2048, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    sf_record_id = models.CharField(max_length=18, blank=True)
    error_message = models.TextField(blank=True)
    auth_type = models.CharField(max_length=20, blank=True)
    auth_identifier = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Form Submission"
        verbose_name_plural = "Form Submissions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.form_type} ({self.status}) - {self.id}"
