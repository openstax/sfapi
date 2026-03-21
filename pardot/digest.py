"""
Daily text digest for Slack/email — Camp Campaign morning briefing.
Works with whatever tier of data is available.
"""

import logging
from datetime import date

from pardot import config
from pardot.assets import (
    get_asset_summary,
    get_campaign_connectivity,
    get_cleanup_status,
    get_prospect_sync_health,
    get_tag_review,
)
from pardot.db_compat import get_cursor

log = logging.getLogger("digest")


def _delta_str(current, previous, fmt="d", suffix=""):
    """Format a delta between current and previous values. Returns '' if no previous."""
    if previous is None:
        return ""
    delta = current - previous
    if delta == 0:
        return ""
    arrow = "+" if delta > 0 else ""
    if fmt == "d":
        return f" ({arrow}{delta}{suffix})"
    elif fmt == ".1f":
        return f" ({arrow}{delta:.1f}{suffix})"
    return f" ({arrow}{delta}{suffix})"


# Display names for area keys
_AREA_DISPLAY = {
    "campaigns": "Campaigns",
    "forms": "Forms",
    "lists": "Lists",
    "landing_pages": "LPs",
    "list_emails": "Emails",
    "custom_redirects": "Redirects",
    "tags": "Tags",
    "prospects": "Prospects",
}

# Short labels for issue keys (used in worst-area callouts)
_ISSUE_LABELS = {
    "campaigns_no_sf": "missing SF link",
    "campaigns_empty": "empty",
    "campaigns_dormant": "dormant",
    "campaigns_no_members": "no members",
    "campaigns_low_response": "low response",
    "campaigns_ghost": "ghost",
    "forms_no_campaign": "w/o campaign",
    "forms_dormant": "dormant",
    "forms_errors": "errors",
    "lps_no_campaign": "w/o campaign",
    "lps_dormant": "dormant",
    "lists_stale_1y": "stale 1y+",
    "lists_stale": "stale 6m+",
    "lists_unnamed": "unnamed",
    "emails_no_campaign": "w/o campaign",
    "emails_no_subject": "w/o subject",
    "redirects_no_campaign": "w/o campaign",
    "orphan_forms": "orphan",
    "orphan_lps": "orphan",
    "orphan_emails": "orphan",
    "orphan_redirects": "orphan",
    "prospects_unlinked_pct": "unlinked %",
    "tags_unused": "unused",
    "tags_no_convention": "no convention",
}


def _area_scores_from_snapshot(snapshot, demerits, grade_map):
    """Derive per-area health scores from a snapshot's issue count columns."""
    from scorecard import ISSUE_AREA, _grade

    area_keys = {}
    for key, area in ISSUE_AREA.items():
        area_keys.setdefault(area, []).append(key)

    areas = {}
    for area, keys in area_keys.items():
        area_demerits = 0
        any_data = False
        for k in keys:
            val = snapshot.get(k)
            if val is not None:
                area_demerits += val * demerits.get(k, 0)
                any_data = True
        if any_data:
            score = max(0, min(100, round(100 - area_demerits)))
            areas[area] = {"score": score, "grade": _grade(score, grade_map)}

    return areas


