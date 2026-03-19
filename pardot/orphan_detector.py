"""
Orphan Detector: Pardot <-> Salesforce Sync Integrity Check
==========================================================

Finds the ghosts in the machine:
  1. Pardot prospects with a CRM ID that no longer exists in Salesforce
  2. Salesforce Leads/Contacts with a Pardot ID that doesn't exist in Pardot
  3. Pardot prospects with NO CRM link at all (the "lost souls")

Reads from PostgreSQL prospects cache, stores results in orphan_runs.
"""

import json
import logging
import math
import time

from pardot.db_compat import get_cursor

log = logging.getLogger("orphan_detector")

BATCH_SIZE = 200  # SOQL IN clause limit


def chunk_list(lst: list, size: int):
    """Yield successive chunks from a list."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def _fmt_duration(seconds: float) -> str:
    """Format seconds into a human-readable duration like '2m 15s'."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"


def _log_batch_progress(batch_num: int, total_batches: int, t0: float):
    elapsed = time.monotonic() - t0
    pct = batch_num / total_batches * 100
    rate = batch_num / elapsed if elapsed > 0 else 0
    remaining = (total_batches - batch_num) / rate if rate > 0 else 0
    log.info(
        f"CHECK 1: Validated {batch_num}/{total_batches} batches "
        f"({pct:.1f}%, {_fmt_duration(elapsed)} elapsed, ~{_fmt_duration(remaining)} remaining)"
    )


# ── Check 1: Pardot prospects pointing to deleted CRM records ───────


def find_pardot_orphans_missing_crm(sf, conn) -> list[dict]:
    """
    Prospects that have a salesforce_id but that ID is gone from SF.
    """
    log.info("CHECK 1: Pardot prospects with stale CRM references")

    # Get all prospects with a CRM link from PostgreSQL
    with get_cursor(conn) as cur:
        cur.execute("""
            SELECT id, email, first_name, last_name,
                   salesforce_id, salesforce_lead_id, salesforce_contact_id, salesforce_account_id,
                   updated_at
            FROM prospects
            WHERE is_deleted = FALSE
              AND (salesforce_id IS NOT NULL AND salesforce_id != ''
                OR salesforce_lead_id IS NOT NULL AND salesforce_lead_id != ''
                OR salesforce_contact_id IS NOT NULL AND salesforce_contact_id != '')
        """)
        prospects_with_crm = cur.fetchall()

    log.info(f"Found {len(prospects_with_crm)} prospects with CRM links. Validating against SF...")

    # Determine which SF ID to validate for each prospect
    sf_id_map = {}  # sf_id -> prospect row
    for p in prospects_with_crm:
        sf_id = p["salesforce_id"] or p["salesforce_lead_id"] or p["salesforce_contact_id"]
        if sf_id:
            sf_id_map[sf_id] = p

    # Group by ID prefix for targeted SOQL
    lead_ids = [sid for sid in sf_id_map if sid.startswith("00Q")]
    contact_ids = [sid for sid in sf_id_map if sid.startswith("003")]
    other_ids = [sid for sid in sf_id_map if not sid.startswith("00Q") and not sid.startswith("003")]

    valid_sf_ids = set()

    total_batches = (
        math.ceil(len(lead_ids) / BATCH_SIZE)
        + math.ceil(len(contact_ids) / BATCH_SIZE)
        + math.ceil(len(other_ids) / BATCH_SIZE)
    )
    batch_num = 0
    t0 = time.monotonic()

    for batch in chunk_list(lead_ids, BATCH_SIZE):
        id_list = "','".join(batch)
        results = sf.query_all(f"SELECT Id FROM Lead WHERE Id IN ('{id_list}')")
        valid_sf_ids.update(r["Id"] for r in results["records"])
        batch_num += 1
        if batch_num % 50 == 0:
            _log_batch_progress(batch_num, total_batches, t0)

    for batch in chunk_list(contact_ids, BATCH_SIZE):
        id_list = "','".join(batch)
        results = sf.query_all(f"SELECT Id FROM Contact WHERE Id IN ('{id_list}')")
        valid_sf_ids.update(r["Id"] for r in results["records"])
        batch_num += 1
        if batch_num % 50 == 0:
            _log_batch_progress(batch_num, total_batches, t0)

    for batch in chunk_list(other_ids, BATCH_SIZE):
        id_list = "','".join(batch)
        for obj in ["Lead", "Contact"]:
            try:
                results = sf.query_all(f"SELECT Id FROM {obj} WHERE Id IN ('{id_list}')")
                valid_sf_ids.update(r["Id"] for r in results["records"])
            except Exception:
                pass
        batch_num += 1
        if batch_num % 50 == 0:
            _log_batch_progress(batch_num, total_batches, t0)

    elapsed = time.monotonic() - t0
    log.info(f"CHECK 1: Validated all {total_batches} batches in {_fmt_duration(elapsed)}")

    # Find orphans (normalize to 15-char comparison)
    valid_sf_ids_15 = {vid[:15] for vid in valid_sf_ids}
    orphans = []
    for sf_id, prospect in sf_id_map.items():
        if sf_id[:15] not in valid_sf_ids_15:
            orphans.append(dict(prospect))

    log.info(f"Found {len(orphans)} Pardot prospects pointing to DELETED CRM records.")
    return orphans


