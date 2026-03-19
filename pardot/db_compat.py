"""
Compatibility layer: provides get_cursor() and field mapping helpers
using Django's database connection instead of raw psycopg2.

This allows the business logic modules (assets.py, engagement.py, scorecard.py,
digest.py, sync.py, orphan_detector.py, config.py) to work with minimal changes.
The `conn` parameter is accepted but ignored — Django manages connections.
"""

import re
from contextlib import contextmanager

from django.db import connection

# Re-export field maps from the original db.py — these are pure data, no DB dependency.

PROSPECT_FIELD_MAP = {
    "id": "id",
    "email": "email",
    "firstName": "first_name",
    "lastName": "last_name",
    "company": "company",
    "score": "score",
    "grade": "grade",
    "campaignId": "campaign_id",
    "salesforceId": "salesforce_id",
    "salesforceLeadId": "salesforce_lead_id",
    "salesforceContactId": "salesforce_contact_id",
    "salesforceAccountId": "salesforce_account_id",
    "optedOut": "opted_out",
    "isDeleted": "is_deleted",
    "lastActivityAt": "last_activity_at",
    "createdAt": "created_at",
    "updatedAt": "updated_at",
}

PROSPECT_FIELD_MAP_REVERSE = {v: k for k, v in PROSPECT_FIELD_MAP.items()}

ACTIVITY_FIELD_MAP = {
    "id": "id",
    "type": "type",
    "typeName": "type_name",
    "prospectId": "prospect_id",
    "campaignId": "campaign_id",
    "formId": "form_id",
    "formHandlerId": "form_handler_id",
    "landingPageId": "landing_page_id",
    "customRedirectId": "custom_redirect_id",
    "emailId": "email_id",
    "createdAt": "created_at",
}


def camel_to_snake(name: str) -> str:
    s1 = re.sub(r"([A-Z])", r"_\1", name)
    return s1.lower().lstrip("_")


def snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def map_prospect(api_record: dict) -> dict:
    row = {}
    for api_key, db_key in PROSPECT_FIELD_MAP.items():
        if api_key in api_record:
            row[db_key] = api_record[api_key]
    return row


def map_activity(api_record: dict) -> dict:
    row = {}
    for api_key, db_key in ACTIVITY_FIELD_MAP.items():
        if api_key in api_record:
            row[db_key] = api_record[api_key]
    return row


class _DictCursorWrapper:
    """Wraps a Django cursor to return dict rows like psycopg2 RealDictCursor."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=None):
        # Remap table names from old standalone schema to Django's camp_ prefixed tables
        sql = _remap_tables(sql)
        return self._cursor.execute(sql, params)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return dict(zip([col[0] for col in self._cursor.description], row))

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        cols = [col[0] for col in self._cursor.description]
        return [dict(zip(cols, row)) for row in rows]

    def close(self):
        self._cursor.close()

    @property
    def description(self):
        return self._cursor.description


# Table name remapping: the standalone app used bare table names,
# but Django models use camp_ prefixed tables.
_TABLE_REMAP = {
    "sync_meta": "pardot_sync_meta",
    "prospects": "pardot_prospects",
    "visitor_activities": "pardot_visitor_activities",
    "campaigns": "pardot_campaigns",
    "lists": "pardot_lists",
    "forms": "pardot_forms",
    "landing_pages": "pardot_landing_pages",
    "list_emails": "pardot_list_emails",
    "custom_redirects": "pardot_custom_redirects",
    "folders": "pardot_folders",
    "sf_health": "pardot_sf_health",
    "orphan_runs": "pardot_orphan_runs",
    "daily_snapshots": "pardot_daily_snapshots",
    "tasks": "pardot_tasks",
    "tags": "pardot_tags",
    "tagged_objects": "pardot_tagged_objects",
    "config": "pardot_config",
    "scoring_categories": "pardot_scoring_categories",
    "campaign_member_counts": "pardot_campaign_member_counts",
    "campaign_members": "pardot_campaign_members",
    "team_members": "pardot_team_members",
}

# Build regex: match standalone table names as whole words, but not if already prefixed
_TABLE_PATTERN = re.compile(
    r"(?<![a-zA-Z_])(" + "|".join(re.escape(k) for k in sorted(_TABLE_REMAP, key=len, reverse=True)) + r")(?![a-zA-Z_])"
)


def _remap_tables(sql: str) -> str:
    """Replace standalone table names with camp_ prefixed names in SQL."""

    def _replace(match):
        name = match.group(1)
        # Don't remap if already prefixed
        start = match.start(1)
        if start >= 5 and sql[start - 5 : start] == "camp_":
            return name
        return _TABLE_REMAP.get(name, name)

    return _TABLE_PATTERN.sub(_replace, sql)


@contextmanager
def get_cursor(conn=None):
    """Context manager yielding a dict cursor using Django's DB connection.

    The `conn` parameter is accepted for API compatibility but ignored.
    Django handles connection lifecycle automatically.
    """
    cursor = connection.cursor()
    wrapped = _DictCursorWrapper(cursor)
    try:
        yield wrapped
    finally:
        cursor.close()


def get_connection():
    """Return Django's database connection wrapper.

    Provided for API compatibility — Django manages connections automatically.
    The returned object has a no-op close() method.
    """

    class _DjangoConnWrapper:
        def close(self):
            pass  # Django manages connection lifecycle

        def commit(self):
            pass  # Django auto-commits by default

        def rollback(self):
            pass

        def cursor(self, cursor_factory=None):
            return _DictCursorWrapper(connection.cursor())

    return _DjangoConnWrapper()