def generate_digest(conn, team=None) -> str:
    """Produce a formatted text block for Slack/email."""
    today = date.today()

    camp_start, camp_end = config.get_camp_dates(conn)
    camp_days = (camp_end - camp_start).days + 1

    if today < camp_start:
        day_label = "Pre-camp"
    elif today > camp_end:
        day_label = "Post-camp"
    else:
        day_num = (today - camp_start).days + 1
        day_label = f"Day {day_num} of {camp_days}"

    if team is None:
        team = config.get_team(conn)

    # Fetch yesterday's snapshot for deltas throughout
    with get_cursor(conn) as cur:
        cur.execute(
            """
            SELECT * FROM daily_snapshots
            WHERE snapshot_date < %s
            ORDER BY snapshot_date DESC LIMIT 1
        """,
            (today,),
        )
        yesterday = cur.fetchone()

    lines = []
    lines.append(f"Camp Campaign — {day_label} ({today.strftime('%b %-d')})")
    lines.append("=" * 50)

    # ── Health Score ──────────────────────────────────────────
    try:
        from scorecard import compute_health_score, generate_issues

        hs = compute_health_score(conn)
        overall = hs.get("overall", {})
        score = overall.get("score", 0)
        grade = overall.get("grade", "?")

        y_score = yesterday.get("health_score") if yesterday else None
        delta = _delta_str(score, y_score, suffix=" pts")
        lines.append("")
        lines.append(f"DATA HEALTH: {score}/100 ({grade}){delta}")

        # Per-person scores
        by_person = hs.get("by_person", {})
        if by_person:
            parts = [f"{name}: {info['score']} ({info['grade']})" for name, info in by_person.items()]
            lines.append(f"  {' | '.join(parts)}")

        # Per-area grades (compact one-liner)
        by_area = hs.get("by_area", {})
        if by_area:
            area_parts = [f"{_AREA_DISPLAY.get(k, k)} {v['grade']}" for k, v in by_area.items() if k in _AREA_DISPLAY]
            if area_parts:
                lines.append(f"  Areas: {' | '.join(area_parts)}")

            # Worst areas callout (C grade or below, up to 3)
            from scorecard import ISSUE_AREA

            issue_counts_temp = hs.get("issue_counts", {})
            sorted_areas = sorted(by_area.items(), key=lambda x: x[1]["score"])
            worst = [(k, v) for k, v in sorted_areas if v["grade"] in ("C", "D", "F")][:3]
            if worst:
                worst_parts = []
                for area_key, area_info in worst:
                    label = _AREA_DISPLAY.get(area_key, area_key)
                    area_issue_keys = [ik for ik, a in ISSUE_AREA.items() if a == area_key]
                    top_issue = max(area_issue_keys, key=lambda ik: issue_counts_temp.get(ik, 0), default=None)
                    top_count = issue_counts_temp.get(top_issue, 0) if top_issue else 0
                    detail = (
                        f" -- {top_count} {_ISSUE_LABELS.get(top_issue, top_issue)}"
                        if top_issue and top_count > 0
                        else ""
                    )
                    worst_parts.append(f"{label} ({area_info['score']}, {area_info['grade']}){detail}")
                lines.append(f"  Worst: {'  |  '.join(worst_parts)}")

        # ── 24h Changes ──────────────────────────────────────
        issue_counts = hs.get("issue_counts", {})
        if yesterday:
            changes = []
            change_keys = [
                ("campaigns_no_sf", "campaigns missing SF"),
                ("campaigns_empty", "empty campaigns"),
                ("forms_no_campaign", "forms w/o campaign"),
                ("forms_errors", "form errors"),
                ("lps_no_campaign", "LPs w/o campaign"),
                ("lists_stale_1y", "stale lists (1y+)"),
                ("lists_stale", "stale lists (6m+)"),
                ("emails_no_campaign", "emails w/o campaign"),
                ("emails_no_subject", "emails w/o subject"),
                ("redirects_no_campaign", "redirects w/o campaign"),
                ("orphan_forms", "orphan forms"),
                ("orphan_lps", "orphan LPs"),
                ("orphan_emails", "orphan emails"),
                ("orphan_redirects", "orphan redirects"),
                ("tags_unused", "unused tags"),
                ("campaigns_dormant", "dormant campaigns"),
                ("campaigns_no_members", "campaigns w/o members"),
                ("campaigns_low_response", "low-response campaigns"),
                ("campaigns_ghost", "ghost campaigns"),
                ("forms_dormant", "dormant forms"),
                ("lps_dormant", "dormant LPs"),
                ("lists_unnamed", "unnamed lists"),
                ("tags_no_convention", "tags w/o convention"),
            ]
            for key, label in change_keys:
                curr = issue_counts.get(key, 0)
                prev = yesterday.get(key)
                if prev is not None and curr != prev:
                    delta = curr - prev
                    arrow = "v" if delta < 0 else "^"  # down is good (fewer issues)
                    sign = "+" if delta > 0 else ""
                    changes.append(f"  {arrow} {label}: {prev} -> {curr} ({sign}{delta})")

            if changes:
                lines.append("")
                lines.append("24H CHANGES")
                for c in changes:
                    lines.append(c)
            else:
                lines.append("")
                lines.append("24H CHANGES: No movement")

        lines.append("")

        # ── Data Quality Summary ──────────────────────────────
        lines.append("DATA QUALITY SNAPSHOT")
        # Group issues by severity
        high_issues = []
        other_issues = []
        all_issues = generate_issues(conn, team=team)
        for issue in all_issues:
            if issue["priority"] == "high":
                high_issues.append(issue)
            else:
                other_issues.append(issue)

        total_issues = sum(i["count"] for i in all_issues)
        high_count = sum(i["count"] for i in high_issues)
        lines.append(f"  Total issues: {total_issues}  (high priority: {high_count})")

        if high_issues:
            lines.append("  High priority:")
            for issue in high_issues[:5]:
                owners_str = f" [{', '.join(issue['owners'])}]" if issue["owners"] else ""
                lines.append(f"    ! {issue['title']}{owners_str}")
        if other_issues:
            other_total = sum(i["count"] for i in other_issues)
            lines.append(f"  + {other_total} lower-priority issues across {len(other_issues)} categories")

        lines.append("")
    except Exception as e:
        log.warning(f"Digest health score failed: {e}")

    # ── Campaign Connectivity ─────────────────────────────────
    try:
        cc = get_campaign_connectivity(conn)
        s = cc.get("summary", {})
        if s.get("total", 0) > 0:
            lines.append("CAMPAIGN CONNECTIVITY")
            lines.append(
                f"  {s['with_assets']:,} with assets | "
                f"{s['empty']:,} empty | "
                f"{s['with_sf_campaign']:,} linked to SF | "
                f"{s['missing_sf_campaign']:,} missing SF link"
            )
            orphan_parts = []
            for key, label in [
                ("orphan_forms", "forms"),
                ("orphan_lps", "LPs"),
                ("orphan_emails", "emails"),
                ("orphan_redirects", "redirects"),
            ]:
                n = s.get(key, 0)
                if n > 0:
                    orphan_parts.append(f"{n} {label}")
            if orphan_parts:
                lines.append(f"  Orphaned: {', '.join(orphan_parts)}")
            # Campaign member coverage
            with_members = s.get("with_members", 0)
            without_members = s.get("without_members", 0)
            total_members = s.get("total_members", 0)
            if with_members > 0 or without_members > 0:
                lines.append(
                    f"  Members: {with_members} campaigns have {total_members:,} total members | "
                    f"{without_members} SF-linked campaigns have none"
                )
            lines.append("")
    except Exception as e:
        log.debug(f"Digest campaign connectivity skipped: {e}")

    # ── SF Health (Tier 1) ───────────────────────────────────
    with get_cursor(conn) as cur:
        cur.execute("SELECT * FROM sf_health ORDER BY captured_at DESC LIMIT 1")
        sf = cur.fetchone()

    lines.append("SF HEALTH")
    if sf:
        linked = sf["leads_with_pardot"] + sf["contacts_with_pardot"]
        total_sf = sf["total_leads"] + sf["total_contacts"]
        pct = (linked / total_sf * 100) if total_sf > 0 else 0

        pct_delta = ""
        if yesterday and yesterday.get("sf_leads_total") is not None:
            y_linked = (yesterday.get("sf_leads_with_pardot") or 0) + (yesterday.get("sf_contacts_with_pardot") or 0)
            y_total = (yesterday.get("sf_leads_total") or 0) + (yesterday.get("sf_contacts_total") or 0)
            if y_total > 0:
                y_pct = y_linked / y_total * 100
                pct_delta = _delta_str(pct, y_pct, fmt=".1f", suffix="pp")

        lines.append(f"  Pardot coverage:   {linked:,} / {total_sf:,} ({pct:.1f}%){pct_delta}")
        lines.append(f"  Leads:             {sf['total_leads']:,}  ({sf['leads_with_pardot']:,} linked)")
        lines.append(f"  Contacts:          {sf['total_contacts']:,}  ({sf['contacts_with_pardot']:,} linked)")
    else:
        lines.append("  (no data yet -- run: python camp.py)")

    lines.append("")

    # ── Top Engaged (Tier 2+) ────────────────────────────────
    with get_cursor(conn) as cur:
        cur.execute("SELECT COUNT(*) AS n FROM prospects")
        has_prospects = cur.fetchone()["n"] > 0

    if has_prospects:
        # Prospect sync health summary
        try:
            psh = get_prospect_sync_health(conn)
            if psh and psh.get("active", 0) > 0:
                lines.append("PROSPECT SYNC HEALTH")
                parts = [f"{psh['active']:,} active"]
                if psh.get("link_rate") is not None:
                    detail = f"{psh['link_rate']:.1f}% linked"
                    if psh.get("linked_as_lead") or psh.get("linked_as_contact"):
                        detail += (
                            f" ({psh.get('linked_as_lead', 0):,} lead, {psh.get('linked_as_contact', 0):,} contact)"
                        )
                    parts.append(detail)
                if psh.get("unlinked", 0) > 0:
                    parts.append(f"{psh['unlinked']:,} unlinked")
                if psh.get("opted_out", 0) > 0:
                    parts.append(f"{psh['opted_out']:,} opted out")
                lines.append(f"  {' | '.join(parts)}")
                lines.append("")
        except Exception as e:
            log.debug(f"Digest prospect sync health skipped: {e}")

        # Engagement summary + grade distribution
        from engagement import get_crm_id_alerts, get_engagement_summary, get_top_engaged

        try:
            eng = get_engagement_summary(conn)
            if eng.get("total_count", 0) > 0:
                lines.append("PROSPECT ENGAGEMENT")
                lines.append(
                    f"  {eng['total_count']:,} total | avg score {eng['avg_score']:.0f} | "
                    f"top score {eng['top_score']} | {eng['active_30d']:,} active (30d)"
                )
                grades = eng.get("grade_distribution", {})
                if grades:
                    grade_str = "  ".join(f"{g}: {n:,}" for g, n in sorted(grades.items()) if n > 0)
                    lines.append(f"  Grades — {grade_str}")
                lines.append("")
        except Exception as e:
            log.debug(f"Digest engagement summary skipped: {e}")

        # CRM ID alerts (bad SF IDs in prospect records)
        try:
            alerts = get_crm_id_alerts(conn)
            if alerts.get("total_bad", 0) > 0:
                s = alerts["summary"]
                lines.append("CRM ID ALERTS")
                id_parts = []
                if s.get("bad_lead_count", 0):
                    id_parts.append(f"{s['bad_lead_count']:,} lead")
                if s.get("bad_contact_count", 0):
                    id_parts.append(f"{s['bad_contact_count']:,} contact")
                id_detail = f" ({', '.join(id_parts)})" if id_parts else ""
                lines.append(f"  {s['total_bad']:,} prospects ({s['pct_affected']}%) have invalid CRM IDs{id_detail}")
                if s.get("high_score_count", 0) > 0:
                    lines.append(f"  ! {s['high_score_count']} are high-score (100+) — sync at risk")
                if s.get("top_companies"):
                    cos = ", ".join(c["company"] for c in s["top_companies"][:4])
                    lines.append(f"  Top affected: {cos}")
                lines.append("")
        except Exception as e:
            log.debug(f"Digest CRM ID alerts skipped: {e}")

        lines.append("TOP ENGAGED (suspicious? audit these!)")
        top = get_top_engaged(conn, limit=5)
        for i, p in enumerate(top, 1):
            email = p["email"] or f"ID {p['id']}"
            score = p["score"] or 0
            acts = p["activity_count"] or 0
            lines.append(f"  {i}. {email} -- Score: {score}, {acts} activities (30d)")
        lines.append("")

    # Orphan detection summary (Tier 3)
    try:
        with get_cursor(conn) as cur:
            cur.execute("SELECT * FROM orphan_runs ORDER BY run_at DESC LIMIT 1")
            orphan_run = cur.fetchone()
        if orphan_run:
            parts = []
            if orphan_run.get("pardot_missing_crm", 0):
                parts.append(f"{orphan_run['pardot_missing_crm']:,} Pardot prospects missing from CRM")
            if orphan_run.get("sf_missing_pardot", 0):
                parts.append(f"{orphan_run['sf_missing_pardot']:,} SF records missing from Pardot")
            if orphan_run.get("unlinked_prospects", 0):
                parts.append(f"{orphan_run['unlinked_prospects']:,} completely unlinked")
            if parts:
                run_date = orphan_run["run_at"].strftime("%b %-d") if orphan_run.get("run_at") else "?"
                lines.append(f"ORPHAN DETECTION (as of {run_date})")
                for p in parts:
                    lines.append(f"  {p}")
                lines.append("")
    except Exception as e:
        log.debug(f"Digest orphan run skipped: {e}")

    # ── Asset Inventory (Tier 1) ─────────────────────────────
    counts = get_asset_summary(conn)
    if any(counts.values()):
        lines.append("ASSET INVENTORY")
        lines.append(
            f"  Campaigns: {counts.get('campaigns', 0)} | "
            f"Lists: {counts.get('lists', 0)} | "
            f"Forms: {counts.get('forms', 0)} | "
            f"LPs: {counts.get('landing_pages', 0)} | "
            f"Emails: {counts.get('list_emails', 0)} | "
            f"Redirects: {counts.get('custom_redirects', 0)}"
        )
        lines.append("")

    # ── Tags (Tier 1) ──────────────────────────────────────────
    try:
        tr = get_tag_review(conn)
        if tr["total_tags"] > 0:
            s = tr["summary"]
            patterns = len(tr["naming_patterns"])
            lines.append(
                f"TAGS: {tr['total_tags']} total, {s['unused']} unused, {patterns} naming pattern{'s' if patterns != 1 else ''}"
            )
            lines.append("")
    except Exception:
        log.debug("Tag review skipped")

    # ── Triage Progress ───────────────────────────────────────
    try:
        cs = get_cleanup_status(conn)
        if cs.get("configured") and cs.get("progress"):
            total_flagged = sum(p["total"] for p in cs["progress"].values())
            total_tagged = sum(p["tagged"] for p in cs["progress"].values())
            if total_flagged > 0:
                pct = total_tagged / total_flagged * 100
                lines.append("TRIAGE PROGRESS")
                lines.append(f"  Reviewed: {total_tagged}/{total_flagged} flagged items ({pct:.1f}%)")
                # Show per-action breakdown if any actions have items
                actions_with_items = [
                    (name, info) for name, info in cs.get("actions", {}).items() if info.get("total", 0) > 0
                ]
                if actions_with_items:
                    action_parts = [f"{name}: {info['total']}" for name, info in actions_with_items]
                    lines.append(f"  Actions: {' | '.join(action_parts)}")
                lines.append("")
    except Exception as e:
        log.debug(f"Digest triage progress skipped: {e}")

    # ── Open Tasks ───────────────────────────────────────────
    with get_cursor(conn) as cur:
        cur.execute("""
            SELECT assignee, title, priority
            FROM tasks WHERE status = 'open'
            ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 WHEN 'low' THEN 2 END, created_at
        """)
        open_tasks = cur.fetchall()

    if open_tasks:
        lines.append("OPEN TASKS")
        by_person = {}
        for t in open_tasks:
            by_person.setdefault(t["assignee"], []).append(t)
        for person, tasks in by_person.items():
            task_list = ", ".join(("!" if t["priority"] == "high" else "") + t["title"] for t in tasks)
            lines.append(f"  {person}: {task_list}")
        lines.append("")

    return "\n".join(lines)


