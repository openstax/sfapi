import uuid

from django.db import models

from .auth import APIKey  # noqa: F401 — re-export so Django finds it


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
