"""
Accountability Scorecard — health score (0-100) and prioritized issue generation.
Calls existing audit functions from assets.py — no new SQL queries.
"""

import logging
import math
import time

from pardot import config
from pardot.assets import get_asset_detail, get_campaign_connectivity, get_prospect_sync_health, get_tag_review
from pardot.db_compat import get_cursor

log = logging.getLogger("scorecard")

# Which area each issue belongs to (structural mapping, not tunable)
ISSUE_AREA = {
    "campaigns_no_sf": "campaigns",
    "campaigns_empty": "campaigns",
    "campaigns_dormant": "campaigns",
    "campaigns_no_members": "campaigns",
    "campaigns_low_response": "campaigns",
    "campaigns_ghost": "campaigns",
    "forms_no_campaign": "forms",
    "forms_dormant": "forms",
    "forms_errors": "forms",
    "lps_no_campaign": "landing_pages",
    "lps_dormant": "landing_pages",
    "lists_stale_1y": "lists",
    "lists_stale": "lists",
    "lists_unnamed": "lists",
    "emails_no_campaign": "list_emails",
    "emails_no_subject": "list_emails",
    "redirects_no_campaign": "custom_redirects",
    "orphan_forms": "forms",
    "orphan_lps": "landing_pages",
    "orphan_emails": "list_emails",
    "orphan_redirects": "custom_redirects",
    "prospects_unlinked_pct": "prospects",
    "tags_unused": "tags",
    "tags_no_convention": "tags",
}


def _grade(score, grade_map):
    for threshold, letter in grade_map:
        if score >= threshold:
            return letter
    return "F"


_issue_counts_cache: dict | None = None
_issue_counts_ts: float = 0.0
_ISSUE_COUNTS_TTL = 30  # seconds — shared across /api/briefing, /api/health-score, /api/issues


