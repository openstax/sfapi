"""
Asset inventory — audit-oriented view of campaigns, lists, forms, landing pages.
Reads from PostgreSQL asset tables. Enriches with activity data when available.
"""

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from pardot import config
from pardot.db_compat import get_cursor

# Compiled once at module load — used in get_tag_review prefix detection
_TAG_PREFIX_CLEAN = re.compile(r"^([A-Za-z0-9_ ]+?)[\s]*[:|\-][\s]")
_TAG_PREFIX_CANON = re.compile(r"^([A-Za-z0-9_ ]+?)[\s]*[:\-\s]")

_EPOCH = datetime.min.replace(tzinfo=timezone.utc)


def _sort_by_date_desc(rows):
    """Sort rows: flagged first, then by most recent updated_at/created_at."""

    def _key(r):
        date = r.get("updated_at") or r.get("created_at") or _EPOCH
        if hasattr(date, "timestamp"):
            return (0 if r.get("flags") else 1, -date.timestamp())
        return (0 if r.get("flags") else 1, 0)

    rows.sort(key=_key)


log = logging.getLogger("assets")


def get_tag_review(conn) -> dict:
    """Analyze tag hygiene: unused tags, naming patterns, object coverage."""
    with get_cursor(conn) as cur:
        cur.execute("SELECT id, name, object_count, created_at, updated_at FROM tags ORDER BY name")
        tags = [dict(r) for r in cur.fetchall()]

        if not tags:
            return {
                "total_tags": 0,
                "total_tagged_objects": 0,
                "tags": [],
                "summary": {
                    "unused": 0,
                    "low_usage": 0,
                    "duplicate_prefix": 0,
                    "prospect_only": 0,
                    "no_naming_convention": 0,
                },
                "naming_patterns": [],
                "object_type_coverage": {},
            }

        # Per-tag object_type counts — aggregate in SQL instead of loading all rows
        cur.execute("""
            SELECT tag_id, object_type, COUNT(*) AS cnt
            FROM tagged_objects
            GROUP BY tag_id, object_type
        """)
        tag_type_map = defaultdict(lambda: defaultdict(int))
        for row in cur.fetchall():
            tag_type_map[row["tag_id"]][row["object_type"]] = row["cnt"]

        # Total tagged objects count
        cur.execute("SELECT COUNT(*) AS n FROM tagged_objects")
        total_tagged_objects = cur.fetchone()["n"]

        # Coverage: distinct tagged object_ids per object_type — aggregate in SQL
        cur.execute("""
            SELECT object_type, COUNT(DISTINCT object_id) AS tagged_count
            FROM tagged_objects
            GROUP BY object_type
        """)
        tagged_by_type_counts = {row["object_type"]: row["tagged_count"] for row in cur.fetchall()}

        # Asset table totals — one round-trip via UNION ALL
        cur.execute("""
            SELECT 'form'             AS obj_type, COUNT(*) AS n FROM forms
            UNION ALL
            SELECT 'landing-page',                 COUNT(*)        FROM landing_pages
            UNION ALL
            SELECT 'Campaign',                     COUNT(*)        FROM campaigns
            UNION ALL
            SELECT 'list',                         COUNT(*)        FROM lists
            UNION ALL
            SELECT 'email',                        COUNT(*)        FROM list_emails
            UNION ALL
            SELECT 'custom-redirect',              COUNT(*)        FROM custom_redirects
        """)
        table_totals = {row["obj_type"]: row["n"] for row in cur.fetchall()}

    # Detect naming patterns — single pass with module-level compiled regexes
    prefix_groups = defaultdict(list)
    prefix_canonical = defaultdict(list)
    for t in tags:
        name = t["name"] or ""
        m = _TAG_PREFIX_CLEAN.match(name)
        if m:
            prefix_groups[m.group(1).strip().lower()].append(name)
        m2 = _TAG_PREFIX_CANON.match(name)
        if m2:
            prefix_canonical[m2.group(1).strip().lower()].append(t["name"])

    # Only keep prefixes used by 2+ tags
    naming_patterns = [
        {"prefix": prefix, "count": len(names), "tags": sorted(names)}
        for prefix, names in sorted(prefix_groups.items(), key=lambda x: -len(x[1]))
        if len(names) >= 2
    ]
    patterned_tags = set()
    for p in naming_patterns:
        patterned_tags.update(p["tags"])

    # Detect duplicate prefixes (same prefix, inconsistent separators)
    dup_prefix_tags = set()
    for prefix, names in prefix_canonical.items():
        if len(names) >= 2:
            seps = set()
            for n in names:
                stripped = n[len(prefix) :].lstrip()
                if stripped:
                    seps.add(stripped[0])
            if len(seps) > 1:
                dup_prefix_tags.update(names)

    # Build enriched tag list with flags
    unused = 0
    low_usage = 0
    dup_prefix_count = 0
    prospect_only = 0
    no_convention = 0
    enriched = []
    for t in tags:
        types = dict(tag_type_map.get(t["id"], {}))
        actual_count = sum(types.values())
        flags = []

        if t["object_count"] == 0 and actual_count == 0:
            flags.append("unused")
            unused += 1
        elif actual_count == 1:
            flags.append("low_usage")
            low_usage += 1

        if t["name"] in dup_prefix_tags:
            flags.append("duplicate_prefix")
            dup_prefix_count += 1

        if types and all(ot == "prospect" for ot in types):
            flags.append("prospect_only")
            prospect_only += 1

        if t["name"] and t["name"] not in patterned_tags:
            flags.append("no_naming_convention")
            no_convention += 1

        enriched.append(
            {
                "id": t["id"],
                "name": t["name"],
                "object_count": t["object_count"] or 0,
                "object_types": types,
                "created_at": t["created_at"].isoformat() if t["created_at"] else None,
                "flags": flags,
            }
        )

    # Object type coverage
    coverage = {
        obj_type: {
            "tagged": tagged_by_type_counts.get(obj_type, 0),
            "total": table_totals.get(obj_type, 0),
        }
        for obj_type in ("form", "landing-page", "Campaign", "list", "email", "custom-redirect")
    }

    return {
        "total_tags": len(tags),
        "total_tagged_objects": total_tagged_objects,
        "tags": enriched,
        "summary": {
            "unused": unused,
            "low_usage": low_usage,
            "duplicate_prefix": dup_prefix_count,
            "prospect_only": prospect_only,
            "no_naming_convention": no_convention,
        },
        "naming_patterns": naming_patterns,
        "object_type_coverage": coverage,
    }


