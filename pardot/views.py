"""
Camp Campaign API views — django-ninja router.
All endpoints require SuperUser auth (SSO + is_super_user check).
"""

import json
import logging
from datetime import date

from django.http import HttpResponse, JsonResponse
from ninja import Router

from api.auth import combined_auth
from api.models import SuperUser
from pardot import config
from pardot.assets import (
    get_asset_detail,
    get_asset_overview,
    get_asset_summary,
    get_campaign_connectivity,
    get_campaign_members,
    get_cleanup_status,
    get_gear_summary,
    get_prospect_sync_health,
    get_tag_review,
)
from pardot.db_compat import get_cursor
from pardot.digest import generate_digest, generate_progress_report
from pardot.engagement import (
    get_adoption_json_alert,
    get_crm_id_alerts,
    get_engagement_summary,
    get_prospect_activities,
    get_scoring_categories,
    get_top_engaged,
)
from pardot.pardot_client import _get_sf_instance_url as _sf_instance_url
from pardot.scorecard import compute_health_score, generate_issues
from pardot.sync import SyncEngine

log = logging.getLogger("camp.views")

router = Router(tags=["camp"])


def _is_super_user(request):
    """Check if the authenticated user is a SuperUser."""
    uuid = getattr(request, "auth_uuid", None)
    return SuperUser.is_super_user(uuid)


def _require_super(request):
    """Return error response if not a super user, else None."""
    if not _is_super_user(request):
        return JsonResponse({"error": "Forbidden — SuperUser access required"}, status=403)
    return None


def _conn():
    """Compatibility shim — returns None since Django manages connections."""
    return None


def _camp_day(camp_start=None, camp_end=None):
    today = date.today()
    if camp_start is None or camp_end is None:
        camp_start, camp_end = config.get_camp_dates(None)
    if today < camp_start:
        return 0
    elif today > camp_end:
        return (camp_end - camp_start).days + 1
    return (today - camp_start).days + 1


def _detect_tier() -> int:
    with get_cursor() as cur:
        cur.execute("SELECT last_sync_mode FROM sync_meta WHERE entity_type = 'visitor_activities'")
        if cur.fetchone():
            return 3
        cur.execute("SELECT last_sync_mode FROM sync_meta WHERE entity_type = 'prospects'")
        if cur.fetchone():
            return 2
        cur.execute("SELECT COUNT(*) AS n FROM sync_meta")
        row = cur.fetchone()
        if row and row["n"] > 0:
            return 1
    return 0


# ── Briefing ──


@router.get("/briefing", auth=combined_auth)
def api_briefing(request):
    denied = _require_super(request)
    if denied:
        return denied

    conn = _conn()
    tier = _detect_tier()
    camp_start, camp_end = config.get_camp_dates(conn)
    camp_days = (camp_end - camp_start).days + 1

    with get_cursor() as cur:
        cur.execute("SELECT * FROM sf_health ORDER BY captured_at DESC LIMIT 1")
        sf = cur.fetchone()

        cur.execute("""
            SELECT * FROM daily_snapshots
            WHERE snapshot_date < CURRENT_DATE
            ORDER BY snapshot_date DESC LIMIT 1
        """)
        yesterday = cur.fetchone()

        cur.execute("""
            SELECT * FROM daily_snapshots
            WHERE snapshot_date <= CURRENT_DATE - INTERVAL '6 days'
            ORDER BY snapshot_date DESC LIMIT 1
        """)
        last_week = cur.fetchone()

    sf_health = None
    if sf:
        linked = sf["leads_with_pardot"] + sf["contacts_with_pardot"]
        total_sf = sf["total_leads"] + sf["total_contacts"]
        sf_health = {
            "total_leads": sf["total_leads"],
            "total_contacts": sf["total_contacts"],
            "leads_with_pardot": sf["leads_with_pardot"],
            "contacts_with_pardot": sf["contacts_with_pardot"],
            "total_sf": total_sf,
            "total_linked": linked,
            "coverage_pct": round(linked / total_sf * 100, 1) if total_sf > 0 else 0,
            "captured_at": sf["captured_at"].isoformat() if sf["captured_at"] else None,
        }

    hs = None
    try:
        hs = compute_health_score(conn)
    except Exception:
        log.debug("Health score computation failed")

    return {
        "date": date.today().isoformat(),
        "camp_day": _camp_day(camp_start=camp_start, camp_end=camp_end),
        "camp_days_total": camp_days,
        "tier": tier,
        "sf_health": sf_health,
        "assets": get_asset_summary(conn),
        "yesterday": dict(yesterday) if yesterday else None,
        "last_week": dict(last_week) if last_week else None,
        "health_score": hs,
    }