def _collect_issue_counts(conn) -> dict:
    """Gather all issue counts from existing audit functions.

    Results are cached in-process for _ISSUE_COUNTS_TTL seconds so that
    /api/briefing, /api/health-score, and /api/issues fired in rapid succession
    on page load don't each independently run the full ~50-query pipeline.
    """
    global _issue_counts_cache, _issue_counts_ts
    if _issue_counts_cache is not None and time.monotonic() - _issue_counts_ts < _ISSUE_COUNTS_TTL:
        return _issue_counts_cache

    counts = {}

    # Campaigns
    try:
        cam = get_asset_detail(conn, "campaigns")
        s = cam.get("summary", {})
        counts["campaigns_no_sf"] = s.get("no_sf", 0)
        counts["campaigns_empty"] = s.get("empty", 0)
        counts["campaigns_dormant"] = s.get("dormant", 0)
    except Exception as e:
        log.warning(f"Scorecard: campaign audit failed: {e}")

    # Forms
    try:
        frm = get_asset_detail(conn, "forms")
        s = frm.get("summary", {})
        counts["forms_no_campaign"] = s.get("no_campaign", 0)
        counts["forms_dormant"] = s.get("dormant", 0)
        counts["forms_errors"] = s.get("with_errors", 0)
    except Exception as e:
        log.warning(f"Scorecard: forms audit failed: {e}")

    # Landing pages
    try:
        lps = get_asset_detail(conn, "landing_pages")
        s = lps.get("summary", {})
        counts["lps_no_campaign"] = s.get("no_campaign", 0)
        counts["lps_dormant"] = s.get("dormant", 0)
    except Exception as e:
        log.warning(f"Scorecard: landing pages audit failed: {e}")

    # Lists
    try:
        lst = get_asset_detail(conn, "lists")
        s = lst.get("summary", {})
        counts["lists_stale_1y"] = s.get("stale_1y", 0)
        counts["lists_stale"] = s.get("stale_6m", 0)
        counts["lists_unnamed"] = 0
        # Count unnamed from records
        for r in lst.get("records", []):
            if "unnamed" in (r.get("flags") or []):
                counts["lists_unnamed"] += 1
    except Exception as e:
        log.warning(f"Scorecard: lists audit failed: {e}")

    # Emails
    try:
        emails = get_asset_detail(conn, "list_emails")
        s = emails.get("summary", {})
        counts["emails_no_campaign"] = s.get("no_campaign", 0)
        counts["emails_no_subject"] = s.get("no_subject", 0)
    except Exception as e:
        log.warning(f"Scorecard: emails audit failed: {e}")

    # Redirects
    try:
        redir = get_asset_detail(conn, "custom_redirects")
        s = redir.get("summary", {})
        counts["redirects_no_campaign"] = s.get("no_campaign", 0)
    except Exception as e:
        log.warning(f"Scorecard: redirects audit failed: {e}")

    # Campaign members
    try:
        with get_cursor(conn) as cur:
            # SF-linked campaigns with zero members
            cur.execute("""
                SELECT COUNT(*) AS n FROM campaigns c
                WHERE c.salesforce_id IS NOT NULL AND c.salesforce_id != ''
                  AND NOT EXISTS (
                    SELECT 1 FROM campaign_member_counts cmc
                    WHERE cmc.campaign_sf_id = c.salesforce_id AND cmc.total_members > 0
                  )
            """)
            counts["campaigns_no_members"] = cur.fetchone()["n"]

            # SF-linked campaigns with members but <5% response rate
            cur.execute("""
                SELECT COUNT(*) AS n FROM campaign_member_counts
                WHERE total_members >= 10
                  AND responded_members * 100.0 / total_members < 5
            """)
            counts["campaigns_low_response"] = cur.fetchone()["n"]

            # Ghost campaigns: have SF members but zero Pardot assets
            cur.execute("""
                SELECT COUNT(*) AS n FROM campaigns c
                WHERE c.salesforce_id IS NOT NULL AND c.salesforce_id != ''
                  AND EXISTS (
                    SELECT 1 FROM campaign_member_counts cmc
                    WHERE cmc.campaign_sf_id = c.salesforce_id AND cmc.total_members > 0
                  )
                  AND NOT EXISTS (SELECT 1 FROM forms WHERE campaign_id = c.id)
                  AND NOT EXISTS (SELECT 1 FROM landing_pages WHERE campaign_id = c.id)
                  AND NOT EXISTS (SELECT 1 FROM list_emails WHERE campaign_id = c.id)
                  AND NOT EXISTS (SELECT 1 FROM custom_redirects WHERE campaign_id = c.id)
            """)
            counts["campaigns_ghost"] = cur.fetchone()["n"]
    except Exception as e:
        log.warning(f"Scorecard: campaign members audit failed: {e}")

    # Campaign connectivity orphans
    try:
        cc = get_campaign_connectivity(conn)
        s = cc.get("summary", {})
        counts["orphan_forms"] = s.get("orphan_forms", 0)
        counts["orphan_lps"] = s.get("orphan_lps", 0)
        counts["orphan_emails"] = s.get("orphan_emails", 0)
        counts["orphan_redirects"] = s.get("orphan_redirects", 0)
    except Exception as e:
        log.warning(f"Scorecard: connectivity audit failed: {e}")

    # Prospect sync health
    try:
        ph = get_prospect_sync_health(conn)
        if ph and ph.get("active", 0) > 0:
            counts["prospects_unlinked_pct"] = round(100 - ph.get("link_rate", 100))
        else:
            counts["prospects_unlinked_pct"] = 0
    except Exception as e:
        log.warning(f"Scorecard: prospect health failed: {e}")

    # Tags
    try:
        tr = get_tag_review(conn)
        s = tr.get("summary", {})
        counts["tags_unused"] = s.get("unused", 0)
        counts["tags_no_convention"] = s.get("no_naming_convention", 0)
    except Exception as e:
        log.warning(f"Scorecard: tag review failed: {e}")

    _issue_counts_cache = counts
    _issue_counts_ts = time.monotonic()
    return counts