def generate_progress_report(conn) -> str:
    """One-pager showing improvements over time from daily_snapshots.

    Compares earliest snapshot to latest, and shows the full trend.
    Designed for copy-paste into Slack or a status update.
    """
    today = date.today()

    with get_cursor(conn) as cur:
        cur.execute("""
            SELECT * FROM daily_snapshots
            ORDER BY snapshot_date ASC
        """)
        snapshots = [dict(r) for r in cur.fetchall()]

    if not snapshots:
        return "No daily snapshots yet. Run 'python camp.py' to start tracking."

    first = snapshots[0]
    latest = snapshots[-1]
    total_days = len(snapshots)

    lines = []
    lines.append(f"Camp Campaign -- Progress Report ({today.strftime('%b %-d')})")
    lines.append("=" * 55)
    lines.append(f"Tracking since {first['snapshot_date']} ({total_days} day{'s' if total_days != 1 else ''})")
    lines.append("")

    # ── Health Score Trend ─────────────────────────────────────
    first_score = first.get("health_score")
    latest_score = latest.get("health_score")
    if latest_score is not None:
        lines.append("HEALTH SCORE TREND")
        if first_score is not None:
            delta = latest_score - first_score
            sign = "+" if delta > 0 else ""
            lines.append(f"  Start: {first_score}/100  ->  Now: {latest_score}/100  ({sign}{delta} pts)")
        else:
            lines.append(f"  Current: {latest_score}/100 ({latest.get('health_grade', '?')})")

        # Show score for each snapshot as a mini sparkline
        scored = [(s["snapshot_date"], s["health_score"]) for s in snapshots if s.get("health_score") is not None]
        if len(scored) > 1:
            scores_only = [s[1] for s in scored]
            lo, hi = min(scores_only), max(scores_only)
            bars = "  "
            for _dt, sc in scored:
                # Simple ASCII bar: map score to block chars
                if hi == lo:
                    bars += "\u2588"
                else:
                    level = (sc - lo) / (hi - lo)
                    blocks = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
                    bars += blocks[int(level * 8)]
            lines.append(f"{bars}  ({scored[0][0]} -> {scored[-1][0]})")
        lines.append("")

    # ── Per-Area Scores (start -> now) ────────────────────────
    try:
        demerits = config.get_demerits(conn)
        grade_map = config.get_grade_map(conn)
        first_areas = _area_scores_from_snapshot(first, demerits, grade_map)
        latest_areas = _area_scores_from_snapshot(latest, demerits, grade_map)

        if latest_areas:
            lines.append("AREA SCORES (start -> now)")
            # Display in pairs of two per line
            area_order = [
                "campaigns",
                "forms",
                "lists",
                "landing_pages",
                "list_emails",
                "custom_redirects",
                "tags",
                "prospects",
            ]
            area_lines = []
            for area in area_order:
                if area not in latest_areas:
                    continue
                label = _AREA_DISPLAY.get(area, area)
                latest_s = latest_areas[area]["score"]
                if area in first_areas:
                    first_s = first_areas[area]["score"]
                    delta = latest_s - first_s
                    delta_str = f"+{delta}" if delta > 0 else str(delta) if delta != 0 else "-"
                    area_lines.append(f"{label}: {first_s} -> {latest_s} ({delta_str})")
                else:
                    area_lines.append(f"{label}: {latest_s}")
            # Print two per line for compactness
            for i in range(0, len(area_lines), 2):
                pair = area_lines[i : i + 2]
                lines.append(f"  {'  |  '.join(f'{p:<28}' if j < len(pair) - 1 else p for j, p in enumerate(pair))}")
            lines.append("")
    except Exception as e:
        log.debug(f"Progress report area scores skipped: {e}")

    # ── Issue Resolution ──────────────────────────────────────
    issue_keys = [
        ("campaigns_no_sf", "Campaigns missing SF link"),
        ("campaigns_empty", "Empty campaigns"),
        ("forms_no_campaign", "Forms w/o campaign"),
        ("forms_errors", "Form errors"),
        ("lps_no_campaign", "LPs w/o campaign"),
        ("lists_stale_1y", "Stale lists (1y+)"),
        ("lists_stale", "Stale lists (6m+)"),
        ("lists_unnamed", "Unnamed lists"),
        ("emails_no_campaign", "Emails w/o campaign"),
        ("emails_no_subject", "Emails w/o subject"),
        ("redirects_no_campaign", "Redirects w/o campaign"),
        ("campaigns_dormant", "Dormant campaigns"),
        ("campaigns_no_members", "Campaigns w/o members"),
        ("campaigns_low_response", "Low response campaigns"),
        ("campaigns_ghost", "Ghost campaigns"),
        ("forms_dormant", "Dormant forms"),
        ("lps_dormant", "Dormant LPs"),
        ("orphan_forms", "Orphan forms"),
        ("orphan_lps", "Orphan LPs"),
        ("orphan_emails", "Orphan emails"),
        ("orphan_redirects", "Orphan redirects"),
        ("tags_unused", "Unused tags"),
        ("tags_no_convention", "Tags w/o naming convention"),
    ]

    improved = []
    worsened = []
    unchanged = []
    for key, label in issue_keys:
        first_val = first.get(key)
        latest_val = latest.get(key)
        if first_val is None or latest_val is None:
            continue
        delta = latest_val - first_val
        if delta < 0:
            improved.append((label, first_val, latest_val, delta))
        elif delta > 0:
            worsened.append((label, first_val, latest_val, delta))
        else:
            unchanged.append((label, first_val, latest_val))

    if improved or worsened:
        lines.append("ISSUE CHANGES (start -> now)")
        if improved:
            lines.append("  Improved:")
            for label, fv, lv, delta in improved:
                lines.append(f"    + {label}: {fv} -> {lv} ({delta})")
        if worsened:
            lines.append("  Worsened:")
            for label, fv, lv, delta in worsened:
                lines.append(f"    - {label}: {fv} -> {lv} (+{delta})")
        if unchanged:
            lines.append(f"  Unchanged: {len(unchanged)} categories")
        lines.append("")

    # ── Best/Worst Area Highlights ────────────────────────────
    try:
        _demerits = config.get_demerits(conn)
        _grade_map = config.get_grade_map(conn)
        _first_areas = _area_scores_from_snapshot(first, _demerits, _grade_map)
        _latest_areas = _area_scores_from_snapshot(latest, _demerits, _grade_map)

        if _first_areas and _latest_areas:
            # Find areas with biggest improvement and biggest remaining gap
            deltas = []
            for area in _latest_areas:
                if area in _first_areas:
                    d = _latest_areas[area]["score"] - _first_areas[area]["score"]
                    deltas.append((area, d, _latest_areas[area]["score"]))
            if deltas:
                deltas.sort(key=lambda x: x[1], reverse=True)
                best = [(a, d, s) for a, d, s in deltas if d > 0]
                needs_work = sorted(deltas, key=lambda x: x[2])
                highlights = []
                if best:
                    top = best[0]
                    highlights.append(f"Most improved: {_AREA_DISPLAY.get(top[0], top[0])} (+{top[1]} pts)")
                needs = [x for x in needs_work if x[2] < 80][:2]
                if needs:
                    parts = [f"{_AREA_DISPLAY.get(a, a)} ({s})" for a, _, s in needs]
                    highlights.append(f"Needs work: {', '.join(parts)}")
                if highlights:
                    lines.append("HIGHLIGHTS")
                    for h in highlights:
                        lines.append(f"  {h}")
                    lines.append("")
    except Exception as e:
        log.debug(f"Progress report area highlights skipped: {e}")

    # ── Engagement Score Trend (Tier 2+) ──────────────────────
    first_top = first.get("top_score")
    latest_top = latest.get("top_score")
    first_avg = first.get("avg_score_sampled")
    latest_avg = latest.get("avg_score_sampled")
    if latest_top is not None or latest_avg is not None:
        lines.append("ENGAGEMENT SCORE TREND (top 500 sampled)")
        if latest_top is not None:
            if first_top is not None and first_top != latest_top:
                delta = latest_top - first_top
                sign = "+" if delta > 0 else ""
                lines.append(f"  Top score:  {first_top} -> {latest_top}  ({sign}{delta})")
            else:
                lines.append(f"  Top score:  {latest_top}")
        if latest_avg is not None:
            if first_avg is not None and abs(latest_avg - first_avg) > 0.05:
                delta = latest_avg - first_avg
                sign = "+" if delta > 0 else ""
                lines.append(f"  Avg score:  {first_avg:.1f} -> {latest_avg:.1f}  ({sign}{delta:.1f})")
            else:
                lines.append(f"  Avg score:  {latest_avg:.1f}")
        lines.append("")

    # ── SF Coverage Trend ─────────────────────────────────────
    first_sf_linked = _sf_linked(first)
    latest_sf_linked = _sf_linked(latest)
    if first_sf_linked is not None and latest_sf_linked is not None:
        first_total = _sf_total(first)
        latest_total = _sf_total(latest)
        first_pct = (first_sf_linked / first_total * 100) if first_total else 0
        latest_pct = (latest_sf_linked / latest_total * 100) if latest_total else 0
        pct_delta = latest_pct - first_pct
        sign = "+" if pct_delta > 0 else ""

        lines.append("SF COVERAGE TREND")
        lines.append(f"  Start: {first_sf_linked:,} / {first_total:,} ({first_pct:.1f}%)")
        lines.append(f"  Now:   {latest_sf_linked:,} / {latest_total:,} ({latest_pct:.1f}%)")
        lines.append(f"  Change: {sign}{pct_delta:.1f} percentage points")
        lines.append("")

    # ── Task Completion ────────────────────────────────────────
    first_done = first.get("tasks_done") or 0
    latest_done = latest.get("tasks_done") or 0
    latest_open = latest.get("tasks_open") or 0
    if latest_done > 0 or latest_open > 0:
        lines.append("TASKS")
        lines.append(f"  Completed: {latest_done}  |  Open: {latest_open}")
        if first_done is not None and latest_done > first_done:
            lines.append(f"  Completed since tracking began: {latest_done - first_done}")
        # Per-person task breakdown
        try:
            with get_cursor(conn) as cur:
                cur.execute("""
                    SELECT assignee,
                           COUNT(*) FILTER (WHERE status = 'done') AS done,
                           COUNT(*) FILTER (WHERE status = 'open') AS open
                    FROM tasks
                    GROUP BY assignee
                    ORDER BY done DESC
                """)
                person_tasks = cur.fetchall()
            if person_tasks:
                parts = [f"{r['assignee']}: {r['done']} done, {r['open']} open" for r in person_tasks]
                lines.append(f"  {'  |  '.join(parts)}")
        except Exception:
            log.debug("Task progress section skipped")
        lines.append("")

    # ── Prospect Sync Health Trend ────────────────────────────
    try:
        psh = get_prospect_sync_health(conn)
        if psh and psh.get("active", 0) > 0:
            # Check if first snapshot had prospect data too
            _first_prospect_count = first.get("prospect_count")
            latest_link_rate = psh.get("link_rate")
            if latest_link_rate is not None:
                lines.append("PROSPECT SYNC HEALTH")
                lines.append(
                    f"  {psh['active']:,} active | "
                    f"{latest_link_rate:.1f}% linked "
                    f"({psh.get('linked_as_lead', 0):,} lead, {psh.get('linked_as_contact', 0):,} contact)"
                )
                if psh.get("unlinked", 0) > 0:
                    lines.append(f"  {psh['unlinked']:,} unlinked | {psh.get('opted_out', 0):,} opted out")
                lines.append("")
    except Exception as e:
        log.debug(f"Progress report prospect sync health skipped: {e}")

    # ── Orphan Detection (Tier 3) ─────────────────────────────
    try:
        with get_cursor(conn) as cur:
            cur.execute("""
                SELECT run_at, pardot_missing_crm, sf_missing_pardot, unlinked_prospects
                FROM orphan_runs ORDER BY run_at DESC LIMIT 5
            """)
            orphan_history = [dict(r) for r in cur.fetchall()]
        if orphan_history:
            latest_o = orphan_history[0]
            run_date = latest_o["run_at"].strftime("%b %-d") if latest_o.get("run_at") else "?"
            lines.append(f"ORPHAN DETECTION (latest run: {run_date})")
            if latest_o.get("pardot_missing_crm", 0):
                lines.append(f"  Pardot missing from CRM:  {latest_o['pardot_missing_crm']:,}")
            if latest_o.get("sf_missing_pardot", 0):
                lines.append(f"  SF missing from Pardot:   {latest_o['sf_missing_pardot']:,}")
            if latest_o.get("unlinked_prospects", 0):
                lines.append(f"  Completely unlinked:      {latest_o['unlinked_prospects']:,}")
            # Show trend across runs if multiple exist
            if len(orphan_history) > 1:
                oldest = orphan_history[-1]
                old_date = oldest["run_at"].strftime("%b %-d") if oldest.get("run_at") else "?"
                delta_missing = (latest_o.get("pardot_missing_crm") or 0) - (oldest.get("pardot_missing_crm") or 0)
                if delta_missing != 0:
                    sign = "+" if delta_missing > 0 else ""
                    lines.append(f"  vs {old_date}: missing from CRM {sign}{delta_missing}")
            lines.append("")
    except Exception as e:
        log.debug(f"Progress orphan history skipped: {e}")

    # ── Daily Log (last 7 entries) ─────────────────────────────
    recent = snapshots[-7:]
    if len(recent) > 1:
        lines.append("DAILY LOG (last 7 days)")
        lines.append(f"  {'Date':<12} {'Score':>5}  {'Issues':>6}  {'Coverage':>8}")
        lines.append(f"  {'-' * 12} {'-' * 5}  {'-' * 6}  {'-' * 8}")
        for s in recent:
            dt = str(s["snapshot_date"])
            sc = str(s.get("health_score", "-")).rjust(5)
            # Sum issue counts
            total_issues = _sum_issues(s)
            issues_str = str(total_issues).rjust(6) if total_issues is not None else "     -"
            sf_l = _sf_linked(s)
            sf_t = _sf_total(s)
            if sf_l is not None and sf_t:
                cov = f"{sf_l / sf_t * 100:.1f}%".rjust(8)
            else:
                cov = "       -"
            lines.append(f"  {dt:<12} {sc}  {issues_str}  {cov}")
        lines.append("")

    return "\n".join(lines)


def _sf_linked(snapshot):
    lp = snapshot.get("sf_leads_with_pardot")
    cp = snapshot.get("sf_contacts_with_pardot")
    if lp is None and cp is None:
        return None
    return (lp or 0) + (cp or 0)


def _sf_total(snapshot):
    lt = snapshot.get("sf_leads_total")
    ct = snapshot.get("sf_contacts_total")
    if lt is None and ct is None:
        return None
    return (lt or 0) + (ct or 0)


def _sum_issues(snapshot):
    """Sum all issue count columns in a snapshot."""
    keys = [
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
    total = 0
    any_found = False
    for k in keys:
        v = snapshot.get(k)
        if v is not None:
            total += v
            any_found = True
    return total if any_found else None