# ── SF Health ──


@router.get("/sf-health", auth=combined_auth)
def api_sf_health(request):
    denied = _require_super(request)
    if denied:
        return denied
    with get_cursor() as cur:
        cur.execute("SELECT * FROM sf_health ORDER BY captured_at DESC LIMIT 1")
        row = cur.fetchone()
    return dict(row) if row else {}


# ── Engagement ──


@router.get("/engagement", auth=combined_auth)
def api_engagement(request, limit: int = 50):
    denied = _require_super(request)
    if denied:
        return denied
    conn = _conn()
    tier = _detect_tier()
    prospects = get_top_engaged(conn, limit=limit) if tier >= 2 else []
    if prospects:
        pids = [p["id"] for p in prospects]
        cats = get_scoring_categories(conn, pids)
        for p in prospects:
            p["scoring_categories"] = cats.get(p["id"], {})
    alerts = (
        get_crm_id_alerts(conn)
        if tier >= 2
        else {"bad_lead_ids": [], "bad_contact_ids": [], "total_bad": 0, "summary": {}}
    )
    adoption = get_adoption_json_alert(conn) if tier >= 2 else {"stuck_count": 0}
    summary = get_engagement_summary(conn) if tier >= 2 else {}
    return {
        "tier": tier,
        "prospects": prospects,
        "crm_id_alerts": alerts,
        "adoption_json_alert": adoption,
        "summary": summary,
    }


@router.get("/engagement/{prospect_id}/activities", auth=combined_auth)
def api_engagement_activities(request, prospect_id: int):
    denied = _require_super(request)
    if denied:
        return denied
    return get_prospect_activities(_conn(), prospect_id)


# ── Assets ──


@router.get("/assets", auth=combined_auth)
def api_assets(request):
    denied = _require_super(request)
    if denied:
        return denied
    return get_asset_overview(_conn())


@router.get("/asset-health", auth=combined_auth)
def api_asset_health(request):
    denied = _require_super(request)
    if denied:
        return denied
    conn = _conn()
    result = {}
    for t in ["campaigns", "lists", "forms", "landing_pages", "list_emails", "custom_redirects"]:
        detail = get_asset_detail(conn, t)
        result[t] = detail.get("summary", {})
    return result


@router.get("/assets/{asset_type}", auth=combined_auth)
def api_asset_detail(request, asset_type: str):
    denied = _require_super(request)
    if denied:
        return denied
    return get_asset_detail(_conn(), asset_type)


@router.get("/gear-summary", auth=combined_auth)
def api_gear_summary(request):
    denied = _require_super(request)
    if denied:
        return denied
    return get_gear_summary(_conn())


# ── Campaigns ──


@router.get("/campaigns", auth=combined_auth)
def api_campaigns(request):
    denied = _require_super(request)
    if denied:
        return denied
    return get_campaign_connectivity(_conn())


@router.get("/campaigns/{sf_id}/members", auth=combined_auth)
def api_campaign_members(request, sf_id: str):
    denied = _require_super(request)
    if denied:
        return denied
    return get_campaign_members(_conn(), sf_id)


# ── Tags ──


@router.get("/tags", auth=combined_auth)
def api_tags(request):
    denied = _require_super(request)
    if denied:
        return denied
    return get_tag_review(_conn())


# ── Prospect Health ──


@router.get("/prospect-health", auth=combined_auth)
def api_prospect_health(request):
    denied = _require_super(request)
    if denied:
        return denied
    return get_prospect_sync_health(_conn())


# ── Orphans ──


@router.get("/orphans", auth=combined_auth)
def api_orphans(request):
    denied = _require_super(request)
    if denied:
        return denied
    tier = _detect_tier()
    with get_cursor() as cur:
        cur.execute("SELECT * FROM orphan_runs ORDER BY run_at DESC LIMIT 1")
        row = cur.fetchone()
    return {"tier": tier, "run": dict(row) if row else None}