def compute_health_score(conn) -> dict:
    """Compute overall health score (0-100) with per-area and per-person breakdowns.

    Returns: {
        "overall": {"score": int, "grade": str, "demerits": float},
        "by_area": {"campaigns": {"score": ..., "grade": ...}, ...},
        "by_person": {"Amanda": {"score": ..., "grade": ..., "areas": [...]}, ...},
        "issue_counts": {...},
    }
    """
    counts = _collect_issue_counts(conn)
    demerits = config.get_demerits(conn)
    grade_map = config.get_grade_map(conn)
    team = config.get_team(conn)

    # Per-area scores (compute first, then derive overall as average)
    areas = {}
    area_keys = {}  # group issue keys by area
    for key, area in ISSUE_AREA.items():
        area_keys.setdefault(area, []).append(key)

    for area, keys in area_keys.items():
        area_demerits = sum(counts.get(k, 0) * demerits.get(k, 0) for k in keys)
        area_score = max(0, min(100, round(100 - area_demerits)))
        areas[area] = {"score": area_score, "grade": _grade(area_score, grade_map), "demerits": round(area_demerits, 1)}

    # Get asset counts per area for weighting — areas with more items matter more
    area_table = {
        "campaigns": "campaigns",
        "lists": "lists",
        "forms": "forms",
        "landing_pages": "landing_pages",
        "list_emails": "list_emails",
        "custom_redirects": "custom_redirects",
        "prospects": "prospects",
        "tags": "tags",
    }
    area_weights = {}
    with get_cursor(conn) as cur:
        for area, table in area_table.items():
            try:
                cur.execute(f"SELECT COUNT(*) AS n FROM {table}")  # noqa: S608
                n = cur.fetchone()["n"]
            except Exception:
                n = 0
            # log scale so 500k prospects doesn't swamp everything,
            # but 1300 campaigns still weighs ~3x more than 50 redirects
            area_weights[area] = math.log(max(n, 1) + 1)

    # Overall score = asset-weighted average of area scores
    total_demerits = sum(a["demerits"] for a in areas.values())
    if areas:
        total_w = sum(area_weights.get(a, 1) for a in areas)
        score = round(sum(areas[a]["score"] * area_weights.get(a, 1) for a in areas) / total_w)
    else:
        score = 100
    score = max(0, min(100, score))
    grade = _grade(score, grade_map)

    # Per-person scores = weighted average of their owned area scores
    ownership = {}
    for member in team:
        if member.get("owns"):
            ownership[member["name"]] = member["owns"]

    by_person = {}
    for person, owned_areas in ownership.items():
        person_areas = [(areas[a]["score"], area_weights.get(a, 1)) for a in owned_areas if a in areas]
        if person_areas:
            pw = sum(w for _, w in person_areas)
            person_score = round(sum(s * w for s, w in person_areas) / pw)
        else:
            person_score = 100
        person_score = max(0, min(100, person_score))
        by_person[person] = {
            "score": person_score,
            "grade": _grade(person_score, grade_map),
            "areas": owned_areas,
        }

    # Per-area contribution to overall score loss
    # points_lost = how much this area pulls overall score below 100
    total_w = sum(area_weights.get(a, 1) for a in areas) if areas else 1
    for area_key, area_data in areas.items():
        w = area_weights.get(area_key, 1)
        area_data["weight"] = round(w, 2)
        area_data["points_lost"] = round((100 - area_data["score"]) * w / total_w, 1)

    return {
        "overall": {"score": score, "grade": grade, "demerits": round(total_demerits, 1)},
        "by_area": areas,
        "by_person": by_person,
        "issue_counts": counts,
    }


def generate_issues(conn, team=None) -> list:
    """Generate prioritized action items with owners and score impact.

    Returns sorted list of {key, title, description, area, priority, count, owners, score_impact}.
    score_impact = how many overall score points would improve if this issue were fully fixed.
    """
    hs = compute_health_score(conn)
    counts = hs["issue_counts"]
    demerits_cfg = config.get_demerits(conn)
    issue_templates = config.get_issue_templates(conn)

    # Build owner lookup from team
    if team is None:
        team = config.get_team(conn)
    area_owners = {}
    for member in team:
        for area in member.get("owns", []):
            area_owners.setdefault(area, []).append(member["name"])

    # Precompute total weight for score impact calculation
    by_area = hs.get("by_area", {})
    total_w = sum(a.get("weight", 1) for a in by_area.values()) if by_area else 1

    issues = []

    for key, template in issue_templates.items():
        count = counts.get(key, 0)
        if count == 0:
            continue

        area = ISSUE_AREA.get(key, "")
        owners = area_owners.get(area, [])

        # Score impact: if this issue were fully fixed, how much would the
        # area score improve, and what's the weighted effect on overall?
        area_data = by_area.get(area, {})
        w = area_data.get("weight", 1)
        issue_demerits = count * demerits_cfg.get(key, 0)
        # Area score would go up by issue_demerits (capped so area doesn't exceed 100)
        area_gain = min(issue_demerits, 100 - area_data.get("score", 100))
        score_impact = round(area_gain * w / total_w, 1)

        issues.append(
            {
                "key": key,
                "title": template["title"].format(count=count),
                "description": template["description"],
                "area": area,
                "priority": template["priority"],
                "count": count,
                "owners": owners,
                "score_impact": score_impact,
            }
        )

    # Sort by score impact descending (most impactful first)
    issues.sort(key=lambda i: -i["score_impact"])

    return issues