# ── Check 2: SF records pointing to missing Pardot prospects ────────


def find_sf_orphans_missing_pardot(sf, conn) -> list[dict]:
    """
    Leads/Contacts with pi__url__c populated but no matching prospect in cache.
    """
    log.info("CHECK 2: SF records with stale Pardot references")

    # Build email set from cached prospects
    with get_cursor(conn) as cur:
        cur.execute("SELECT LOWER(email) AS email FROM prospects WHERE email IS NOT NULL AND email != ''")
        cached_emails = {row["email"] for row in cur.fetchall()}

    log.info(f"  {len(cached_emails)} unique emails in prospect cache")

    orphans = []
    pardot_id_fields = {"Lead": "pi__url__c", "Contact": "pi__url__c"}

    for obj_type, pardot_field in pardot_id_fields.items():
        log.info(f"Checking {obj_type} records with Pardot references...")

        try:
            query = f"""
                SELECT Id, Email, FirstName, LastName, {pardot_field}
                FROM {obj_type}
                WHERE {pardot_field} != null
            """
            results = sf.query_all(query)
        except Exception as e:
            log.warning(f"Could not query {obj_type}.{pardot_field}: {e}")
            continue

        sf_records = results["records"]
        log.info(f"Found {len(sf_records)} {obj_type} records with Pardot links.")

        for record in sf_records:
            email = record.get("Email")
            if not email:
                continue
            if email.lower().strip() not in cached_emails:
                orphans.append(
                    {
                        "sf_object": obj_type,
                        "sf_id": record["Id"],
                        "email": email,
                        "first_name": record.get("FirstName", ""),
                        "last_name": record.get("LastName", ""),
                        "pardot_field_value": record.get(pardot_field, ""),
                    }
                )

    log.info(f"Found {len(orphans)} SF records pointing to MISSING Pardot prospects.")
    return orphans


# ── Check 3: Unlinked Pardot prospects (no CRM ID at all) ──────────


def find_unlinked_prospects(conn) -> tuple[int, list[dict]]:
    """
    Pardot prospects with no CRM assignment whatsoever.
    Returns (total_count, top_500_by_score).
    """
    log.info("CHECK 3: Pardot prospects with NO CRM link (lost souls)")

    unlinked_filter = """
        WHERE is_deleted = FALSE
          AND (salesforce_id IS NULL OR salesforce_id = '')
          AND (salesforce_lead_id IS NULL OR salesforce_lead_id = '')
          AND (salesforce_contact_id IS NULL OR salesforce_contact_id = '')
    """

    with get_cursor(conn) as cur:
        cur.execute(f"SELECT COUNT(*) AS n FROM prospects {unlinked_filter}")
        total = cur.fetchone()["n"]

        cur.execute(f"""
            SELECT id, email, first_name, last_name, score, created_at
            FROM prospects {unlinked_filter}
            ORDER BY score DESC NULLS LAST
            LIMIT 500
        """)
        top_500 = [dict(row) for row in cur.fetchall()]

    log.info(f"Found {total} Pardot prospects with NO CRM link.")
    return total, top_500


# ── Run all checks ──────────────────────────────────────────────────


def run(sf, conn) -> dict:
    """Run all three orphan checks and store results in orphan_runs."""
    log.info("Pardot <-> Salesforce Orphan Detection")
    log.info("=" * 60)

    pardot_orphans = find_pardot_orphans_missing_crm(sf, conn)
    sf_orphans = find_sf_orphans_missing_pardot(sf, conn)
    unlinked_count, unlinked_top500 = find_unlinked_prospects(conn)

    # Store in orphan_runs (keep first 500 per category for drill-down)
    details = {
        "pardot_orphans": pardot_orphans[:500],
        "sf_orphans": sf_orphans[:500],
        "unlinked": unlinked_top500,
    }

    with get_cursor(conn) as cur:
        cur.execute(
            """
            INSERT INTO orphan_runs (pardot_missing_crm, sf_missing_pardot, unlinked_prospects, details_json)
            VALUES (%s, %s, %s, %s)
        """,
            (len(pardot_orphans), len(sf_orphans), unlinked_count, json.dumps(details, default=str)),
        )

    summary = {
        "pardot_missing_crm": len(pardot_orphans),
        "sf_missing_pardot": len(sf_orphans),
        "unlinked_prospects": unlinked_count,
    }

    print(f"\n{'=' * 60}")
    print("ORPHAN DETECTION SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Pardot -> deleted CRM records:  {summary['pardot_missing_crm']:>6}")
    print(f"  SF -> missing Pardot prospects:  {summary['sf_missing_pardot']:>6}")
    print(f"  Pardot with NO CRM link:        {summary['unlinked_prospects']:>6}")
    print(f"{'=' * 60}")

    return summary