def get_asset_overview(conn) -> dict:
    """Count + 10 most recent per asset type."""
    overview = {}
    tables = {
        "campaigns": "campaigns",
        "lists": "lists",
        "forms": "forms",
        "landing_pages": "landing_pages",
        "list_emails": "list_emails",
        "custom_redirects": "custom_redirects",
    }

    with get_cursor(conn) as cur:
        for key, table in tables.items():
            cur.execute(f"SELECT COUNT(*) AS n FROM {table}")  # noqa: S608
            count = cur.fetchone()["n"]

            cur.execute(f"""
                SELECT id, name, created_at, updated_at
                FROM {table}
                ORDER BY COALESCE(updated_at, created_at) DESC NULLS LAST
                LIMIT 10
            """)  # noqa: S608
            recent = [dict(row) for row in cur.fetchall()]

            overview[key] = {"count": count, "recent": recent}

    return overview


def get_asset_summary(conn) -> dict:
    """Just the counts — used by digest and daily snapshot."""
    with get_cursor(conn) as cur:
        counts = {}
        for table in ["campaigns", "lists", "forms", "landing_pages", "list_emails", "custom_redirects"]:
            cur.execute(f"SELECT COUNT(*) AS n FROM {table}")  # noqa: S608
            counts[table] = cur.fetchone()["n"]
    return counts


def _has_activities(cur) -> bool:
    """Check if visitor_activities has any data."""
    cur.execute("SELECT EXISTS(SELECT 1 FROM visitor_activities LIMIT 1) AS has")
    return cur.fetchone()["has"]


def get_asset_detail(conn, asset_type: str) -> dict:
    """Return audit-enriched records + summary flags for an asset type.

    Returns: {
        "has_activities": bool,
        "summary": { counts and flag totals },
        "records": [ ... enriched rows ... ],
    }
    """
    valid = ("campaigns", "lists", "forms", "landing_pages", "list_emails", "custom_redirects")
    if asset_type not in valid:
        return {"has_activities": False, "summary": {}, "records": []}

    with get_cursor(conn) as cur:
        has_acts = _has_activities(cur)
        lookback_days = config.get_activity_lookback_days(conn)

        if asset_type == "campaigns":
            return _audit_campaigns(cur, has_acts, lookback_days)
        elif asset_type == "lists":
            return _audit_lists(cur, has_acts, conn)
        elif asset_type == "forms":
            return _audit_forms(cur, has_acts, lookback_days)
        elif asset_type == "landing_pages":
            return _audit_landing_pages(cur, has_acts, lookback_days)
        elif asset_type == "list_emails":
            return _audit_list_emails(cur, has_acts)
        elif asset_type == "custom_redirects":
            return _audit_custom_redirects(cur, has_acts, lookback_days)


