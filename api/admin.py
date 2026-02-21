from django.contrib import admin
from .models import RequestLog, FieldChangeLog, APIKey


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'method', 'path', 'status_code', 'auth_type', 'duration_ms')
    list_filter = ('method', 'status_code', 'auth_type')
    search_fields = ('path', 'auth_identifier')
    readonly_fields = [f.name for f in RequestLog._meta.fields]
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FieldChangeLog)
class FieldChangeLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'model_name', 'record_id', 'field_name', 'change_source', 'changed_by')
    list_filter = ('model_name', 'change_source')
    search_fields = ('record_id', 'field_name')
    readonly_fields = [f.name for f in FieldChangeLog._meta.fields]
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'key_prefix', 'is_active', 'expires_at', 'last_used_at', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'key_prefix')
    readonly_fields = ('key_prefix', 'key_hash', 'created_at', 'last_used_at')
