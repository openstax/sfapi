"""
Django admin configuration for Camp Campaign.
Replaces the custom admin.html page — all config is managed through Django admin.
"""

from django.contrib import admin

from .models import (
    Campaign,
    CampaignMember,
    CampaignMemberCount,
    CampConfig,
    CustomRedirect,
    DailySnapshot,
    Folder,
    Form,
    LandingPage,
    List,
    ListEmail,
    OrphanRun,
    Prospect,
    ScoringCategory,
    SFHealth,
    SyncMeta,
    Tag,
    TaggedObject,
    Task,
    TeamMember,
    VisitorActivity,
)

# ── Config (the main admin screen replacement) ──


@admin.register(CampConfig)
class CampConfigAdmin(admin.ModelAdmin):
    list_display = ("key", "updated_at")
    search_fields = ("key",)
    readonly_fields = ("updated_at",)

    def has_delete_permission(self, request, obj=None):
        return True  # Deleting resets to hardcoded default


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "owns", "sort_order")
    list_editable = ("role", "sort_order")
    search_fields = ("name", "role")
    ordering = ("sort_order", "name")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "assignee", "status", "priority", "area", "created_at")
    list_filter = ("status", "priority", "assignee")
    list_editable = ("status", "priority")
    search_fields = ("title", "assignee", "description")
    readonly_fields = ("created_at", "updated_at", "completed_at")
    ordering = ("-created_at",)


# ── Read-mostly data (synced from Pardot/SF) ──


@admin.register(SyncMeta)
class SyncMetaAdmin(admin.ModelAdmin):
    list_display = ("entity_type", "last_sync_at", "last_sync_mode", "last_sync_count")
    readonly_fields = ("entity_type", "last_sync_at", "last_sync_mode", "last_sync_count", "updated_at")

    def has_add_permission(self, request):
        return False


@admin.register(DailySnapshot)
class DailySnapshotAdmin(admin.ModelAdmin):
    list_display = ("snapshot_date", "health_score", "health_grade", "total_campaigns", "total_forms")
    list_filter = ("health_grade",)
    ordering = ("-snapshot_date",)
    readonly_fields = [f.name for f in DailySnapshot._meta.get_fields() if f.name != "id"]

    def has_add_permission(self, request):
        return False


@admin.register(SFHealth)
class SFHealthAdmin(admin.ModelAdmin):
    list_display = ("captured_at", "total_leads", "total_contacts", "leads_with_pardot", "contacts_with_pardot")
    ordering = ("-captured_at",)

    def has_add_permission(self, request):
        return False


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "salesforce_id", "created_at")
    search_fields = ("name", "salesforce_id")
    list_filter = ("start_date",)
    readonly_fields = ("cached_at",)

    def has_add_permission(self, request):
        return False


@admin.register(Prospect)
class ProspectAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "company", "score", "grade", "is_deleted")
    search_fields = ("email", "company", "salesforce_id")
    list_filter = ("is_deleted", "opted_out", "grade")
    readonly_fields = ("cached_at",)

    def has_add_permission(self, request):
        return False


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "object_count")
    search_fields = ("name",)

    def has_add_permission(self, request):
        return False


@admin.register(OrphanRun)
class OrphanRunAdmin(admin.ModelAdmin):
    list_display = ("run_at", "pardot_missing_crm", "sf_missing_pardot", "unlinked_prospects")
    ordering = ("-run_at",)

    def has_add_permission(self, request):
        return False


# Register remaining models with minimal admin (read-only, synced data)
for model in [
    List,
    Form,
    LandingPage,
    ListEmail,
    CustomRedirect,
    Folder,
    VisitorActivity,
    TaggedObject,
    ScoringCategory,
    CampaignMemberCount,
    CampaignMember,
]:
    admin.site.register(model)
