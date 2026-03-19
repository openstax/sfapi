"""
Engagement analysis — top engaged prospects and activity enrichment.
Reads from PostgreSQL prospects + visitor_activities tables.
"""

import logging

from pardot.db_compat import get_cursor

log = logging.getLogger("engagement")


def get_top_engaged(conn, limit=50) -> list[dict]:
    """
    Top prospects by score + activity count (30d).
    These are the hottest campfires — make sure they're not wildfires.
    """
    with get_cursor(conn) as cur:
        cur.execute(
            """
            SELECT
                p.id, p.email, p.first_name, p.last_name, p.company,
                p.score, p.grade,
                p.salesforce_id, p.salesforce_lead_id, p.salesforce_contact_id,
                COUNT(va.id) AS activity_count,
                MAX(va.created_at) AS last_activity
            FROM prospects p
            LEFT JOIN visitor_activities va
                ON va.prospect_id = p.id AND va.created_at > NOW() - INTERVAL '30 days'
            WHERE p.is_deleted = FALSE
            GROUP BY p.id
            ORDER BY p.score DESC NULLS LAST, activity_count DESC
            LIMIT %s
        """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def get_prospect_activities(conn, prospect_id: int, days=30) -> list[dict]:
    """Activity detail for a single prospect."""
    with get_cursor(conn) as cur:
        cur.execute(
            """
            SELECT id, type, type_name, campaign_id, form_id,
                   landing_page_id, email_id, created_at
            FROM visitor_activities
            WHERE prospect_id = %s AND created_at > NOW() - make_interval(days := %s)
            ORDER BY created_at DESC
        """,
            (prospect_id, days),
        )
        return [dict(row) for row in cur.fetchall()]


def get_scoring_categories(conn, prospect_ids: list[int]) -> dict[int, dict[str, float]]:
    """Return per-category score breakdowns for a list of prospect IDs.

    Returns {prospect_id: {"Adoption Engagement": 50.0, ...}, ...}.
    Prospects with no category data are omitted from the result.
    """
    if not prospect_ids:
        return {}
    with get_cursor(conn) as cur:
        cur.execute(
            """
            SELECT prospect_id, category_name, score
            FROM scoring_categories
            WHERE prospect_id = ANY(%s)
        """,
            (prospect_ids,),
        )
        rows = cur.fetchall()
    result = {}
    for r in rows:
        pid = r["prospect_id"]
        if pid not in result:
            result[pid] = {}
        result[pid][r["category_name"]] = float(r["score"]) if r["score"] is not None else 0.0
    return result


def get_crm_id_alerts(conn) -> dict:
    """Find prospects with email addresses or other junk in CRM ID fields.

    Returns row-level data plus summary stats for dashboard metrics.
    """
    with get_cursor(conn) as cur:
        cur.execute("""
            SELECT id, email, first_name, last_name, company, score, grade,
                   salesforce_lead_id, salesforce_contact_id
            FROM prospects
            WHERE is_deleted = FALSE
              AND salesforce_lead_id IS NOT NULL AND salesforce_lead_id != ''
              AND (salesforce_lead_id LIKE '%%@%%'
                   OR salesforce_lead_id !~ '^[a-zA-Z0-9]{15,18}$')
        """)
        bad_lead = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT id, email, first_name, last_name, company, score, grade,
                   salesforce_lead_id, salesforce_contact_id
            FROM prospects
            WHERE is_deleted = FALSE
              AND salesforce_contact_id IS NOT NULL AND salesforce_contact_id != ''
              AND (salesforce_contact_id LIKE '%%@%%'
                   OR salesforce_contact_id !~ '^[a-zA-Z0-9]{15,18}$')
        """)
        bad_contact = [dict(r) for r in cur.fetchall()]

        # Total prospect count for context
        cur.execute("SELECT COUNT(*) AS n FROM prospects WHERE is_deleted = FALSE")
        total_prospects = cur.fetchone()["n"]

    # Merge into deduplicated list for summary computation
    lead_ids = {r["id"] for r in bad_lead}
    contact_ids = {r["id"] for r in bad_contact}
    all_ids = lead_ids | contact_ids
    both_ids = lead_ids & contact_ids

    # Build merged list for stats
    by_id = {}
    for r in bad_lead:
        by_id[r["id"]] = r
    for r in bad_contact:
        if r["id"] not in by_id:
            by_id[r["id"]] = r

    scores = [r["score"] or 0 for r in by_id.values()]
    high_score = sum(1 for s in scores if s >= 100)
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    # Top companies by affected count
    co_counts = {}
    for r in by_id.values():
        co = (r.get("company") or "").strip()
        if co:
            co_counts[co] = co_counts.get(co, 0) + 1
    top_companies = sorted(co_counts.items(), key=lambda x: -x[1])[:8]

    # Grade distribution
    grade_counts = {}
    for r in by_id.values():
        g = (r.get("grade") or "").strip()
        if g:
            grade_counts[g] = grade_counts.get(g, 0) + 1

    return {
        "bad_lead_ids": bad_lead,
        "bad_contact_ids": bad_contact,
        "total_bad": len(all_ids),
        "summary": {
            "total_prospects": total_prospects,
            "pct_affected": round(len(all_ids) / total_prospects * 100, 1) if total_prospects else 0,
            "bad_lead_count": len(lead_ids),
            "bad_contact_count": len(contact_ids),
            "both_count": len(both_ids),
            "high_score_count": high_score,
            "avg_score": avg_score,
            "top_companies": [{"company": co, "count": n} for co, n in top_companies],
            "grade_distribution": grade_counts,
        },
    }


def get_adoption_json_alert(conn) -> dict:
    """Find prospects with AdoptionJSON still set (not blank).

    AdoptionJSON should be empty (or literally 'Blank') after processing.
    Prospects where it's populated likely have a stuck/broken adoption sync.
    """
    with get_cursor(conn) as cur:
        cur.execute("""
            SELECT COUNT(*) AS n
            FROM prospects
            WHERE is_deleted = FALSE
              AND adoption_json IS NOT NULL
              AND adoption_json != ''
              AND LOWER(TRIM(adoption_json)) != 'blank'
        """)
        stuck_count = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) AS n FROM prospects WHERE is_deleted = FALSE")
        total = cur.fetchone()["n"]

        # High-score subset (most urgent)
        cur.execute("""
            SELECT COUNT(*) AS n
            FROM prospects
            WHERE is_deleted = FALSE
              AND adoption_json IS NOT NULL
              AND adoption_json != ''
              AND LOWER(TRIM(adoption_json)) != 'blank'
              AND score >= 100
        """)
        high_score = cur.fetchone()["n"]

        # Sample a few for context
        cur.execute("""
            SELECT id, email, first_name, last_name, company, score, grade,
                   adoption_json
            FROM prospects
            WHERE is_deleted = FALSE
              AND adoption_json IS NOT NULL
              AND adoption_json != ''
              AND LOWER(TRIM(adoption_json)) != 'blank'
            ORDER BY score DESC NULLS LAST
            LIMIT 10
        """)
        sample = [dict(r) for r in cur.fetchall()]

    return {
        "stuck_count": stuck_count,
        "total_prospects": total,
        "pct_affected": round(stuck_count / total * 100, 1) if total else 0,
        "high_score_count": high_score,
        "sample": sample,
    }


def get_engagement_summary(conn) -> dict:
    """Aggregate engagement stats."""
    with get_cursor(conn) as cur:
        cur.execute("""
            SELECT
                COALESCE(AVG(score), 0) AS avg_score,
                MAX(score) AS top_score,
                COUNT(*) FILTER (WHERE score > 0) AS scored_count,
                COUNT(*) AS total_count
            FROM prospects WHERE is_deleted = FALSE
        """)
        score_row = dict(cur.fetchone())

        # Grade distribution
        cur.execute("""
            SELECT grade, COUNT(*) AS n
            FROM prospects
            WHERE is_deleted = FALSE AND grade IS NOT NULL AND grade != ''
            GROUP BY grade ORDER BY grade
        """)
        grades = {row["grade"]: row["n"] for row in cur.fetchall()}

        # Active in 30d
        cur.execute("""
            SELECT COUNT(DISTINCT prospect_id) AS n FROM visitor_activities
            WHERE created_at > NOW() - INTERVAL '30 days'
        """)
        active_30d = cur.fetchone()["n"]

        return {
            "avg_score": round(float(score_row["avg_score"]), 1),
            "top_score": score_row["top_score"] or 0,
            "scored_count": score_row["scored_count"],
            "total_count": score_row["total_count"],
            "grade_distribution": grades,
            "active_30d": active_30d,
        }
