"""
Centralized configuration — reads from DB with hardcoded fallbacks.
30-second TTL cache so the DB isn't hit on every request.
"""

import logging
import time
from datetime import date

from pardot.db_compat import get_cursor

log = logging.getLogger("config")

# ── Cache ─────────────────────────────────────────────────────────

_cache = {}
_CACHE_TTL = 30  # seconds


def _cached(key, loader):
    """Return cached value or call loader to refresh."""
    now = time.time()
    entry = _cache.get(key)
    if entry and now - entry["t"] < _CACHE_TTL:
        return entry["v"]
    value = loader()
    _cache[key] = {"v": value, "t": now}
    return value


def invalidate_cache():
    """Clear all cached config — call after admin writes."""
    _cache.clear()


# ── Defaults (moved from hardcoded locations) ─────────────────────

DEFAULT_TEAM = [
    {
        "name": "Amanda",
        "role": "Marketing Automation Specialist",
        "owns": ["campaigns", "lists", "forms", "landing_pages", "list_emails", "custom_redirects", "prospects"],
        "label": "Pardot admin — gatekeeps all asset creation, owns system-wide data quality",
    },
    {
        "name": "Lindsay",
        "role": "HE Marketing",
        "owns": ["campaigns", "lists"],
        "label": "Higher Ed campaigns & lists",
    },
    {
        "name": "Liz",
        "role": "K12 Marketing",
        "owns": ["campaigns", "lists"],
        "label": "K-12 campaigns & lists",
    },
    {
        "name": "Devynn",
        "role": "BI Engineer",
        "owns": ["sf_health", "orphans"],
        "label": "Data pipelines, SF sync, orphan resolution",
    },
    {
        "name": "Sarah",
        "role": "Director of Marketing",
        "owns": [],
        "label": "Campaign strategy, overall marketing health",
    },
    {
        "name": "Michael",
        "role": "Director of Data & Analytics",
        "owns": ["survey"],
        "label": "Toolkit owner, data architecture, full survey",
    },
]

DEFAULT_DEMERITS = {
    "campaigns_no_sf": 0.05,
    "campaigns_empty": 0.03,
    "campaigns_dormant": 0.01,
    "campaigns_no_members": 0.04,
    "campaigns_low_response": 0.02,
    "campaigns_ghost": 0.03,
    "forms_no_campaign": 0.10,
    "forms_dormant": 0.02,
    "forms_errors": 0.15,
    "lps_no_campaign": 0.10,
    "lps_dormant": 0.02,
    "lists_stale_1y": 0.05,
    "lists_stale": 0.02,
    "lists_unnamed": 0.08,
    "emails_no_campaign": 0.05,
    "emails_no_subject": 0.08,
    "redirects_no_campaign": 0.03,
    "orphan_forms": 0.10,
    "orphan_lps": 0.10,
    "orphan_emails": 0.05,
    "orphan_redirects": 0.03,
    "prospects_unlinked_pct": 0.30,
    "tags_unused": 0.03,
    "tags_no_convention": 0.02,
}

