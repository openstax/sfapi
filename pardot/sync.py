"""
Tiered sync engine — pulls data from Pardot API and Salesforce SOQL into PostgreSQL.

Tier 1 "Set Up Camp"  — assets + SF aggregate counts      (~20 API calls)
Tier 2 "Scout"        — top prospects by score             (~5 additional calls)
Tier 3 "Full Survey"  — all prospects + activities         (~2500+ calls for 500k)
"""

import logging
import re
import time
from datetime import date, datetime, timedelta, timezone

from pardot.db_compat import (
    ACTIVITY_FIELD_MAP,
    PROSPECT_FIELD_MAP,
    get_cursor,
    map_activity,
    map_prospect,
)

log = logging.getLogger("sync")

PROSPECT_FIELDS = ",".join(PROSPECT_FIELD_MAP.keys())
ACTIVITY_FIELDS = ",".join(ACTIVITY_FIELD_MAP.keys())


def _fmt_duration(seconds: float) -> str:
    """Format seconds into a human-readable duration like '2m 15s'."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"


class SyncEngine:
    # Single source of truth for all asset type configs.
    # Keys are DB table names. Each entry has:
    #   fetcher_attr: method name on PardotClient
    #   api_fields:   fields to request from the API
    #   field_map:    API camelCase → DB snake_case mapping
    #   endpoint, windowed, window_days: optional windowed pagination params
    ASSET_CONFIGS = {
        "campaigns": {
            "fetcher_attr": "get_campaigns",
            "api_fields": ["id", "name", "cost", "salesforceId", "folderId", "createdAt", "updatedAt"],
            "field_map": {
                "id": "id",
                "name": "name",
                "cost": "cost",
                "salesforceId": "salesforce_id",
                "folderId": "folder_id",
                "createdAt": "created_at",
                "updatedAt": "updated_at",
            },
        },
        "lists": {
            "fetcher_attr": "get_lists",
            "api_fields": ["id", "name", "isDynamic", "isPublic", "title", "createdAt", "updatedAt"],
            "field_map": {
                "id": "id",
                "name": "name",
                "isDynamic": "is_dynamic",
                "isPublic": "is_public",
                "title": "title",
                "createdAt": "created_at",
                "updatedAt": "updated_at",
            },
        },
        "forms": {
            "fetcher_attr": "get_forms",
            "api_fields": ["id", "name", "campaignId", "folderId", "embedCode", "createdAt", "updatedAt"],
            "field_map": {
                "id": "id",
                "name": "name",
                "campaignId": "campaign_id",
                "folderId": "folder_id",
                "embedCode": "embed_code",
                "createdAt": "created_at",
                "updatedAt": "updated_at",
            },
        },
        "landing_pages": {
            "fetcher_attr": "get_landing_pages",
            "api_fields": ["id", "name", "campaignId", "folderId", "url", "createdAt", "updatedAt"],
            "field_map": {
                "id": "id",
                "name": "name",
                "campaignId": "campaign_id",
                "folderId": "folder_id",
                "url": "url",
                "createdAt": "created_at",
                "updatedAt": "updated_at",
            },
        },
        "list_emails": {
            "fetcher_attr": "get_list_emails",
            "api_fields": ["id", "name", "campaignId", "subject", "folderId", "isSent", "createdAt", "updatedAt"],
            "field_map": {
                "id": "id",
                "name": "name",
                "campaignId": "campaign_id",
                "subject": "subject",
                "folderId": "folder_id",
                "isSent": "is_sent",
                "createdAt": "created_at",
                "updatedAt": "updated_at",
            },
        },
        "custom_redirects": {
            "fetcher_attr": "get_custom_redirects",
            "api_fields": ["id", "name", "campaignId", "url", "folderId", "createdAt", "updatedAt"],
            "field_map": {
                "id": "id",
                "name": "name",
                "campaignId": "campaign_id",
                "url": "url",
                "folderId": "folder_id",
                "createdAt": "created_at",
                "updatedAt": "updated_at",
            },
        },
        "folders": {
            "fetcher_attr": "get_folders",
            "api_fields": ["id", "name", "parentFolderId", "createdAt", "updatedAt"],
            "field_map": {
                "id": "id",
                "name": "name",
                "parentFolderId": "parent_folder_id",
                "createdAt": "created_at",
                "updatedAt": "updated_at",
            },
        },
        "tags": {
            "fetcher_attr": "get_tags",
            "api_fields": ["id", "name", "objectCount", "createdAt", "updatedAt"],
            "field_map": {
                "id": "id",
                "name": "name",
                "objectCount": "object_count",
                "createdAt": "created_at",
                "updatedAt": "updated_at",
            },
        },
        "tagged_objects": {
            "fetcher_attr": "get_tagged_objects",
            "api_fields": ["id", "tagId", "objectType", "objectId", "objectName", "createdAt"],
            "field_map": {
                "id": "id",
                "tagId": "tag_id",
                "objectType": "object_type",
                "objectId": "object_id",
                "objectName": "object_name",
                "createdAt": "created_at",
            },
            "endpoint": "objects/tagged-objects",
            "windowed": True,
            "window_days": 180,
        },
    }

    ENTITY_ALIASES = {
        "emails": "list_emails",
        "lps": "landing_pages",
        "redirects": "custom_redirects",
        "sf_dates": "sf_campaign_dates",
        "scores": "scoring_categories",
        "members": "campaign_members",
        "member_counts": "campaign_member_counts",
    }

    ENTITY_GROUPS = {
        "assets": list(ASSET_CONFIGS.keys()),
        "all": list(ASSET_CONFIGS.keys())
        + [
            "prospects",
            "activities",
            "sf_health",
            "sf_campaign_dates",
            "scoring_categories",
            "campaign_member_counts",
            "campaign_members",
        ],
    }

    def __init__(self, pardot_client, conn):
        self.pardot = pardot_client
        self.conn = conn

    # ══════════════════════════════════════════════════════════════
    # TIER 1: Set Up Camp — assets + SF health counts
    # ══════════════════════════════════════════════════════════════

    def sync_assets(self, force_full=False) -> dict:
        """Sync all 9 asset types from Pardot. Returns counts per type."""
        counts = {}
        for name, cfg in self.ASSET_CONFIGS.items():
            fetcher = getattr(self.pardot, cfg["fetcher_attr"])
            counts[name] = self._sync_asset_type(
                name,
                fetcher,
                cfg["api_fields"],
                cfg["field_map"],
                endpoint=cfg.get("endpoint"),
                windowed=cfg.get("windowed", False),
                window_days=cfg.get("window_days", 180),
                force_full=force_full,
            )
        return counts

    def sync_tags(self) -> dict:
        """Sync tags and tagged-object associations. Returns counts."""
        counts = {}
        for name in ("tags", "tagged_objects"):
            cfg = self.ASSET_CONFIGS[name]
            fetcher = getattr(self.pardot, cfg["fetcher_attr"])
            counts[name] = self._sync_asset_type(
                name,
                fetcher,
                cfg["api_fields"],
                cfg["field_map"],
                endpoint=cfg.get("endpoint"),
                windowed=cfg.get("windowed", False),
                window_days=cfg.get("window_days", 180),
            )
        return counts

    @staticmethod
    def sync_sf_campaign_dates(sf, conn):
        """Fetch CreatedDate, LastModifiedDate, StartDate, EndDate from SF Campaigns
        and update our local campaigns table."""
        with get_cursor(conn) as cur:
            cur.execute(
                "SELECT id, salesforce_id FROM campaigns WHERE salesforce_id IS NOT NULL AND salesforce_id != ''"
            )
            rows = cur.fetchall()

        if not rows:
            log.info("No campaigns with SF IDs to enrich.")
            return

        sf_ids = [r["salesforce_id"][:18] for r in rows]
        # Batch in groups of 200 for SOQL IN clause
        updated = 0
        for i in range(0, len(sf_ids), 200):
            batch = sf_ids[i : i + 200]
            id_list = "','".join(batch)
            soql = (
                f"SELECT Id, CreatedDate, LastModifiedDate, StartDate, EndDate FROM Campaign WHERE Id IN ('{id_list}')"  # noqa: S608
            )
            try:
                result = sf.query_all(soql)
            except Exception as e:
                log.warning(f"SOQL campaign dates query failed: {e}")
                continue

            sf_map = {}
            for rec in result.get("records", []):
                sf_map[rec["Id"][:15]] = rec

            with get_cursor(conn) as cur:
                for row in rows[i : i + 200]:
                    sf_id_15 = row["salesforce_id"][:15]
                    rec = sf_map.get(sf_id_15)
                    if not rec:
                        continue
                    cur.execute(
                        """
                        UPDATE campaigns SET
                            sf_created_at = %s, sf_modified_at = %s,
                            start_date = %s, end_date = %s
                        WHERE id = %s
                    """,
                        (
                            rec.get("CreatedDate"),
                            rec.get("LastModifiedDate"),
                            rec.get("StartDate"),
                            rec.get("EndDate"),
                            row["id"],
                        ),
                    )
                    updated += 1

        log.info(f"Enriched {updated} campaigns with SF dates.")

    @staticmethod
    def sync_scoring_categories(sf, conn):
        """Fetch per-category scores from SF custom objects and upsert into scoring_categories.

        Queries pi__Category_Lead_Score__c (linked by LeadId) and
        pi__Category_Contact_Score__c (linked by ContactId).
        ~6 SOQL calls total for 500 prospects.
        """
        # Build reverse map: sf_id_15 → prospect_id
        with get_cursor(conn) as cur:
            cur.execute("""
                SELECT id, salesforce_lead_id, salesforce_contact_id
                FROM prospects WHERE is_deleted = FALSE
            """)
            rows = cur.fetchall()

        if not rows:
            log.info("No prospects to fetch scoring categories for.")
            return

        lead_map = {}  # sf_id_15 → prospect_id
        contact_map = {}
        lead_ids = []
        contact_ids = []
        _sf_id_re = re.compile(r"^[a-zA-Z0-9]{15,18}$")
        for r in rows:
            if r["salesforce_lead_id"] and _sf_id_re.match(r["salesforce_lead_id"]):
                sf15 = r["salesforce_lead_id"][:15]
                lead_map[sf15] = r["id"]
                lead_ids.append(r["salesforce_lead_id"][:18])
            if r["salesforce_contact_id"] and _sf_id_re.match(r["salesforce_contact_id"]):
                sf15 = r["salesforce_contact_id"][:15]
                contact_map[sf15] = r["id"]
                contact_ids.append(r["salesforce_contact_id"][:18])

        total = 0

        # Query Lead scoring categories in batches of 200
        for i in range(0, len(lead_ids), 200):
            batch = lead_ids[i : i + 200]
            id_list = "','".join(batch)
            soql = f"SELECT pi__Lead__c, pi__Scoring_Category_Name__c, pi__Score__c FROM pi__Category_Lead_Score__c WHERE pi__Lead__c IN ('{id_list}')"  # noqa: S608
            try:
                result = sf.query_all(soql)
            except Exception as e:
                log.warning(f"SOQL lead scoring category query failed: {e}")
                continue

            upserts = []
            for rec in result.get("records", []):
                sf15 = rec["pi__Lead__c"][:15]
                pid = lead_map.get(sf15)
                if pid and rec.get("pi__Scoring_Category_Name__c"):
                    upserts.append((pid, rec["pi__Scoring_Category_Name__c"], rec.get("pi__Score__c") or 0))

            if upserts:
                with get_cursor(conn) as cur:
                    for pid, cat, score in upserts:
                        cur.execute(
                            """
                            INSERT INTO scoring_categories (prospect_id, category_name, score, cached_at)
                            VALUES (%s, %s, %s, NOW())
                            ON CONFLICT (prospect_id, category_name) DO UPDATE SET
                                score = EXCLUDED.score, cached_at = NOW()
                        """,
                            (pid, cat, score),
                        )
                total += len(upserts)

        # Query Contact scoring categories in batches of 200
        for i in range(0, len(contact_ids), 200):
            batch = contact_ids[i : i + 200]
            id_list = "','".join(batch)
            soql = f"SELECT pi__Contact__c, pi__Scoring_Category_Name__c, pi__Score__c FROM pi__Category_Contact_Score__c WHERE pi__Contact__c IN ('{id_list}')"  # noqa: S608
            try:
                result = sf.query_all(soql)
            except Exception as e:
                log.warning(f"SOQL contact scoring category query failed: {e}")
                continue

            upserts = []
            for rec in result.get("records", []):
                sf15 = rec["pi__Contact__c"][:15]
                pid = contact_map.get(sf15)
                if pid and rec.get("pi__Scoring_Category_Name__c"):
                    upserts.append((pid, rec["pi__Scoring_Category_Name__c"], rec.get("pi__Score__c") or 0))

            if upserts:
                with get_cursor(conn) as cur:
                    for pid, cat, score in upserts:
                        cur.execute(
                            """
                            INSERT INTO scoring_categories (prospect_id, category_name, score, cached_at)
                            VALUES (%s, %s, %s, NOW())
                            ON CONFLICT (prospect_id, category_name) DO UPDATE SET
                                score = EXCLUDED.score, cached_at = NOW()
                        """,
                            (pid, cat, score),
                        )
                total += len(upserts)

        log.info(f"Synced {total} scoring category records for {len(rows)} prospects.")

    @staticmethod
    def sync_sf_health(sf, conn) -> dict:
        """Run SOQL aggregate queries for SF-side health counts. Cheap and fast."""
        log.info("Querying SF health counts via SOQL...")

        counts = {"total_leads": 0, "total_contacts": 0, "leads_with_pardot": 0, "contacts_with_pardot": 0}

        try:
            r = sf.query("SELECT COUNT() FROM Lead")
            counts["total_leads"] = r["totalSize"]
        except Exception as e:
            log.warning(f"Could not count Leads: {e}")

        try:
            r = sf.query("SELECT COUNT() FROM Contact")
            counts["total_contacts"] = r["totalSize"]
        except Exception as e:
            log.warning(f"Could not count Contacts: {e}")

        try:
            r = sf.query("SELECT COUNT() FROM Lead WHERE pi__url__c != null")
            counts["leads_with_pardot"] = r["totalSize"]
        except Exception as e:
            log.warning(f"Could not count Leads with pi__url__c: {e}")

        try:
            r = sf.query("SELECT COUNT() FROM Contact WHERE pi__url__c != null")
            counts["contacts_with_pardot"] = r["totalSize"]
        except Exception as e:
            log.warning(f"Could not count Contacts with pi__url__c: {e}")

        # Store in sf_health table
        with get_cursor(conn) as cur:
            cur.execute(
                """
                INSERT INTO sf_health (total_leads, total_contacts, leads_with_pardot, contacts_with_pardot)
                VALUES (%s, %s, %s, %s)
            """,
                (
                    counts["total_leads"],
                    counts["total_contacts"],
                    counts["leads_with_pardot"],
                    counts["contacts_with_pardot"],
                ),
            )

        log.info(
            f"SF health: {counts['total_leads']} leads, {counts['total_contacts']} contacts, "
            f"{counts['leads_with_pardot']} leads linked, {counts['contacts_with_pardot']} contacts linked"
        )
        return counts

    @staticmethod
    def sync_campaign_member_counts(sf, conn):
        """Fetch CampaignMember data per campaign from SF and aggregate in Python (Tier 1).

        SOQL doesn't support CASE WHEN, so we fetch raw fields and count locally.
        Batched in groups of 50 SF Campaign IDs to avoid URL length limits.
        """
        with get_cursor(conn) as cur:
            cur.execute(
                "SELECT DISTINCT salesforce_id FROM campaigns WHERE salesforce_id IS NOT NULL AND salesforce_id != ''"
            )
            rows = cur.fetchall()

        if not rows:
            log.info("No SF-linked campaigns to count members for.")
            return 0

        sf_ids = [r["salesforce_id"][:18] for r in rows]
        total_upserted = 0

        for i in range(0, len(sf_ids), 50):
            batch = sf_ids[i : i + 50]
            id_list = "','".join(batch)
            soql = f"SELECT CampaignId, HasResponded, LeadId, ContactId FROM CampaignMember WHERE CampaignId IN ('{id_list}')"  # noqa: S608
            try:
                result = sf.query_all(soql)
            except Exception as e:
                log.warning(f"SOQL campaign member query failed: {e}")
                continue

            # Aggregate in Python
            counts_by_campaign = {}  # sf_id -> {total, responded, leads, contacts}
            for rec in result.get("records", []):
                cid = rec["CampaignId"]
                if cid not in counts_by_campaign:
                    counts_by_campaign[cid] = {"total": 0, "responded": 0, "leads": 0, "contacts": 0}
                c = counts_by_campaign[cid]
                c["total"] += 1
                if rec.get("HasResponded"):
                    c["responded"] += 1
                if rec.get("LeadId"):
                    c["leads"] += 1
                if rec.get("ContactId"):
                    c["contacts"] += 1

            with get_cursor(conn) as cur:
                for cid, c in counts_by_campaign.items():
                    cur.execute(
                        """
                        INSERT INTO campaign_member_counts
                            (campaign_sf_id, total_members, responded_members, lead_members, contact_members, cached_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (campaign_sf_id) DO UPDATE SET
                            total_members = EXCLUDED.total_members,
                            responded_members = EXCLUDED.responded_members,
                            lead_members = EXCLUDED.lead_members,
                            contact_members = EXCLUDED.contact_members,
                            cached_at = NOW()
                    """,
                        (cid, c["total"], c["responded"], c["leads"], c["contacts"]),
                    )
                    total_upserted += 1

                # Zero-out campaigns in this batch that had no members
                found_ids = {cid[:15] for cid in counts_by_campaign}
                for sf_id in batch:
                    if sf_id[:15] not in found_ids:
                        cur.execute(
                            """
                            INSERT INTO campaign_member_counts
                                (campaign_sf_id, total_members, responded_members, lead_members, contact_members, cached_at)
                            VALUES (%s, 0, 0, 0, 0, NOW())
                            ON CONFLICT (campaign_sf_id) DO UPDATE SET
                                total_members = 0, responded_members = 0,
                                lead_members = 0, contact_members = 0, cached_at = NOW()
                        """,
                            (sf_id,),
                        )
                        total_upserted += 1

        log.info(f"Synced campaign member counts for {total_upserted} SF-linked campaigns.")
        return total_upserted

    @staticmethod
    def sync_campaign_members(sf, conn):
        """Fetch individual CampaignMember rows from SF (Tier 2).

        Only syncs for campaigns that have a salesforce_id.
        Batched in groups of 50 campaign IDs to avoid URL length limits.
        """
        with get_cursor(conn) as cur:
            cur.execute(
                "SELECT DISTINCT salesforce_id FROM campaigns WHERE salesforce_id IS NOT NULL AND salesforce_id != ''"
            )
            rows = cur.fetchall()

        if not rows:
            log.info("No SF-linked campaigns to sync members for.")
            return 0

        sf_ids = [r["salesforce_id"][:18] for r in rows]
        total = 0

        for i in range(0, len(sf_ids), 50):
            batch = sf_ids[i : i + 50]
            id_list = "','".join(batch)
            soql = f"SELECT Id, CampaignId, LeadId, ContactId, Status, HasResponded, CreatedDate, FirstRespondedDate FROM CampaignMember WHERE CampaignId IN ('{id_list}')"  # noqa: S608
            try:
                result = sf.query_all(soql)
            except Exception as e:
                log.warning(f"SOQL campaign member query failed: {e}")
                continue

            records = result.get("records", [])
            if not records:
                continue

            with get_cursor(conn) as cur:
                for rec in records:
                    cur.execute(
                        """
                        INSERT INTO campaign_members
                            (id, campaign_sf_id, lead_id, contact_id, status,
                             has_responded, created_date, first_responded_date, cached_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (id) DO UPDATE SET
                            campaign_sf_id = EXCLUDED.campaign_sf_id,
                            lead_id = EXCLUDED.lead_id,
                            contact_id = EXCLUDED.contact_id,
                            status = EXCLUDED.status,
                            has_responded = EXCLUDED.has_responded,
                            created_date = EXCLUDED.created_date,
                            first_responded_date = EXCLUDED.first_responded_date,
                            cached_at = NOW()
                    """,
                        (
                            rec["Id"],
                            rec["CampaignId"],
                            rec.get("LeadId"),
                            rec.get("ContactId"),
                            rec.get("Status"),
                            rec.get("HasResponded", False),
                            rec.get("CreatedDate"),
                            rec.get("FirstRespondedDate"),
                        ),
                    )
                    total += 1

            if total % 5000 == 0 and total > 0:
                log.info(f"  ...{total} campaign members synced so far")

        log.info(f"Synced {total} campaign members across {len(sf_ids)} SF-linked campaigns.")
        return total

    @staticmethod
    def save_daily_snapshot(conn, tier=1):
        """Capture today's metrics into daily_snapshots. Only writes data for the given tier."""
        today = date.today()

        with get_cursor(conn) as cur:
            # Tier 1: assets + SF health (always available)
            cur.execute("SELECT COUNT(*) AS n FROM campaigns")
            total_campaigns = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM lists")
            total_lists = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM forms")
            total_forms = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM landing_pages")
            total_lps = cur.fetchone()["n"]

            cur.execute("SELECT * FROM sf_health ORDER BY captured_at DESC LIMIT 1")
            sf = cur.fetchone()

            # Start building the upsert
            cols = [
                "snapshot_date",
                "total_campaigns",
                "total_lists",
                "total_forms",
                "total_landing_pages",
                "sf_leads_total",
                "sf_contacts_total",
                "sf_leads_with_pardot",
                "sf_contacts_with_pardot",
            ]
            vals = [
                today,
                total_campaigns,
                total_lists,
                total_forms,
                total_lps,
                sf["total_leads"] if sf else None,
                sf["total_contacts"] if sf else None,
                sf["leads_with_pardot"] if sf else None,
                sf["contacts_with_pardot"] if sf else None,
            ]

            # Campaign member counts (Tier 1 — from SF CampaignMember aggregates)
            try:
                cur.execute("""
                    SELECT COUNT(*) FILTER (WHERE cmc.total_members > 0) AS with_members,
                           COUNT(*) FILTER (WHERE cmc.total_members = 0) AS no_members
                    FROM campaigns c
                    JOIN campaign_member_counts cmc ON cmc.campaign_sf_id = c.salesforce_id
                    WHERE c.salesforce_id IS NOT NULL AND c.salesforce_id != ''
                """)
                cm_row = cur.fetchone()
                cols += ["campaigns_with_members", "campaigns_no_members_snap"]
                vals += [cm_row["with_members"] or 0, cm_row["no_members"] or 0]
            except Exception:
                log.debug("campaign_member_counts table may not exist yet")

            # Tier 2: prospect sample stats
            if tier >= 2:
                cur.execute("SELECT COUNT(*) AS n FROM prospects WHERE is_deleted = FALSE")
                sampled = cur.fetchone()["n"]
                cur.execute(
                    "SELECT MAX(score) AS mx, COALESCE(AVG(score), 0) AS av FROM prospects WHERE is_deleted = FALSE"
                )
                score_row = cur.fetchone()
                cols += ["prospects_sampled", "top_score", "avg_score_sampled"]
                vals += [sampled, score_row["mx"] or 0, round(float(score_row["av"]), 1)]

            # Tier 3: full prospect + activity stats
            if tier >= 3:
                cur.execute("""
                    SELECT COUNT(*) AS n FROM prospects
                    WHERE is_deleted = FALSE
                      AND (salesforce_id IS NOT NULL AND salesforce_id != ''
                        OR salesforce_lead_id IS NOT NULL AND salesforce_lead_id != ''
                        OR salesforce_contact_id IS NOT NULL AND salesforce_contact_id != '')
                """)
                synced = cur.fetchone()["n"]

                cur.execute("""
                    SELECT COUNT(*) AS n FROM prospects
                    WHERE is_deleted = FALSE
                      AND (salesforce_id IS NULL OR salesforce_id = '')
                      AND (salesforce_lead_id IS NULL OR salesforce_lead_id = '')
                      AND (salesforce_contact_id IS NULL OR salesforce_contact_id = '')
                """)
                unlinked = cur.fetchone()["n"]

                cur.execute(
                    "SELECT pardot_missing_crm, sf_missing_pardot FROM orphan_runs ORDER BY run_at DESC LIMIT 1"
                )
                orph = cur.fetchone()

                cur.execute(
                    "SELECT COUNT(DISTINCT prospect_id) AS n FROM visitor_activities WHERE created_at > NOW() - INTERVAL '30 days'"
                )
                active_30d = cur.fetchone()["n"]

                cur.execute("SELECT COUNT(*) AS n FROM prospects WHERE is_deleted = FALSE")
                total_p = cur.fetchone()["n"]

                cols += [
                    "total_prospects",
                    "synced_prospects",
                    "unlinked_prospects",
                    "pardot_orphans",
                    "sf_orphans",
                    "active_prospects_30d",
                ]
                vals += [
                    total_p,
                    synced,
                    unlinked,
                    orph["pardot_missing_crm"] if orph else 0,
                    orph["sf_missing_pardot"] if orph else 0,
                    active_30d,
                ]

            # Scorecard: audit issue counts + health score
            try:
                from scorecard import compute_health_score

                hs = compute_health_score(conn)
                ic = hs.get("issue_counts", {})
                overall = hs.get("overall", {})

                audit_cols = [
                    "campaigns_no_sf",
                    "campaigns_empty",
                    "campaigns_dormant",
                    "campaigns_no_members",
                    "campaigns_low_response",
                    "campaigns_ghost",
                    "forms_no_campaign",
                    "forms_dormant",
                    "forms_errors",
                    "lps_no_campaign",
                    "lps_dormant",
                    "lists_stale",
                    "lists_stale_1y",
                    "lists_unnamed",
                    "emails_no_campaign",
                    "emails_no_subject",
                    "redirects_no_campaign",
                    "orphan_forms",
                    "orphan_lps",
                    "orphan_emails",
                    "orphan_redirects",
                ]
                for ac in audit_cols:
                    cols.append(ac)
                    vals.append(ic.get(ac, 0))

                cols += ["health_score", "health_grade"]
                vals += [overall.get("score", 0), overall.get("grade", "?")]

                # Task counts
                cur.execute(
                    "SELECT COUNT(*) FILTER (WHERE status = 'open') AS open, COUNT(*) FILTER (WHERE status = 'done') AS done FROM tasks"
                )
                task_row = cur.fetchone()
                cols += ["tasks_open", "tasks_done"]
                vals += [task_row["open"], task_row["done"]]

                log.info(f"Health score: {overall.get('score', '?')}/100 ({overall.get('grade', '?')})")
            except Exception as e:
                log.warning(f"Scorecard data not saved to snapshot: {e}")

            placeholders = ", ".join(["%s"] * len(cols))
            col_names = ", ".join(cols)
            updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "snapshot_date")

            cur.execute(
                f"""
                INSERT INTO daily_snapshots ({col_names})
                VALUES ({placeholders})
                ON CONFLICT (snapshot_date) DO UPDATE SET {updates}
            """,  # noqa: S608
                vals,
            )

        log.info(f"Saved Tier {tier} daily snapshot for {today}.")

    # ══════════════════════════════════════════════════════════════
    # TIER 2: Scout — top prospects by score
    # ══════════════════════════════════════════════════════════════

    def sync_top_prospects(self, limit=500) -> int:
        """Fetch prospects with recent activity, keep top N by score.

        Pardot API v5 only allows orderBy on id, createdAt, updatedAt,
        lastActivityAt — not score. So we fetch recently-active prospects
        and keep the highest-scored ones.
        """
        log.info(f"Fetching recently-active prospects to find top {limit} by score...")
        params = {"fields": PROSPECT_FIELDS, "orderBy": "lastActivityAt DESC"}

        # Fetch up to 5x the limit to get a good pool, then keep top N by score
        fetch_limit = limit * 5
        all_rows = []
        for record in self.pardot.get_prospects(**params):
            row = map_prospect(record)
            if "id" in row:
                all_rows.append(row)
            if len(all_rows) >= fetch_limit:
                break

        # Sort by score descending and keep top N
        all_rows.sort(key=lambda r: r.get("score") or 0, reverse=True)
        top_rows = all_rows[:limit]

        # Upsert in batches
        for i in range(0, len(top_rows), 500):
            self._upsert_prospects(top_rows[i : i + 500])

        self._update_sync_meta("prospects", f"top_{limit}", len(top_rows))
        log.info(f"Synced top {len(top_rows)} prospects by score (from {len(all_rows)} fetched).")
        return len(top_rows)

    # ══════════════════════════════════════════════════════════════
    # TIER 3: Full Survey — all prospects + activities
    # ══════════════════════════════════════════════════════════════

    def sync_prospects(self, force_full=False) -> int:
        """Full prospect sync. Returns count of upserted rows."""
        last_sync = None
        if not force_full:
            last_sync = self._get_last_sync("prospects")

        mode = "full" if force_full or not last_sync else "incremental"
        log.info(f"Syncing ALL prospects ({mode})...")

        if mode == "full":
            # Full sync uses windowed pagination to handle 500k+ prospects
            source = self.pardot.get_all_windowed(
                "objects/prospects",
                params={"fields": PROSPECT_FIELDS, "deleted": "all"},
                date_field="createdAt",
                window_days=180,
            )
        else:
            # Incremental sync — should be well under 100k
            source = self.pardot.get_prospects(
                fields=PROSPECT_FIELDS,
                deleted="all",
                updatedAtAfter=last_sync.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            )

        batch = []
        total = 0
        t0 = time.monotonic()
        for record in source:
            row = map_prospect(record)
            if "id" in row:
                batch.append(row)
            if len(batch) >= 500:
                total += self._upsert_prospects(batch)
                batch = []
                if total % 5000 == 0:
                    elapsed = time.monotonic() - t0
                    rate = total / elapsed if elapsed > 0 else 0
                    log.info(f"  ...{total} prospects synced so far ({_fmt_duration(elapsed)}, ~{rate:.0f}/s)")

        if batch:
            total += self._upsert_prospects(batch)

        elapsed = time.monotonic() - t0
        self._update_sync_meta("prospects", mode, total)
        log.info(f"Synced {total} prospects ({mode}) in {_fmt_duration(elapsed)}.")
        return total

    def sync_activities(self, days=30, force_full=False) -> int:
        """Sync visitor activities. Incremental from last sync by default."""
        last_sync = None if force_full else self._get_last_sync("visitor_activities")

        if last_sync:
            # True incremental — only fetch since last run.
            # 5-minute overlap guards against clock skew at window boundaries.
            cutoff = last_sync - timedelta(minutes=5)
            mode = "incremental"
            log.info(f"Syncing visitor activities (incremental from {last_sync:%Y-%m-%d %H:%M UTC})...")
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            mode = "full"
            log.info(f"Syncing visitor activities (initial {days}d window)...")

        # Use windowed pagination — activity volume can exceed 100k in 30 days
        source = self.pardot.get_all_windowed(
            "objects/visitor-activities",
            params={"fields": ACTIVITY_FIELDS},
            date_field="createdAt",
            start_date=cutoff,
            window_days=7,  # weekly windows for dense activity data
        )

        batch = []
        total = 0
        t0 = time.monotonic()
        for record in source:
            row = map_activity(record)
            if "id" in row:
                batch.append(row)
            if len(batch) >= 500:
                total += self._insert_activities(batch)
                batch = []
                if total % 5000 == 0:
                    elapsed = time.monotonic() - t0
                    rate = total / elapsed if elapsed > 0 else 0
                    log.info(f"  ...{total} activities synced so far ({_fmt_duration(elapsed)}, ~{rate:.0f}/s)")

        if batch:
            total += self._insert_activities(batch)

        elapsed = time.monotonic() - t0
        self._update_sync_meta("visitor_activities", mode, total)
        log.info(f"Synced {total} visitor activities ({mode}) in {_fmt_duration(elapsed)}.")
        return total

    # ══════════════════════════════════════════════════════════════
    # Internals
    # ══════════════════════════════════════════════════════════════

    def _upsert_prospects(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        cols = list(rows[0].keys())
        placeholders = ", ".join(["%s"] * len(cols))
        col_names = ", ".join(cols)
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "id")
        sql = f"""
            INSERT INTO prospects ({col_names})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE SET {updates}, cached_at = NOW()
        """  # noqa: S608
        with get_cursor(self.conn) as cur:
            for row in rows:
                cur.execute(sql, [row.get(c) for c in cols])
        return len(rows)

    def _insert_activities(self, rows: list[dict]) -> int:
        if not rows:
            return 0
        cols = list(rows[0].keys())
        col_names = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"INSERT INTO visitor_activities ({col_names}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"  # noqa: S608
        with get_cursor(self.conn) as cur:
            for row in rows:
                cur.execute(sql, [row.get(c) for c in cols])
        return len(rows)

    def sync_one(self, entity_type: str, force_full=False, sf=None, days=30) -> int:
        """Dispatch sync for a single entity type. Returns count."""
        if entity_type in self.ASSET_CONFIGS:
            cfg = self.ASSET_CONFIGS[entity_type]
            fetcher = getattr(self.pardot, cfg["fetcher_attr"])
            return self._sync_asset_type(
                entity_type,
                fetcher,
                cfg["api_fields"],
                cfg["field_map"],
                endpoint=cfg.get("endpoint"),
                windowed=cfg.get("windowed", False),
                window_days=cfg.get("window_days", 180),
                force_full=force_full,
            )
        elif entity_type == "prospects":
            return self.sync_prospects(force_full=force_full)
        elif entity_type == "activities":
            return self.sync_activities(days=days, force_full=force_full)
        elif entity_type == "sf_health":
            if sf is None:
                raise ValueError("sf_health requires a Salesforce client (pass sf=)")
            return len(self.sync_sf_health(sf, self.conn))
        elif entity_type == "sf_campaign_dates":
            if sf is None:
                raise ValueError("sf_campaign_dates requires a Salesforce client (pass sf=)")
            self.sync_sf_campaign_dates(sf, self.conn)
            return 0
        elif entity_type == "scoring_categories":
            if sf is None:
                raise ValueError("scoring_categories requires a Salesforce client (pass sf=)")
            self.sync_scoring_categories(sf, self.conn)
            return 0
        elif entity_type == "campaign_member_counts":
            if sf is None:
                raise ValueError("campaign_member_counts requires a Salesforce client (pass sf=)")
            return self.sync_campaign_member_counts(sf, self.conn)
        elif entity_type == "campaign_members":
            if sf is None:
                raise ValueError("campaign_members requires a Salesforce client (pass sf=)")
            return self.sync_campaign_members(sf, self.conn)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

    @classmethod
    def list_syncable_entities(cls) -> list[str]:
        """Return all valid entity type names for sync_one()."""
        return list(cls.ASSET_CONFIGS.keys()) + [
            "prospects",
            "activities",
            "sf_health",
            "sf_campaign_dates",
            "scoring_categories",
            "campaign_member_counts",
            "campaign_members",
        ]

    def _sync_asset_type(
        self,
        table: str,
        fetcher,
        api_fields: list,
        field_map: dict,
        endpoint: str | None = None,
        windowed: bool = False,
        date_field: str = "createdAt",
        window_days: int = 180,
        force_full: bool = False,
    ) -> int:
        fields_param = ",".join(api_fields)

        if windowed and endpoint:
            # Windowed types support incremental sync via start_date
            last_sync = None if force_full else self._get_last_sync(table)
            mode = "incremental" if last_sync else "full"
            log.info(f"Syncing {table} ({mode})...")
            source = self.pardot.get_all_windowed(
                endpoint,
                params={"fields": fields_param},
                date_field=date_field,
                window_days=window_days,
                start_date=last_sync,  # None → falls back to 2007 (full)
            )
        else:
            mode = "full"
            log.info(f"Syncing {table}...")
            source = fetcher(fields=fields_param)

        is_full_sync = mode == "full"
        seen_ids = set() if is_full_sync else None

        batch = []
        total = 0
        t0 = time.monotonic()
        for record in source:
            row = {}
            for api_key, db_key in field_map.items():
                if api_key in record:
                    row[db_key] = record[api_key]
            if "id" in row:
                batch.append(row)
                if is_full_sync:
                    seen_ids.add(row["id"])
            if len(batch) >= 500:
                self._upsert_batch(table, batch)
                total += len(batch)
                batch = []
                if total % 5000 == 0:
                    elapsed = time.monotonic() - t0
                    rate = total / elapsed if elapsed > 0 else 0
                    log.info(f"  ...{total} {table} synced so far ({_fmt_duration(elapsed)}, ~{rate:.0f}/s)")

        if batch:
            self._upsert_batch(table, batch)
            total += len(batch)

        # On full sync, remove rows that no longer exist in Pardot
        deleted = 0
        if is_full_sync and seen_ids:
            deleted = self._purge_stale_rows(table, seen_ids)

        elapsed = time.monotonic() - t0
        self._update_sync_meta(table, mode, total)
        if deleted:
            log.info(f"Synced {total} {table} ({mode}), purged {deleted} deleted rows, in {_fmt_duration(elapsed)}.")
        else:
            log.info(f"Synced {total} {table} ({mode}) in {_fmt_duration(elapsed)}.")
        return total

    def _purge_stale_rows(self, table: str, seen_ids: set) -> int:
        """Delete rows from table whose IDs were not seen during a full sync."""
        with get_cursor(self.conn) as cur:
            cur.execute(f"SELECT id FROM {table}")  # noqa: S608
            db_ids = {row["id"] for row in cur.fetchall()}
        stale_ids = db_ids - seen_ids
        if not stale_ids:
            return 0
        with get_cursor(self.conn) as cur:
            # Delete in batches to avoid overly large IN clauses
            stale_list = list(stale_ids)
            for i in range(0, len(stale_list), 500):
                batch = stale_list[i : i + 500]
                cur.execute(f"DELETE FROM {table} WHERE id = ANY(%s)", (batch,))  # noqa: S608
        log.info(f"Purged {len(stale_ids)} stale rows from {table}.")
        return len(stale_ids)

    def _upsert_batch(self, table: str, rows: list[dict]):
        """Generic batch upsert for any asset table."""
        if not rows:
            return
        cols = list(rows[0].keys())
        all_cols = cols + ["cached_at"]
        placeholders = ", ".join(["%s"] * len(cols)) + ", NOW()"
        col_names = ", ".join(all_cols)
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in cols if c != "id")
        sql = f"""
            INSERT INTO {table} ({col_names})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE SET {updates}, cached_at = NOW()
        """  # noqa: S608
        with get_cursor(self.conn) as cur:
            for row in rows:
                cur.execute(sql, [row.get(c) for c in cols])

    @staticmethod
    def get_sync_status(conn) -> list[dict]:
        with get_cursor(conn) as cur:
            cur.execute("SELECT * FROM sync_meta ORDER BY entity_type")
            return [dict(row) for row in cur.fetchall()]

    @staticmethod
    def get_last_asset_sync(conn):
        """Return the oldest last_sync_at among core asset types, or None if any are missing."""
        asset_types = [
            "campaigns",
            "lists",
            "forms",
            "landing_pages",
            "list_emails",
            "custom_redirects",
            "folders",
            "tags",
            "tagged_objects",
        ]
        with get_cursor(conn) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS synced, MIN(last_sync_at) AS oldest
                FROM sync_meta
                WHERE entity_type = ANY(%s)
            """,
                (asset_types,),
            )
            row = cur.fetchone()
            # All asset types must have been synced at least once
            if row["synced"] < len(asset_types):
                return None
            return row["oldest"]

    def _get_last_sync(self, entity_type: str):
        with get_cursor(self.conn) as cur:
            cur.execute("SELECT last_sync_at FROM sync_meta WHERE entity_type = %s", (entity_type,))
            row = cur.fetchone()
            return row["last_sync_at"] if row else None

    def _update_sync_meta(self, entity_type: str, mode: str, count: int):
        with get_cursor(self.conn) as cur:
            cur.execute(
                """
                INSERT INTO sync_meta (entity_type, last_sync_at, last_sync_mode, last_sync_count, updated_at)
                VALUES (%s, NOW(), %s, %s, NOW())
                ON CONFLICT (entity_type) DO UPDATE SET
                    last_sync_at = NOW(), last_sync_mode = EXCLUDED.last_sync_mode,
                    last_sync_count = EXCLUDED.last_sync_count, updated_at = NOW()
            """,
                (entity_type, mode, count),
            )