def _audit_campaigns(cur, has_acts: bool, lookback_days: int) -> dict:
    if has_acts:
        cur.execute(
            """
            SELECT c.id, c.name, c.cost, c.salesforce_id, c.created_at, c.updated_at,
                   COUNT(DISTINCT f.id) AS form_count,
                   COUNT(DISTINCT lp.id) AS landing_page_count,
                   COUNT(DISTINCT le.id) AS email_count,
                   COUNT(DISTINCT cr.id) AS redirect_count,
                   COALESCE(va_stats.activity_count, 0) AS activity_count,
                   COALESCE(va_stats.activity_recent, 0) AS activity_30d,
                   va_stats.last_activity_at
            FROM campaigns c
            LEFT JOIN forms f ON f.campaign_id = c.id
            LEFT JOIN landing_pages lp ON lp.campaign_id = c.id
            LEFT JOIN list_emails le ON le.campaign_id = c.id
            LEFT JOIN custom_redirects cr ON cr.campaign_id = c.id
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS activity_count,
                       COUNT(*) FILTER (WHERE va.created_at >= NOW() - make_interval(days => %s)) AS activity_recent,
                       MAX(va.created_at) AS last_activity_at
                FROM visitor_activities va
                WHERE va.campaign_id = c.id
            ) va_stats ON true
            GROUP BY c.id, va_stats.activity_count, va_stats.activity_recent, va_stats.last_activity_at
            ORDER BY c.name
        """,
            (lookback_days,),
        )
    else:
        cur.execute("""
            SELECT c.id, c.name, c.cost, c.salesforce_id, c.created_at, c.updated_at,
                   COUNT(DISTINCT f.id) AS form_count,
                   COUNT(DISTINCT lp.id) AS landing_page_count,
                   COUNT(DISTINCT le.id) AS email_count,
                   COUNT(DISTINCT cr.id) AS redirect_count,
                   0 AS activity_count, 0 AS activity_30d,
                   NULL AS last_activity_at
            FROM campaigns c
            LEFT JOIN forms f ON f.campaign_id = c.id
            LEFT JOIN landing_pages lp ON lp.campaign_id = c.id
            LEFT JOIN list_emails le ON le.campaign_id = c.id
            LEFT JOIN custom_redirects cr ON cr.campaign_id = c.id
            GROUP BY c.id
            ORDER BY c.name
        """)

    rows = [dict(r) for r in cur.fetchall()]

    # Compute flags per row
    empty = 0
    no_activity = 0
    active = 0
    no_sf = 0
    for r in rows:
        flags = []
        total_assets = r["form_count"] + r["landing_page_count"] + r["email_count"] + r["redirect_count"]
        if total_assets == 0:
            flags.append("empty")
            empty += 1
        if not r.get("salesforce_id"):
            flags.append("no_sf")
            no_sf += 1
        if has_acts and r["activity_30d"] == 0:
            flags.append("dormant")
            no_activity += 1
        if has_acts and r["activity_30d"] > 0:
            active += 1
        r["flags"] = flags
        r["total_assets"] = total_assets

    _sort_by_date_desc(rows)

    summary = {
        "total": len(rows),
        "empty": empty,
        "no_sf": no_sf,
        "active_30d": active,
        "dormant": no_activity,
    }
    return {"has_activities": has_acts, "summary": summary, "records": rows}


def _audit_lists(cur, has_acts: bool, conn) -> dict:

    cur.execute("""
        SELECT id, name, title, is_dynamic, is_public, created_at, updated_at
        FROM lists ORDER BY name
    """)
    rows = [dict(r) for r in cur.fetchall()]

    stale_months, severe_months = config.get_list_stale_thresholds(conn)
    now = datetime.now(timezone.utc)
    cutoff_stale = now - timedelta(days=stale_months * 30)
    cutoff_severe = now - timedelta(days=severe_months * 30)

    dynamic = 0
    stale_6m = 0
    stale_1y = 0
    unnamed = 0
    for r in rows:
        flags = []
        if r["is_dynamic"]:
            dynamic += 1
        if not r["name"] or not r["name"].strip():
            flags.append("unnamed")
            unnamed += 1
        # Flag lists by staleness
        if r["updated_at"]:
            updated = r["updated_at"]
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            if updated < cutoff_severe:
                flags.append("stale_1y")
                stale_1y += 1
            elif updated < cutoff_stale:
                flags.append("stale")
                stale_6m += 1
        r["flags"] = flags

    _sort_by_date_desc(rows)

    summary = {
        "total": len(rows),
        "dynamic": dynamic,
        "static": len(rows) - dynamic,
        "stale_6m": stale_6m,
        "stale_1y": stale_1y,
        "unnamed": unnamed,
    }
    return {"has_activities": has_acts, "summary": summary, "records": rows}