@router.get("/orphans/history", auth=combined_auth)
def api_orphans_history(request):
    denied = _require_super(request)
    if denied:
        return denied
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, run_at, pardot_missing_crm, sf_missing_pardot, unlinked_prospects
            FROM orphan_runs ORDER BY run_at ASC LIMIT 100
        """)
        return [dict(r) for r in cur.fetchall()]


# ── Trail ──


@router.get("/trail", auth=combined_auth)
def api_trail(request):
    denied = _require_super(request)
    if denied:
        return denied
    with get_cursor() as cur:
        cur.execute("SELECT * FROM daily_snapshots ORDER BY snapshot_date ASC")
        return [dict(r) for r in cur.fetchall()]


# ── Digest ──


@router.get("/digest", auth=combined_auth)
def api_digest(request):
    denied = _require_super(request)
    if denied:
        return denied
    conn = _conn()
    team = config.get_team(conn)
    text = generate_digest(conn, team=team)
    return HttpResponse(text, content_type="text/plain")


@router.get("/progress", auth=combined_auth)
def api_progress(request):
    denied = _require_super(request)
    if denied:
        return denied
    text = generate_progress_report(_conn())
    return HttpResponse(text, content_type="text/plain")


# ── Sync Status ──


@router.get("/sync/status", auth=combined_auth)
def api_sync_status(request):
    denied = _require_super(request)
    if denied:
        return denied
    return SyncEngine.get_sync_status(_conn())


# ── Tasks ──


@router.get("/tasks", auth=combined_auth)
def api_tasks(request, assignee: str = None, status: str = None):
    denied = _require_super(request)
    if denied:
        return denied
    with get_cursor() as cur:
        sql = "SELECT * FROM tasks WHERE 1=1"
        params = []
        if assignee:
            sql += " AND assignee = %s"
            params.append(assignee)
        if status:
            sql += " AND status = %s"
            params.append(status)
        sql += " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 WHEN 'low' THEN 2 END, created_at DESC"
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


@router.post("/tasks", auth=combined_auth)
def api_tasks_create(request):
    denied = _require_super(request)
    if denied:
        return denied
    data = json.loads(request.body)
    if not data.get("assignee") or not data.get("title"):
        return JsonResponse({"error": "assignee and title are required"}, status=400)
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO tasks (assignee, title, description, area, asset_type, asset_id, asset_name, priority, created_by, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING *
        """,
            (
                data["assignee"],
                data["title"],
                data.get("description"),
                data.get("area"),
                data.get("asset_type"),
                data.get("asset_id"),
                data.get("asset_name"),
                data.get("priority", "normal"),
                data.get("created_by"),
            ),
        )
        return cur.fetchone()


@router.patch("/tasks/{task_id}", auth=combined_auth)
def api_tasks_update(request, task_id: int):
    denied = _require_super(request)
    if denied:
        return denied
    data = json.loads(request.body)
    allowed = {"status", "priority", "title", "description", "assignee", "area", "asset_type", "asset_id", "asset_name"}
    sets = []
    params = []
    for key in allowed:
        if key in data:
            sets.append(f"{key} = %s")
            params.append(data[key])
    if not sets:
        return JsonResponse({"error": "no valid fields to update"}, status=400)
    sets.append("updated_at = NOW()")
    if data.get("status") == "done":
        sets.append("completed_at = NOW()")
    params.append(task_id)
    with get_cursor() as cur:
        cur.execute(f"UPDATE tasks SET {', '.join(sets)} WHERE id = %s RETURNING *", params)  # noqa: S608
        row = cur.fetchone()
    if not row:
        return JsonResponse({"error": "task not found"}, status=404)
    return row


@router.delete("/tasks/{task_id}", auth=combined_auth)
def api_tasks_delete(request, task_id: int):
    denied = _require_super(request)
    if denied:
        return denied
    with get_cursor() as cur:
        cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    return {"ok": True}


# ── Health Score & Issues ──


@router.get("/health-score", auth=combined_auth)
def api_health_score(request):
    denied = _require_super(request)
    if denied:
        return denied
    return compute_health_score(_conn())


@router.get("/issues", auth=combined_auth)
def api_issues(request):
    denied = _require_super(request)
    if denied:
        return denied
    conn = _conn()
    team = config.get_team(conn)
    return generate_issues(conn, team=team)