DEFAULT_ISSUE_TEMPLATES = {
    "campaigns_no_sf": {
        "title": "{count} campaigns have no Salesforce link",
        "description": "These campaigns won't appear in SF reporting. Open each in Pardot and link to the matching SF Campaign.",
        "priority": "high",
    },
    "campaigns_empty": {
        "title": "{count} campaigns have zero connected assets",
        "description": "Campaigns with no forms, landing pages, emails, or redirects. Archive or connect assets to them.",
        "priority": "normal",
    },
    "campaigns_dormant": {
        "title": "{count} campaigns have no activity in 30 days",
        "description": "No visitor activities recorded. Review if these campaigns are still active or should be archived.",
        "priority": "low",
    },
    "campaigns_no_members": {
        "title": "{count} SF-linked campaigns have zero members",
        "description": "These campaigns are linked to Salesforce but have no CampaignMembers — no attribution is being tracked. Add leads/contacts as members or archive the SF Campaign.",
        "priority": "high",
    },
    "campaigns_low_response": {
        "title": "{count} campaigns have a <5% member response rate",
        "description": "These campaigns have members but very few have responded. Review targeting, content, and CTA effectiveness.",
        "priority": "normal",
    },
    "campaigns_ghost": {
        "title": "{count} campaigns have SF members but no Pardot assets",
        "description": "These campaigns have CampaignMembers in Salesforce but zero forms, LPs, emails, or redirects in Pardot. Attribution is one-sided — add assets or review if the campaign is active.",
        "priority": "normal",
    },
    "forms_no_campaign": {
        "title": "{count} forms have no campaign assigned",
        "description": "Forms without a campaign_id won't appear in campaign reporting. Assign each form to a campaign in Pardot.",
        "priority": "high",
    },
    "forms_dormant": {
        "title": "{count} forms have no submissions in 30 days",
        "description": "No form submissions in the last 30 days. Check if these forms are still live and working.",
        "priority": "normal",
    },
    "forms_errors": {
        "title": "{count} forms have submission errors",
        "description": "Form errors mean lost leads. Check the error handler, required fields, and completion actions.",
        "priority": "high",
    },
    "lps_no_campaign": {
        "title": "{count} landing pages have no campaign assigned",
        "description": "Landing pages without a campaign_id won't appear in campaign reporting. Assign each to a campaign in Pardot.",
        "priority": "high",
    },
    "lps_dormant": {
        "title": "{count} landing pages have no views in 30 days",
        "description": "No page views recorded. Check if these pages are still linked and receiving traffic.",
        "priority": "normal",
    },
    "lists_stale_1y": {
        "title": "{count} lists haven't been updated in over a year",
        "description": "Stale lists clutter the system and may contain outdated contacts. Review and archive or delete unused lists.",
        "priority": "high",
    },
    "lists_stale": {
        "title": "{count} lists haven't been updated in 6-12 months",
        "description": "Lists going stale. Check if they're still in use or if they should be refreshed/archived.",
        "priority": "normal",
    },
    "lists_unnamed": {
        "title": "{count} lists have no name",
        "description": "Unnamed lists make the system harder to manage. Name them with a clear, descriptive convention.",
        "priority": "normal",
    },
    "emails_no_campaign": {
        "title": "{count} emails have no campaign assigned",
        "description": "Emails without campaign attribution. Assign each to the appropriate campaign for proper reporting.",
        "priority": "normal",
    },
    "emails_no_subject": {
        "title": "{count} emails have no subject line",
        "description": "Missing subject lines usually indicate draft or broken emails. Review and fix or delete.",
        "priority": "normal",
    },
    "redirects_no_campaign": {
        "title": "{count} custom redirects have no campaign assigned",
        "description": "Redirects without campaign attribution. Assign to the relevant campaign for click tracking.",
        "priority": "low",
    },
    "orphan_forms": {
        "title": "{count} forms are orphaned (not linked to any campaign)",
        "description": "These forms exist but aren't connected to any campaign. They won't show up in campaign reporting.",
        "priority": "high",
    },
    "orphan_lps": {
        "title": "{count} landing pages are orphaned",
        "description": "Landing pages with no campaign connection. Assign them or archive if unused.",
        "priority": "high",
    },
    "orphan_emails": {
        "title": "{count} emails are orphaned (no campaign connection)",
        "description": "Emails floating without campaign attribution. Link them to the right campaign.",
        "priority": "normal",
    },
    "orphan_redirects": {
        "title": "{count} custom redirects are orphaned",
        "description": "Redirects without campaign connection. Low impact but worth cleaning up.",
        "priority": "low",
    },
    "prospects_unlinked_pct": {
        "title": "{count}% of prospects have no CRM link",
        "description": "These prospects aren't syncing to Salesforce. Check connector settings and assignment rules.",
        "priority": "high",
    },
    "tags_unused": {
        "title": "{count} tags are unused (zero objects attached)",
        "description": "Unused tags clutter the system. Review and delete tags that are no longer needed.",
        "priority": "low",
    },
    "tags_no_convention": {
        "title": "{count} tags don't follow a naming convention",
        "description": "Tags without a consistent naming pattern (e.g., 'Region: East', 'FY25 - Q1') are harder to manage. Standardize tag names.",
        "priority": "low",
    },
}

DEFAULT_GRADE_THRESHOLDS = [(90, "A"), (80, "B"), (70, "C"), (60, "D"), (0, "F")]

DEFAULT_CAMP_START = "2026-03-01"
DEFAULT_CAMP_END = "2026-03-31"

DEFAULT_CLEANUP_TAG_PREFIX = "Camp: "
DEFAULT_CLEANUP_ACTIONS = ["Remove", "Archive", "Reviewed"]

DEFAULT_ACTIVITY_LOOKBACK_DAYS = 30
DEFAULT_LIST_STALE_MONTHS = 6
DEFAULT_LIST_STALE_SEVERE_MONTHS = 12


# ── Config readers ────────────────────────────────────────────────


def _get_config_value(conn, key):
    """Read a single config key from DB. Returns None if not set."""
    with get_cursor(conn) as cur:
        cur.execute("SELECT value FROM config WHERE key = %s", (key,))
        row = cur.fetchone()
        return row["value"] if row else None


def get_team(conn) -> list:
    """Team roster from team_members table, falling back to DEFAULT_TEAM."""

    def _load():
        try:
            with get_cursor(conn) as cur:
                cur.execute("""
                    SELECT name, role, owns, label
                    FROM team_members
                    ORDER BY sort_order, name
                """)
                rows = cur.fetchall()
                if rows:
                    return [dict(r) for r in rows]
        except Exception:
            pass
        return list(DEFAULT_TEAM)

    return _cached("team", _load)