def _audit_forms(cur, has_acts: bool, lookback_days: int) -> dict:
    if has_acts:
        cur.execute(
            """
            SELECT f.id, f.name, f.campaign_id, c.name AS campaign_name,
                   f.created_at, f.updated_at,
                   COALESCE(va_stats.total_submissions, 0) AS total_submissions,
                   COALESCE(va_stats.submissions_recent, 0) AS submissions_30d,
                   COALESCE(va_stats.errors_recent, 0) AS errors_30d,
                   va_stats.last_submission_at
            FROM forms f
            LEFT JOIN campaigns c ON c.id = f.campaign_id
            LEFT JOIN LATERAL (
                SELECT COUNT(*) FILTER (WHERE va.type IN (4, 14)) AS total_submissions,
                       COUNT(*) FILTER (WHERE va.type IN (4, 14) AND va.created_at >= NOW() - make_interval(days => %s)) AS submissions_recent,
                       COUNT(*) FILTER (WHERE va.type IN (3, 13) AND va.created_at >= NOW() - make_interval(days => %s)) AS errors_recent,
                       MAX(va.created_at) FILTER (WHERE va.type IN (4, 14)) AS last_submission_at
                FROM visitor_activities va
                WHERE va.form_id = f.id OR va.form_handler_id = f.id
            ) va_stats ON true
            ORDER BY f.name
        """,
            (lookback_days, lookback_days),
        )
    else:
        cur.execute("""
            SELECT f.id, f.name, f.campaign_id, c.name AS campaign_name,
                   f.created_at, f.updated_at,
                   0 AS total_submissions, 0 AS submissions_30d,
                   0 AS errors_30d, NULL AS last_submission_at
            FROM forms f
            LEFT JOIN campaigns c ON c.id = f.campaign_id
            ORDER BY f.name
        """)

    rows = [dict(r) for r in cur.fetchall()]

    no_campaign = 0
    no_submissions = 0
    has_errors = 0
    active = 0
    for r in rows:
        flags = []
        if not r["campaign_id"]:
            flags.append("no_campaign")
            no_campaign += 1
        if has_acts and r["submissions_30d"] == 0:
            flags.append("dormant")
            no_submissions += 1
        if has_acts and r["submissions_30d"] > 0:
            active += 1
        if has_acts and r["errors_30d"] > 0:
            flags.append("errors")
            has_errors += 1
        r["flags"] = flags

    _sort_by_date_desc(rows)

    summary = {
        "total": len(rows),
        "no_campaign": no_campaign,
        "active_30d": active,
        "dormant": no_submissions,
        "with_errors": has_errors,
    }
    return {"has_activities": has_acts, "summary": summary, "records": rows}


def _audit_landing_pages(cur, has_acts: bool, lookback_days: int) -> dict:
    if has_acts:
        cur.execute(
            """
            SELECT lp.id, lp.name, lp.campaign_id, c.name AS campaign_name,
                   lp.created_at, lp.updated_at,
                   COALESCE(va_stats.total_views, 0) AS total_views,
                   COALESCE(va_stats.views_recent, 0) AS views_30d,
                   va_stats.last_view_at
            FROM landing_pages lp
            LEFT JOIN campaigns c ON c.id = lp.campaign_id
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS total_views,
                       COUNT(*) FILTER (WHERE va.created_at >= NOW() - make_interval(days => %s)) AS views_recent,
                       MAX(va.created_at) AS last_view_at
                FROM visitor_activities va
                WHERE va.landing_page_id = lp.id
            ) va_stats ON true
            ORDER BY lp.name
        """,
            (lookback_days,),
        )
    else:
        cur.execute("""
            SELECT lp.id, lp.name, lp.campaign_id, c.name AS campaign_name,
                   lp.created_at, lp.updated_at,
                   0 AS total_views, 0 AS views_30d,
                   NULL AS last_view_at
            FROM landing_pages lp
            LEFT JOIN campaigns c ON c.id = lp.campaign_id
            ORDER BY lp.name
        """)

    rows = [dict(r) for r in cur.fetchall()]

    no_campaign = 0
    no_views = 0
    active = 0
    for r in rows:
        flags = []
        if not r["campaign_id"]:
            flags.append("no_campaign")
            no_campaign += 1
        if has_acts and r["views_30d"] == 0:
            flags.append("dormant")
            no_views += 1
        if has_acts and r["views_30d"] > 0:
            active += 1
        r["flags"] = flags

    _sort_by_date_desc(rows)

    summary = {
        "total": len(rows),
        "no_campaign": no_campaign,
        "active_30d": active,
        "dormant": no_views,
    }
    return {"has_activities": has_acts, "summary": summary, "records": rows}


def _audit_list_emails(cur, has_acts: bool) -> dict:
    cur.execute("""
        SELECT le.id, le.name, le.subject, le.campaign_id, le.is_sent, c.name AS campaign_name,
               le.created_at, le.updated_at
        FROM list_emails le
        LEFT JOIN campaigns c ON c.id = le.campaign_id
        ORDER BY le.name
    """)
    rows = [dict(r) for r in cur.fetchall()]

    no_campaign = 0
    no_subject = 0
    for r in rows:
        flags = []
        if not r["campaign_id"]:
            flags.append("no_campaign")
            no_campaign += 1
        if not r["subject"] or not r["subject"].strip():
            flags.append("no_subject")
            no_subject += 1
        r["flags"] = flags

    _sort_by_date_desc(rows)

    summary = {
        "total": len(rows),
        "no_campaign": no_campaign,
        "no_subject": no_subject,
    }
    return {"has_activities": has_acts, "summary": summary, "records": rows}


