from django.contrib import admin
from django.db.models import Sum

from .models import APIKey, FieldChangeLog, FormSubmission, RequestLog, SFAPIUsageLog, SuperUser, SyncConfig


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "method", "path", "status_code", "auth_type", "duration_ms")
    list_filter = ("method", "status_code", "auth_type")
    search_fields = ("path", "auth_identifier")
    readonly_fields = [f.name for f in RequestLog._meta.fields]
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FieldChangeLog)
class FieldChangeLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "model_name", "record_id", "field_name", "change_source", "changed_by")
    list_filter = ("model_name", "change_source")
    search_fields = ("record_id", "field_name")
    readonly_fields = [f.name for f in FieldChangeLog._meta.fields]
    ordering = ("-timestamp",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "key_prefix", "is_active", "expires_at", "last_used_at", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "key_prefix")
    readonly_fields = ("key_prefix", "key_hash", "created_at", "last_used_at")


@admin.register(SuperUser)
class SuperUserAdmin(admin.ModelAdmin):
    list_display = ("name", "accounts_uuid", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "accounts_uuid")


@admin.register(SyncConfig)
class SyncConfigAdmin(admin.ModelAdmin):
    list_display = ("sync_enabled", "pause_threshold", "api_limit", "last_usage_display")
    readonly_fields = ("last_usage_check", "last_usage_value", "last_usage_limit")
    fieldsets = (
        ("Kill Switch", {"fields": ("sync_enabled",)}),
        ("API Usage Threshold", {"fields": ("api_limit", "pause_threshold")}),
        (
            "Last Usage Check (auto-updated by sync commands)",
            {"fields": ("last_usage_check", "last_usage_value", "last_usage_limit")},
        ),
    )

    def last_usage_display(self, obj):
        if obj.last_usage_value is not None and obj.last_usage_limit:
            pct = obj.last_usage_value / obj.last_usage_limit * 100
            return f"{obj.last_usage_value:,}/{obj.last_usage_limit:,} ({pct:.1f}%)"
        return "No data"

    last_usage_display.short_description = "Last API Usage"

    def has_add_permission(self, request):
        # Only allow one instance
        return not SyncConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SFAPIUsageLog)
class SFAPIUsageLogAdmin(admin.ModelAdmin):
    list_display = ("date", "source", "call_count")
    list_filter = ("source", "date")
    ordering = ("-date", "source")
    readonly_fields = [f.name for f in SFAPIUsageLog._meta.fields]
    date_hierarchy = "date"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Add summary stats to the top of the list view
        extra_context = extra_context or {}
        from django.utils import timezone

        today = timezone.localdate()
        today_total = SFAPIUsageLog.objects.filter(date=today).aggregate(total=Sum("call_count"))["total"] or 0
        extra_context["title"] = f"SF API Usage Logs — Today: {today_total:,} calls"
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "form_type", "status", "auth_type", "created_at", "processed_at")
    list_filter = ("form_type", "status", "auth_type")
    search_fields = ("id", "form_type", "auth_identifier")
    readonly_fields = [f.name for f in FormSubmission._meta.fields]
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