def get_demerits(conn) -> dict:
    """Demerit weights from config table, falling back to DEFAULT_DEMERITS."""

    def _load():
        val = _get_config_value(conn, "demerits")
        if val and isinstance(val, dict):
            merged = dict(DEFAULT_DEMERITS)
            merged.update(val)
            return merged
        return dict(DEFAULT_DEMERITS)

    return _cached("demerits", _load)


def get_issue_templates(conn) -> dict:
    """Issue templates from config table, falling back to DEFAULT_ISSUE_TEMPLATES."""

    def _load():
        val = _get_config_value(conn, "issue_templates")
        if val and isinstance(val, dict):
            merged = {}
            for key in DEFAULT_ISSUE_TEMPLATES:
                merged[key] = dict(DEFAULT_ISSUE_TEMPLATES[key])
                if key in val:
                    merged[key].update(val[key])
            return merged
        return dict(DEFAULT_ISSUE_TEMPLATES)

    return _cached("issue_templates", _load)


def get_grade_map(conn) -> list:
    """Grade thresholds from config table, falling back to DEFAULT_GRADE_THRESHOLDS.

    Returns list of (threshold, letter) tuples sorted descending by threshold.
    """

    def _load():
        val = _get_config_value(conn, "grade_thresholds")
        if val and isinstance(val, list):
            try:
                result = [(int(item[0]), str(item[1])) for item in val]
                result.sort(key=lambda x: -x[0])
                return result
            except (IndexError, ValueError, TypeError):
                pass
        return list(DEFAULT_GRADE_THRESHOLDS)

    return _cached("grade_map", _load)


def get_camp_dates(conn) -> tuple:
    """Camp start and end dates. Returns (start_date, end_date)."""

    def _load():
        start_str = _get_config_value(conn, "camp_start")
        end_str = _get_config_value(conn, "camp_end")
        try:
            start = date.fromisoformat(start_str) if start_str else date.fromisoformat(DEFAULT_CAMP_START)
        except (ValueError, TypeError):
            start = date.fromisoformat(DEFAULT_CAMP_START)
        try:
            end = date.fromisoformat(end_str) if end_str else date.fromisoformat(DEFAULT_CAMP_END)
        except (ValueError, TypeError):
            end = date.fromisoformat(DEFAULT_CAMP_END)
        return (start, end)

    return _cached("camp_dates", _load)


def get_activity_lookback_days(conn) -> int:
    """Activity lookback window in days."""

    def _load():
        val = _get_config_value(conn, "activity_lookback_days")
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass
        return DEFAULT_ACTIVITY_LOOKBACK_DAYS

    return _cached("activity_lookback_days", _load)


def get_cleanup_config(conn) -> dict:
    """Cleanup tag prefix and actions. Returns {"prefix": str, "actions": list}."""

    def _load():
        prefix = _get_config_value(conn, "cleanup_tag_prefix")
        if not isinstance(prefix, str) or not prefix:
            prefix = DEFAULT_CLEANUP_TAG_PREFIX
        actions = _get_config_value(conn, "cleanup_actions")
        if not isinstance(actions, list) or not actions:
            actions = list(DEFAULT_CLEANUP_ACTIONS)
        return {"prefix": prefix, "actions": actions}

    return _cached("cleanup_config", _load)


def get_list_stale_thresholds(conn) -> tuple:
    """List staleness thresholds. Returns (stale_months, severe_months)."""

    def _load():
        stale = _get_config_value(conn, "list_stale_months")
        severe = _get_config_value(conn, "list_stale_severe_months")
        try:
            stale_val = int(stale) if stale is not None else DEFAULT_LIST_STALE_MONTHS
        except (ValueError, TypeError):
            stale_val = DEFAULT_LIST_STALE_MONTHS
        try:
            severe_val = int(severe) if severe is not None else DEFAULT_LIST_STALE_SEVERE_MONTHS
        except (ValueError, TypeError):
            severe_val = DEFAULT_LIST_STALE_SEVERE_MONTHS
        return (stale_val, severe_val)

    return _cached("list_stale_thresholds", _load)


# ── Convenience: all config as a dict (for admin API) ─────────────


def get_all_config(conn) -> dict:
    """Return all config values merged with defaults — for the admin UI."""
    return {
        "demerits": get_demerits(conn),
        "issue_templates": get_issue_templates(conn),
        "grade_thresholds": get_grade_map(conn),
        "camp_start": get_camp_dates(conn)[0].isoformat(),
        "camp_end": get_camp_dates(conn)[1].isoformat(),
        "activity_lookback_days": get_activity_lookback_days(conn),
        "list_stale_months": get_list_stale_thresholds(conn)[0],
        "list_stale_severe_months": get_list_stale_thresholds(conn)[1],
        "cleanup_tag_prefix": get_cleanup_config(conn)["prefix"],
        "cleanup_actions": get_cleanup_config(conn)["actions"],
    }