def _audit_custom_redirects(cur, has_acts: bool, lookback_days: int) -> dict:
    if has_acts:
        cur.execute(
            """
            SELECT cr.id, cr.name, cr.url, cr.campaign_id, c.name AS campaign_name,
                   cr.created_at, cr.updated_at,
                   COALESCE(va_stats.click_count, 0) AS click_count,
                   COALESCE(va_stats.clicks_recent, 0) AS clicks_30d,
                   va_stats.last_click_at
            FROM custom_redirects cr
            LEFT JOIN campaigns c ON c.id = cr.campaign_id
            LEFT JOIN LATERAL (
                SELECT COUNT(*) AS click_count,
                       COUNT(*) FILTER (WHERE va.created_at >= NOW() - make_interval(days => %s)) AS clicks_recent,
                       MAX(va.created_at) AS last_click_at
                FROM visitor_activities va
                WHERE va.custom_redirect_id = cr.id
            ) va_stats ON true
            ORDER BY cr.name
        """,
            (lookback_days,),
        )
    else:
        cur.execute("""
            SELECT cr.id, cr.name, cr.url, cr.campaign_id, c.name AS campaign_name,
                   cr.created_at, cr.updated_at,
                   0 AS click_count, 0 AS clicks_30d,
                   NULL AS last_click_at
            FROM custom_redirects cr
            LEFT JOIN campaigns c ON c.id = cr.campaign_id
            ORDER BY cr.name
        """)

    rows = [dict(r) for r in cur.fetchall()]

    no_campaign = 0
    dormant = 0
    active = 0
    for r in rows:
        flags = []
        if not r["campaign_id"]:
            flags.append("no_campaign")
            no_campaign += 1
        if has_acts and r["clicks_30d"] == 0:
            flags.append("dormant")
            dormant += 1
        if has_acts and r["clicks_30d"] > 0:
            active += 1
        r["flags"] = flags

    _sort_by_date_desc(rows)

    summary = {
        "total": len(rows),
        "no_campaign": no_campaign,
        "active_30d": active,
        "dormant": dormant,
    }
    return {"has_activities": has_acts, "summary": summary, "records": rows}


# ── Campaign Connectivity View ─────────────────────────────────────


def get_campaign_connectivity(conn) -> dict:
    """Return campaigns with nested child assets + SF linkage status.

    Returns: {
        "summary": { total, with_assets, empty, with_sf_campaign, missing_sf, ... },
        "campaigns": [ { ...campaign, "sf_linked": bool, "children": { forms: [...], ... } } ]
    }
    """
    with get_cursor(conn) as cur:
        has_acts = _has_activities(cur)

        # 1) Fetch all campaigns
        cur.execute("""
            SELECT id, name, cost, salesforce_id, folder_id, created_at, updated_at,
                   sf_created_at, sf_modified_at, start_date, end_date
            FROM campaigns ORDER BY name
        """)
        campaigns = {r["id"]: dict(r) for r in cur.fetchall()}
        for c in campaigns.values():
            c["children"] = {"forms": [], "landing_pages": [], "list_emails": [], "custom_redirects": []}
            c["sf_linked"] = bool(c.get("salesforce_id"))

        # 2) Fetch child assets and attach to parent campaigns
        cur.execute(
            "SELECT id, name, campaign_id, folder_id, embed_code, created_at, updated_at FROM forms ORDER BY name"
        )
        orphan_forms = []
        for r in cur.fetchall():
            row = dict(r)
            if row["campaign_id"] and row["campaign_id"] in campaigns:
                campaigns[row["campaign_id"]]["children"]["forms"].append(row)
            else:
                orphan_forms.append(row)

        cur.execute(
            "SELECT id, name, campaign_id, folder_id, url, created_at, updated_at FROM landing_pages ORDER BY name"
        )
        orphan_lps = []
        for r in cur.fetchall():
            row = dict(r)
            if row["campaign_id"] and row["campaign_id"] in campaigns:
                campaigns[row["campaign_id"]]["children"]["landing_pages"].append(row)
            else:
                orphan_lps.append(row)

        cur.execute(
            "SELECT id, name, campaign_id, subject, folder_id, is_sent, created_at, updated_at FROM list_emails ORDER BY name"
        )
        orphan_emails = []
        for r in cur.fetchall():
            row = dict(r)
            if row["campaign_id"] and row["campaign_id"] in campaigns:
                campaigns[row["campaign_id"]]["children"]["list_emails"].append(row)
            else:
                orphan_emails.append(row)

        cur.execute(
            "SELECT id, name, campaign_id, url, folder_id, created_at, updated_at FROM custom_redirects ORDER BY name"
        )
        orphan_redirects = []
        for r in cur.fetchall():
            row = dict(r)
            if row["campaign_id"] and row["campaign_id"] in campaigns:
                campaigns[row["campaign_id"]]["children"]["custom_redirects"].append(row)
            else:
                orphan_redirects.append(row)

        # 2b) Fetch campaign member counts and attach to campaigns
        member_counts = {}
        try:
            cur.execute(
                "SELECT campaign_sf_id, total_members, responded_members, lead_members, contact_members FROM campaign_member_counts"
            )
            for r in cur.fetchall():
                member_counts[r["campaign_sf_id"]] = dict(r)
        except Exception:
            log.debug("campaign_member_counts table may not exist yet")

        for c in campaigns.values():
            sf_id = c.get("salesforce_id")
            mc = member_counts.get(sf_id) if sf_id else None
            c["member_count"] = mc["total_members"] if mc else 0
            c["responded_count"] = mc["responded_members"] if mc else 0
            c["lead_count"] = mc["lead_members"] if mc else 0
            c["contact_count"] = mc["contact_members"] if mc else 0

        # 3) Compute per-campaign stats
        with_assets = 0
        empty = 0
        with_sf = 0
        missing_sf = 0
        with_members = 0
        without_members = 0
        total_members_all = 0

        for c in campaigns.values():
            ch = c["children"]
            total_children = sum(len(ch[k]) for k in ch)
            c["total_children"] = total_children
            if total_children > 0:
                with_assets += 1
            else:
                empty += 1
            if c["sf_linked"]:
                with_sf += 1
                if c["member_count"] > 0:
                    with_members += 1
                else:
                    without_members += 1
            else:
                missing_sf += 1
            total_members_all += c["member_count"]

        # Sort: campaigns with issues first (no SF link, no assets), then by name
        cam_list = list(campaigns.values())
        cam_list.sort(
            key=lambda c: (
                0 if not c["sf_linked"] else 1,
                0 if c["total_children"] == 0 else 1,
                (c.get("name") or "").lower(),
            )
        )

        summary = {
            "total": len(campaigns),
            "with_assets": with_assets,
            "empty": empty,
            "with_sf_campaign": with_sf,
            "missing_sf_campaign": missing_sf,
            "orphan_forms": len(orphan_forms),
            "orphan_lps": len(orphan_lps),
            "orphan_emails": len(orphan_emails),
            "orphan_redirects": len(orphan_redirects),
            "with_members": with_members,
            "without_members": without_members,
            "total_members": total_members_all,
        }

        # Folder name lookup
        folder_map = {}
        try:
            cur.execute("SELECT id, name FROM folders")
            folder_map = {r["id"]: r["name"] for r in cur.fetchall()}
        except Exception:
            log.debug("folders table may not exist yet")

        return {
            "summary": summary,
            "has_activities": has_acts,
            "campaigns": cam_list,
            "orphans": {
                "forms": orphan_forms,
                "landing_pages": orphan_lps,
                "list_emails": orphan_emails,
                "custom_redirects": orphan_redirects,
            },
            "folder_names": folder_map,
        }