@router.post("/issues/{key}/create-task", auth=combined_auth)
def api_issue_create_task(request, key: str):
    denied = _require_super(request)
    if denied:
        return denied
    conn = _conn()
    team = config.get_team(conn)
    issues = generate_issues(conn, team=team)
    issue = next((i for i in issues if i["key"] == key), None)
    if not issue:
        return JsonResponse({"error": "issue not found or count is zero"}, status=404)
    assignee = issue["owners"][0] if issue["owners"] else "Unassigned"
    try:
        data = json.loads(request.body)
        assignee = data.get("assignee", assignee)
    except Exception:
        log.debug("Could not parse request body for assignee")
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO tasks (assignee, title, description, area, priority, created_by, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING *
        """,
            (assignee, issue["title"], issue["description"], issue["area"], issue["priority"], "scorecard"),
        )
        return cur.fetchone()


# ── Config ──


@router.get("/config", auth=combined_auth)
def api_config(request):
    denied = _require_super(request)
    if denied:
        return denied
    conn = _conn()
    team = config.get_team(conn)
    return {
        "sf_instance_url": _sf_instance_url(),
        "team": team,
    }


# ── Cleanup ──


@router.get("/cleanup/status", auth=combined_auth)
def api_cleanup_status(request):
    denied = _require_super(request)
    if denied:
        return denied
    return get_cleanup_status(_conn())


@router.post("/cleanup/setup", auth=combined_auth)
def api_cleanup_setup(request):
    denied = _require_super(request)
    if denied:
        return denied
    conn = _conn()
    cleanup_cfg = config.get_cleanup_config(conn)
    prefix = cleanup_cfg["prefix"]
    actions = cleanup_cfg["actions"]

    with get_cursor() as cur:
        cur.execute("SELECT name FROM tags WHERE name ILIKE %s", (prefix + "%",))
        existing = {r["name"].lower() for r in cur.fetchall()}

    from pardot.pardot_client import PardotClient

    pardot = PardotClient()
    created = []
    skipped = []
    for action in actions:
        tag_name = f"{prefix}{action}"
        if tag_name.lower() in existing:
            skipped.append(tag_name)
            continue
        pardot.create_tag(tag_name)
        created.append(tag_name)

    engine = SyncEngine(pardot, conn)
    engine.sync_tags()
    return {"created": created, "skipped": skipped}


# ── Admin Config API ──


@router.get("/admin/team", auth=combined_auth)
def api_admin_team_get(request):
    denied = _require_super(request)
    if denied:
        return denied
    return config.get_team(_conn())


@router.put("/admin/team", auth=combined_auth)
def api_admin_team_put(request):
    denied = _require_super(request)
    if denied:
        return denied
    data = json.loads(request.body)
    if not isinstance(data, list):
        return JsonResponse({"error": "expected a JSON array of team members"}, status=400)
    with get_cursor() as cur:
        cur.execute("DELETE FROM team_members")
        for i, member in enumerate(data):
            name = member.get("name", "").strip()
            if not name:
                continue
            cur.execute(
                """
                INSERT INTO team_members (name, role, owns, label, sort_order, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            """,
                (name, member.get("role", ""), member.get("owns", []), member.get("label", ""), i),
            )
    config.invalidate_cache()
    return config.get_team(_conn())


@router.get("/admin/config", auth=combined_auth)
def api_admin_config_get(request):
    denied = _require_super(request)
    if denied:
        return denied
    return config.get_all_config(_conn())


@router.put("/admin/config/{key}", auth=combined_auth)
def api_admin_config_put(request, key: str):
    denied = _require_super(request)
    if denied:
        return denied
    valid_keys = {
        "demerits",
        "issue_templates",
        "grade_thresholds",
        "camp_start",
        "camp_end",
        "activity_lookback_days",
        "list_stale_months",
        "list_stale_severe_months",
        "cleanup_tag_prefix",
        "cleanup_actions",
    }
    if key not in valid_keys:
        return JsonResponse({"error": f"unknown config key: {key}"}, status=400)
    data = json.loads(request.body)
    value = data.get("value") if isinstance(data, dict) and "value" in data else data
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO config (key, value, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
        """,
            (key, json.dumps(value)),
        )
    config.invalidate_cache()
    return {"ok": True, "key": key}


@router.delete("/admin/config/{key}", auth=combined_auth)
def api_admin_config_delete(request, key: str):
    denied = _require_super(request)
    if denied:
        return denied
    with get_cursor() as cur:
        cur.execute("DELETE FROM config WHERE key = %s", (key,))
    config.invalidate_cache()
    return {"ok": True, "key": key, "reset": True}
