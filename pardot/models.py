"""
Django models for Camp Campaign — Pardot/SF data health tracker.
Maps all 17 tables from the standalone psycopg2 schema to Django ORM models.
"""

from django.contrib.postgres.fields import ArrayField
from django.db import models


class SyncMeta(models.Model):
    entity_type = models.CharField(max_length=255, primary_key=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_mode = models.CharField(max_length=50, null=True, blank=True)
    last_sync_count = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_sync_meta"
        verbose_name = "Sync Meta"
        verbose_name_plural = "Sync Meta"

    def __str__(self):
        return self.entity_type


class Prospect(models.Model):
    id = models.BigIntegerField(primary_key=True)
    email = models.TextField(null=True, blank=True)
    first_name = models.TextField(null=True, blank=True)
    last_name = models.TextField(null=True, blank=True)
    company = models.TextField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    grade = models.TextField(null=True, blank=True)
    campaign_id = models.TextField(null=True, blank=True)
    salesforce_id = models.TextField(null=True, blank=True)
    salesforce_lead_id = models.TextField(null=True, blank=True)
    salesforce_contact_id = models.TextField(null=True, blank=True)
    salesforce_account_id = models.TextField(null=True, blank=True)
    adoption_json = models.TextField(null=True, blank=True)
    opted_out = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_prospects"
        indexes = [
            models.Index(fields=["email"], name="pardot_idx_prospect_email"),
            models.Index(fields=["salesforce_id"], name="pardot_idx_prospect_sf_id"),
            models.Index(fields=["salesforce_lead_id"], name="pardot_idx_prospect_sf_lead"),
            models.Index(fields=["salesforce_contact_id"], name="pardot_idx_prospect_sf_cont"),
            models.Index(fields=["-score"], name="pardot_idx_prospect_score"),
            models.Index(fields=["updated_at"], name="pardot_idx_prospect_updated"),
            models.Index(fields=["is_deleted"], name="pardot_idx_prospect_deleted"),
        ]

    def __str__(self):
        return self.email or f"Prospect {self.id}"


class VisitorActivity(models.Model):
    id = models.BigIntegerField(primary_key=True)
    type = models.IntegerField(null=True, blank=True)
    type_name = models.TextField(null=True, blank=True)
    prospect_id = models.BigIntegerField(null=True, blank=True)
    campaign_id = models.BigIntegerField(null=True, blank=True)
    form_id = models.BigIntegerField(null=True, blank=True)
    form_handler_id = models.BigIntegerField(null=True, blank=True)
    landing_page_id = models.BigIntegerField(null=True, blank=True)
    custom_redirect_id = models.BigIntegerField(null=True, blank=True)
    email_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_visitor_activities"
        indexes = [
            models.Index(fields=["prospect_id"], name="pardot_idx_va_prospect"),
            models.Index(fields=["created_at"], name="pardot_idx_va_created"),
            models.Index(fields=["type"], name="pardot_idx_va_type"),
            models.Index(fields=["campaign_id"], name="pardot_idx_va_campaign"),
            models.Index(fields=["form_id"], name="pardot_idx_va_form"),
            models.Index(fields=["form_handler_id"], name="pardot_idx_va_formhandler"),
            models.Index(fields=["landing_page_id"], name="pardot_idx_va_lp"),
            models.Index(fields=["custom_redirect_id"], name="pardot_idx_va_redirect"),
        ]

    def __str__(self):
        return f"Activity {self.id} ({self.type_name})"


class Campaign(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField(null=True, blank=True)
    cost = models.IntegerField(null=True, blank=True)
    salesforce_id = models.TextField(null=True, blank=True)
    folder_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    sf_created_at = models.DateTimeField(null=True, blank=True)
    sf_modified_at = models.DateTimeField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_campaigns"

    def __str__(self):
        return self.name or f"Campaign {self.id}"


class List(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField(null=True, blank=True)
    is_dynamic = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    title = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_lists"

    def __str__(self):
        return self.name or f"List {self.id}"


class Form(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField(null=True, blank=True)
    campaign_id = models.IntegerField(null=True, blank=True)
    folder_id = models.IntegerField(null=True, blank=True)
    embed_code = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_forms"

    def __str__(self):
        return self.name or f"Form {self.id}"


class LandingPage(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField(null=True, blank=True)
    campaign_id = models.IntegerField(null=True, blank=True)
    folder_id = models.IntegerField(null=True, blank=True)
    url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_landing_pages"

    def __str__(self):
        return self.name or f"LP {self.id}"


class ListEmail(models.Model):
    id = models.BigIntegerField(primary_key=True)
    name = models.TextField(null=True, blank=True)
    campaign_id = models.IntegerField(null=True, blank=True)
    subject = models.TextField(null=True, blank=True)
    folder_id = models.IntegerField(null=True, blank=True)
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_list_emails"

    def __str__(self):
        return self.name or f"Email {self.id}"


class CustomRedirect(models.Model):
    id = models.BigIntegerField(primary_key=True)
    name = models.TextField(null=True, blank=True)
    campaign_id = models.IntegerField(null=True, blank=True)
    url = models.TextField(null=True, blank=True)
    folder_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_custom_redirects"

    def __str__(self):
        return self.name or f"Redirect {self.id}"


class Folder(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField(null=True, blank=True)
    parent_folder_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_folders"

    def __str__(self):
        return self.name or f"Folder {self.id}"


class SFHealth(models.Model):
    captured_at = models.DateTimeField(auto_now_add=True)
    total_leads = models.IntegerField(default=0)
    total_contacts = models.IntegerField(default=0)
    leads_with_pardot = models.IntegerField(default=0)
    contacts_with_pardot = models.IntegerField(default=0)

    class Meta:
        db_table = "pardot_sf_health"
        indexes = [
            models.Index(fields=["captured_at"], name="pardot_idx_sfh_captured"),
        ]

    def __str__(self):
        return f"SF Health {self.captured_at}"


class OrphanRun(models.Model):
    run_at = models.DateTimeField(auto_now_add=True)
    pardot_missing_crm = models.IntegerField(default=0)
    sf_missing_pardot = models.IntegerField(default=0)
    unlinked_prospects = models.IntegerField(default=0)
    details_json = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "pardot_orphan_runs"

    def __str__(self):
        return f"Orphan Run {self.run_at}"


class DailySnapshot(models.Model):
    snapshot_date = models.DateField(unique=True)
    # Tier 1
    total_campaigns = models.IntegerField(default=0)
    total_lists = models.IntegerField(default=0)
    total_forms = models.IntegerField(default=0)
    total_landing_pages = models.IntegerField(default=0)
    sf_leads_total = models.IntegerField(null=True, blank=True)
    sf_contacts_total = models.IntegerField(null=True, blank=True)
    sf_leads_with_pardot = models.IntegerField(null=True, blank=True)
    sf_contacts_with_pardot = models.IntegerField(null=True, blank=True)
    # Tier 2
    prospects_sampled = models.IntegerField(null=True, blank=True)
    top_score = models.IntegerField(null=True, blank=True)
    avg_score_sampled = models.FloatField(null=True, blank=True)
    # Tier 3
    total_prospects = models.IntegerField(null=True, blank=True)
    synced_prospects = models.IntegerField(null=True, blank=True)
    unlinked_prospects = models.IntegerField(null=True, blank=True)
    pardot_orphans = models.IntegerField(null=True, blank=True)
    sf_orphans = models.IntegerField(null=True, blank=True)
    active_prospects_30d = models.IntegerField(null=True, blank=True)
    # Audit issues
    campaigns_no_sf = models.IntegerField(null=True, blank=True)
    campaigns_empty = models.IntegerField(null=True, blank=True)
    campaigns_dormant = models.IntegerField(null=True, blank=True)
    campaigns_no_members = models.IntegerField(null=True, blank=True)
    campaigns_low_response = models.IntegerField(null=True, blank=True)
    campaigns_ghost = models.IntegerField(null=True, blank=True)
    forms_no_campaign = models.IntegerField(null=True, blank=True)
    forms_dormant = models.IntegerField(null=True, blank=True)
    forms_errors = models.IntegerField(null=True, blank=True)
    lps_no_campaign = models.IntegerField(null=True, blank=True)
    lps_dormant = models.IntegerField(null=True, blank=True)
    lists_stale = models.IntegerField(null=True, blank=True)
    lists_stale_1y = models.IntegerField(null=True, blank=True)
    lists_unnamed = models.IntegerField(null=True, blank=True)
    emails_no_campaign = models.IntegerField(null=True, blank=True)
    emails_no_subject = models.IntegerField(null=True, blank=True)
    redirects_no_campaign = models.IntegerField(null=True, blank=True)
    orphan_forms = models.IntegerField(null=True, blank=True)
    orphan_lps = models.IntegerField(null=True, blank=True)
    orphan_emails = models.IntegerField(null=True, blank=True)
    orphan_redirects = models.IntegerField(null=True, blank=True)
    # Health score
    health_score = models.IntegerField(null=True, blank=True)
    health_grade = models.TextField(null=True, blank=True)
    # Tasks
    tasks_open = models.IntegerField(null=True, blank=True)
    tasks_done = models.IntegerField(null=True, blank=True)
    # Campaign members
    campaigns_with_members = models.IntegerField(null=True, blank=True)
    campaigns_no_members_snap = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "pardot_daily_snapshots"

    def __str__(self):
        return f"Snapshot {self.snapshot_date}"


class Task(models.Model):
    PRIORITY_CHOICES = [("high", "High"), ("normal", "Normal"), ("low", "Low")]
    STATUS_CHOICES = [("open", "Open"), ("done", "Done")]

    assignee = models.TextField()
    title = models.TextField()
    description = models.TextField(null=True, blank=True)
    area = models.TextField(null=True, blank=True)
    asset_type = models.TextField(null=True, blank=True)
    asset_id = models.IntegerField(null=True, blank=True)
    asset_name = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, default="open", choices=STATUS_CHOICES)
    priority = models.CharField(max_length=20, default="normal", choices=PRIORITY_CHOICES)
    created_by = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pardot_tasks"
        indexes = [
            models.Index(fields=["assignee"], name="pardot_idx_task_assignee"),
            models.Index(fields=["status"], name="pardot_idx_task_status"),
        ]

    def __str__(self):
        return f"[{self.status}] {self.title} ({self.assignee})"


class Tag(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.TextField(null=True, blank=True)
    object_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_tags"

    def __str__(self):
        return self.name or f"Tag {self.id}"


class TaggedObject(models.Model):
    id = models.BigIntegerField(primary_key=True)
    tag_id = models.IntegerField(null=True, blank=True)
    object_type = models.TextField(null=True, blank=True)
    object_id = models.BigIntegerField(null=True, blank=True)
    object_name = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_tagged_objects"
        indexes = [
            models.Index(fields=["tag_id"], name="pardot_idx_to_tag_id"),
            models.Index(fields=["object_type"], name="pardot_idx_to_obj_type"),
            models.Index(fields=["object_type", "object_id"], name="pardot_idx_to_type_id"),
        ]

    def __str__(self):
        return f"{self.object_type}:{self.object_id}"


class CampConfig(models.Model):
    key = models.CharField(max_length=255, primary_key=True)
    value = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_config"
        verbose_name = "Config Setting"
        verbose_name_plural = "Config Settings"

    def __str__(self):
        return self.key


class ScoringCategory(models.Model):
    prospect_id = models.BigIntegerField()
    category_name = models.TextField()
    score = models.FloatField(default=0)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_scoring_categories"
        constraints = [
            models.UniqueConstraint(
                fields=["prospect_id", "category_name"],
                name="pardot_scoring_cat_pk",
            ),
        ]
        indexes = [
            models.Index(fields=["prospect_id"], name="pardot_idx_sc_prospect"),
        ]

    def __str__(self):
        return f"{self.prospect_id}: {self.category_name} = {self.score}"


class CampaignMemberCount(models.Model):
    campaign_sf_id = models.CharField(max_length=18, primary_key=True)
    total_members = models.IntegerField(default=0)
    responded_members = models.IntegerField(default=0)
    lead_members = models.IntegerField(default=0)
    contact_members = models.IntegerField(default=0)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_campaign_member_counts"

    def __str__(self):
        return f"{self.campaign_sf_id}: {self.total_members} members"


class CampaignMember(models.Model):
    id = models.CharField(max_length=18, primary_key=True)
    campaign_sf_id = models.TextField(null=True, blank=True)
    lead_id = models.TextField(null=True, blank=True)
    contact_id = models.TextField(null=True, blank=True)
    status = models.TextField(null=True, blank=True)
    has_responded = models.BooleanField(default=False)
    created_date = models.DateTimeField(null=True, blank=True)
    first_responded_date = models.DateTimeField(null=True, blank=True)
    cached_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_campaign_members"
        indexes = [
            models.Index(fields=["campaign_sf_id"], name="pardot_idx_cm_campaign"),
            models.Index(fields=["lead_id"], name="pardot_idx_cm_lead"),
            models.Index(fields=["contact_id"], name="pardot_idx_cm_contact"),
        ]

    def __str__(self):
        return f"Member {self.id}"


class TeamMember(models.Model):
    name = models.TextField(unique=True)
    role = models.TextField(default="")
    owns = ArrayField(models.TextField(), default=list)
    label = models.TextField(default="")
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pardot_team_members"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.role})"