def get_campaign_members(conn, campaign_sf_id: str) -> dict:
    """Return individual CampaignMember rows for a given SF campaign ID.

    Returns: { "members": [...], "summary": { total, responded, leads, contacts } }
    """
    with get_cursor(conn) as cur:
        cur.execute(
            """
            SELECT id, campaign_sf_id, lead_id, contact_id, status,
                   has_responded, created_date, first_responded_date
            FROM campaign_members
            WHERE campaign_sf_id = %s
            ORDER BY created_date DESC
        """,
            (campaign_sf_id,),
        )
        members = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT total_members, responded_members, lead_members, contact_members
            FROM campaign_member_counts
            WHERE campaign_sf_id = %s
        """,
            (campaign_sf_id,),
        )
        counts = cur.fetchone()

    return {
        "members": members,
        "summary": {
            "total": counts["total_members"] if counts else len(members),
            "responded": counts["responded_members"] if counts else sum(1 for m in members if m.get("has_responded")),
            "leads": counts["lead_members"] if counts else sum(1 for m in members if m.get("lead_id")),
            "contacts": counts["contact_members"] if counts else sum(1 for m in members if m.get("contact_id")),
        },
    }


def get_cleanup_status(conn) -> dict:
    """Cross-reference cleanup tags against issue flags to show triage progress.

    Returns configured state, per-action queues, and per-issue progress bars.
    """
    cleanup_cfg = config.get_cleanup_config(conn)
    prefix = cleanup_cfg["prefix"]
    actions = cleanup_cfg["actions"]

    # Object type mapping: Pardot tagged_objects object_type → our DB table
    obj_type_to_table = {
        "form": "forms",
        "landing-page": "landing_pages",
        "Campaign": "campaigns",
        "list": "lists",
        "email": "list_emails",
        "custom-redirect": "custom_redirects",
    }

    # Issue key → (table_name, flag)
    issue_flag_map = {
        "campaigns_empty": ("campaigns", "empty"),
        "campaigns_no_sf": ("campaigns", "no_sf"),
        "campaigns_dormant": ("campaigns", "dormant"),
        "forms_no_campaign": ("forms", "no_campaign"),
        "forms_dormant": ("forms", "dormant"),
        "forms_errors": ("forms", "errors"),
        "lps_no_campaign": ("landing_pages", "no_campaign"),
        "lps_dormant": ("landing_pages", "dormant"),
        "lists_stale_1y": ("lists", "stale_1y"),
        "lists_stale": ("lists", "stale"),
        "lists_unnamed": ("lists", "unnamed"),
        "emails_no_campaign": ("list_emails", "no_campaign"),
        "emails_no_subject": ("list_emails", "no_subject"),
        "redirects_no_campaign": ("custom_redirects", "no_campaign"),
    }

    with get_cursor(conn) as cur:
        # Find cleanup tags matching prefix
        cur.execute("SELECT id, name FROM tags WHERE name ILIKE %s", (prefix + "%",))
        tag_rows = cur.fetchall()

    if not tag_rows:
        return {
            "configured": False,
            "tag_prefix": prefix,
            "actions": {},
            "progress": {},
        }

    # Map action name → tag info
    tag_map = {}  # action_name → {tag_id, tag_name}
    tag_ids = []
    for row in tag_rows:
        action_name = row["name"][len(prefix) :].title()
        tag_map[action_name] = {"tag_id": row["id"], "tag_name": row["name"]}
        tag_ids.append(row["id"])

    # Fetch all tagged objects for these tags
    with get_cursor(conn) as cur:
        cur.execute("SELECT tag_id, object_type, object_id FROM tagged_objects WHERE tag_id = ANY(%s)", (tag_ids,))
        tagged_rows = cur.fetchall()

    # Build tag_id → action lookup
    tag_id_to_action = {v["tag_id"]: k for k, v in tag_map.items()}

    # Group tagged objects by action and object_type
    # Also collect all tagged IDs per table for progress calc
    action_items = defaultdict(list)  # action → [{object_type, object_id, table}]
    tagged_ids_by_table = defaultdict(set)  # table_name → set of object_ids

    for row in tagged_rows:
        action = tag_id_to_action.get(row["tag_id"])
        if not action:
            continue
        obj_type = row["object_type"]
        table = obj_type_to_table.get(obj_type)
        action_items[action].append(
            {
                "object_type": obj_type,
                "object_id": row["object_id"],
                "table": table,
            }
        )
        if table:
            tagged_ids_by_table[table].add(row["object_id"])

    # Enrich action items with asset names
    # Collect IDs needed per table
    ids_by_table = defaultdict(set)
    for items in action_items.values():
        for item in items:
            if item["table"]:
                ids_by_table[item["table"]].add(item["object_id"])

    # Batch-fetch names
    name_lookup = {}  # (table, id) → name
    with get_cursor(conn) as cur:
        for table, ids in ids_by_table.items():
            if not ids:
                continue
            cur.execute(f"SELECT id, name FROM {table} WHERE id = ANY(%s)", (list(ids),))  # noqa: S608
            for r in cur.fetchall():
                name_lookup[(table, r["id"])] = r["name"]

    # Build action response
    actions_resp = {}
    for action_name in actions:
        info = tag_map.get(action_name, {})
        items = action_items.get(action_name, [])
        enriched = []
        for item in items:
            enriched.append(
                {
                    "object_type": item["object_type"],
                    "object_id": item["object_id"],
                    "name": name_lookup.get((item["table"], item["object_id"]), None),
                }
            )
        actions_resp[action_name] = {
            "tag_id": info.get("tag_id"),
            "tag_name": info.get("tag_name"),
            "items": enriched,
            "total": len(enriched),
        }

    # Build per-issue progress
    # Get flagged asset data per type (cached per call)
    detail_cache = {}

    def _get_detail(table):
        if table not in detail_cache:
            detail_cache[table] = get_asset_detail(conn, table)
        return detail_cache[table]

    progress = {}
    for issue_key, (table, flag) in issue_flag_map.items():
        detail = _get_detail(table)
        records = detail.get("records", [])
        flagged_ids = {r["id"] for r in records if flag in r.get("flags", [])}
        total_flagged = len(flagged_ids)
        if total_flagged == 0:
            continue
        tagged_count = len(flagged_ids & tagged_ids_by_table.get(table, set()))
        progress[issue_key] = {
            "total": total_flagged,
            "tagged": tagged_count,
            "pct": round(tagged_count / total_flagged * 100, 1) if total_flagged > 0 else 0,
        }

    return {
        "configured": True,
        "tag_prefix": prefix,
        "actions": actions_resp,
        "progress": progress,
    }


def get_gear_summary(conn) -> dict:
    """Connection chain stats per asset type. Powers the Gear Locker tab hero + chain table.

    Returns per-asset-type counts for: total, in_campaign, in_sf_campaign (campaign has SF link).
    Also returns campaign and list totals.
    """
    with get_cursor(conn) as cur:
        cur.execute("""
            SELECT 'forms' AS t, COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE f.campaign_id IS NOT NULL) AS in_campaign,
                   COUNT(*) FILTER (WHERE f.campaign_id IS NOT NULL
                       AND c.salesforce_id IS NOT NULL AND c.salesforce_id != '') AS in_sf_campaign
            FROM forms f LEFT JOIN campaigns c ON c.id = f.campaign_id
            UNION ALL
            SELECT 'landing_pages', COUNT(*),
                   COUNT(*) FILTER (WHERE lp.campaign_id IS NOT NULL),
                   COUNT(*) FILTER (WHERE lp.campaign_id IS NOT NULL
                       AND c.salesforce_id IS NOT NULL AND c.salesforce_id != '')
            FROM landing_pages lp LEFT JOIN campaigns c ON c.id = lp.campaign_id
            UNION ALL
            SELECT 'list_emails', COUNT(*),
                   COUNT(*) FILTER (WHERE le.campaign_id IS NOT NULL),
                   COUNT(*) FILTER (WHERE le.campaign_id IS NOT NULL
                       AND c.salesforce_id IS NOT NULL AND c.salesforce_id != '')
            FROM list_emails le LEFT JOIN campaigns c ON c.id = le.campaign_id
            UNION ALL
            SELECT 'custom_redirects', COUNT(*),
                   COUNT(*) FILTER (WHERE cr.campaign_id IS NOT NULL),
                   COUNT(*) FILTER (WHERE cr.campaign_id IS NOT NULL
                       AND c.salesforce_id IS NOT NULL AND c.salesforce_id != '')
            FROM custom_redirects cr LEFT JOIN campaigns c ON c.id = cr.campaign_id
        """)
        chain = {}
        total_content = 0
        total_in_campaign = 0
        total_orphaned = 0
        for row in cur.fetchall():
            t = row["t"]
            total = row["total"]
            in_camp = row["in_campaign"]
            orphaned = total - in_camp
            chain[t] = {
                "total": total,
                "in_campaign": in_camp,
                "in_sf_campaign": row["in_sf_campaign"],
                "orphaned": orphaned,
            }
            total_content += total
            total_in_campaign += in_camp
            total_orphaned += orphaned

        cur.execute("""
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE salesforce_id IS NOT NULL AND salesforce_id != '') AS with_sf,
                   COUNT(*) FILTER (WHERE salesforce_id IS NULL OR salesforce_id = '') AS missing_sf
            FROM campaigns
        """)
        camp = dict(cur.fetchone())

        cur.execute("SELECT COUNT(*) AS n FROM lists")
        lists_count = cur.fetchone()["n"]

    return {
        "connection_chain": chain,
        "campaigns": camp,
        "lists_count": lists_count,
        "totals": {
            "content_assets": total_content,
            "in_campaign": total_in_campaign,
            "orphaned": total_orphaned,
        },
    }


def get_prospect_sync_health(conn) -> dict:
    """Categorize prospects by their Pardot<->SF sync status.

    Based on the sync logic:
    - CRM ID linked: has salesforce_id, salesforce_lead_id, or salesforce_contact_id
    - Unlinked: no CRM IDs at all (may still sync via email match if connector configured)
    - Deleted in Pardot: is_deleted = TRUE
    """
    with get_cursor(conn) as cur:
        cur.execute("""
            SELECT
                COUNT(*)                                                         AS total,
                COUNT(*) FILTER (WHERE is_deleted = FALSE
                  AND (salesforce_id        IS NOT NULL AND salesforce_id        != ''
                    OR salesforce_lead_id   IS NOT NULL AND salesforce_lead_id   != ''
                    OR salesforce_contact_id IS NOT NULL AND salesforce_contact_id != '')) AS linked,
                COUNT(*) FILTER (WHERE is_deleted = FALSE
                  AND salesforce_lead_id IS NOT NULL AND salesforce_lead_id != '')         AS linked_lead,
                COUNT(*) FILTER (WHERE is_deleted = FALSE
                  AND salesforce_contact_id IS NOT NULL AND salesforce_contact_id != '')   AS linked_contact,
                COUNT(*) FILTER (WHERE is_deleted = FALSE
                  AND (salesforce_id         IS NULL OR salesforce_id         = '')
                  AND (salesforce_lead_id    IS NULL OR salesforce_lead_id    = '')
                  AND (salesforce_contact_id IS NULL OR salesforce_contact_id = ''))       AS unlinked,
                COUNT(*) FILTER (WHERE is_deleted = TRUE)                                  AS deleted,
                COUNT(*) FILTER (WHERE is_deleted = FALSE
                  AND email IS NOT NULL AND email != '')                                    AS has_email,
                COUNT(*) FILTER (WHERE is_deleted = FALSE AND opted_out = TRUE)            AS opted_out
            FROM prospects
        """)
        row = cur.fetchone()

        total = row["total"]
        linked = row["linked"]
        linked_lead = row["linked_lead"]
        linked_contact = row["linked_contact"]
        unlinked = row["unlinked"]
        deleted = row["deleted"]
        has_email = row["has_email"]
        opted_out = row["opted_out"]
        active = total - deleted

        if total == 0:
            return {}

        return {
            "total": total,
            "active": active,
            "deleted": deleted,
            "linked": linked,
            "linked_as_lead": linked_lead,
            "linked_as_contact": linked_contact,
            "unlinked": unlinked,
            "has_email": has_email,
            "opted_out": opted_out,
            "link_rate": round(linked / active * 100, 1) if active > 0 else 0,
        }
