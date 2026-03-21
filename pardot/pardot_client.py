"""
Pardot API v5 client adapted for Django.

Reuses the existing django-salesforce connection for auth — no separate
client ID, username, or private key needed.  The only Pardot-specific
setting is SALESFORCE_PARDOT_BUSINESS_UNIT (required by the Pardot API header).

For SOQL queries, use ``get_sf_client()`` which also piggybacks on the
same django-salesforce connection.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Generator

import requests
from django.conf import settings

log = logging.getLogger("camp.pardot_client")


def _get_sf_token() -> str:
    """Get a fresh access token from the existing django-salesforce connection."""
    from django.db import connections

    sf_conn = connections["salesforce"]
    sf_conn.ensure_connection()
    token = sf_conn.sf_session.auth.get_token()
    log.debug("Obtained SF access token (length=%d)", len(token) if token else 0)
    return token


def _get_sf_instance_url() -> str:
    """Get the instance URL from the existing django-salesforce connection."""
    from django.db import connections

    sf_conn = connections["salesforce"]
    sf_conn.ensure_connection()
    instance_url = sf_conn.sf_session.auth.instance_url
    log.debug("SF instance URL: %s", instance_url)
    return instance_url


class PardotAPIError(Exception):
    def __init__(self, status_code: int, message: str, response: dict | None = None):
        self.status_code = status_code
        self.response = response or {}
        super().__init__(f"HTTP {status_code}: {message}")


class PardotClient:
    API_BASE = "https://pi.pardot.com/api/v5"
    RATE_LIMIT_WAIT = 60
    PAGINATION_CEILING = 99_000

    def __init__(self):
        self.business_unit_id = getattr(settings, "SALESFORCE_PARDOT_BUSINESS_UNIT", "")
        self.session = requests.Session()

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {_get_sf_token()}",
            "Pardot-Business-Unit-Id": self.business_unit_id,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, params=None, json_body=None, retries=3) -> dict:
        url = f"{self.API_BASE}/{endpoint}"
        auth_retries = 0
        for attempt in range(retries):
            try:
                resp = self.session.request(
                    method,
                    url,
                    headers=self._headers,
                    params=params,
                    json=json_body,
                    timeout=60,
                )
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as exc:
                wait = 10 * (attempt + 1)
                log.warning(
                    f"{type(exc).__name__} on {endpoint} (attempt {attempt + 1}/{retries}). Retrying in {wait}s..."
                )
                time.sleep(wait)
                continue

            if resp.status_code in (200, 201):
                return resp.json() if resp.content else {}
            elif resp.status_code == 204:
                return {}
            elif resp.status_code == 429:
                wait = self.RATE_LIMIT_WAIT * (attempt + 1)
                log.warning(f"Rate limited. Backing off {wait}s")
                time.sleep(wait)
            elif resp.status_code == 401:
                auth_retries += 1
                if auth_retries > 2:
                    raise PardotAPIError(401, "Max auth retries exceeded.")
                # Token may have expired — next iteration will fetch a fresh one
                log.info("Got 401, will retry with fresh token.")
            else:
                raise PardotAPIError(resp.status_code, resp.text)
        raise PardotAPIError(429, f"Max retries exceeded on {endpoint}.")

    def get(self, endpoint, params=None):
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint, json_body=None):
        return self._request("POST", endpoint, json_body=json_body)

    def delete(self, endpoint):
        return self._request("DELETE", endpoint)

    def get_all(self, endpoint, params=None, page_size=200) -> Generator[dict, None, None]:
        params = dict(params or {})
        params["limit"] = page_size
        next_page_token = None
        while True:
            if next_page_token:
                page_params = {"nextPageToken": next_page_token}
                if "fields" in params:
                    page_params["fields"] = params["fields"]
            else:
                page_params = params
            data = self.get(endpoint, params=page_params)
            values = data.get("values", [])
            if not values:
                break
            yield from values
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

    def get_all_windowed(
        self,
        endpoint,
        params=None,
        date_field="createdAt",
        start_date=None,
        end_date=None,
        window_days=90,
        page_size=200,
    ) -> Generator[dict, None, None]:
        params = dict(params or {})
        start = start_date or datetime(2007, 1, 1, tzinfo=timezone.utc)
        end = end_date or datetime.now(timezone.utc) + timedelta(days=1)
        after_key = f"{date_field}After"
        before_key = f"{date_field}Before"
        seen_ids: set[int] = set()
        total = 0
        current = start
        while current < end:
            window_end = min(current + timedelta(days=window_days), end)
            window_params = dict(params)
            window_params[after_key] = current.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            window_params[before_key] = window_end.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            window_count = 0
            for record in self.get_all(endpoint, params=window_params, page_size=page_size):
                rec_id = record.get("id")
                if rec_id is not None and rec_id in seen_ids:
                    continue
                if rec_id is not None:
                    seen_ids.add(rec_id)
                yield record
                window_count += 1
                total += 1
            if window_count >= self.PAGINATION_CEILING:
                log.warning(f"Window {current.date()} to {window_end.date()} near 100k ceiling.")
            elif window_count > 0:
                log.info(f"Window {current.date()} to {window_end.date()}: {window_count} records")
            current = window_end

    # Convenience methods
    def get_prospects(self, **filters):
        return self.get_all("objects/prospects", params=filters)

    def get_campaigns(self, **filters):
        return self.get_all("objects/campaigns", params=filters)

    def get_lists(self, **filters):
        return self.get_all("objects/lists", params=filters)

    def get_forms(self, **filters):
        return self.get_all("objects/forms", params=filters)

    def get_landing_pages(self, **filters):
        return self.get_all("objects/landing-pages", params=filters)

    def get_list_emails(self, **filters):
        return self.get_all("objects/list-emails", params=filters)

    def get_custom_redirects(self, **filters):
        return self.get_all("objects/custom-redirects", params=filters)

    def get_folders(self, **filters):
        return self.get_all("objects/folders", params=filters)

    def get_tags(self, **filters):
        return self.get_all("objects/tags", params=filters)

    def get_tagged_objects(self, **filters):
        return self.get_all("objects/tagged-objects", params=filters)

    def create_tag(self, name: str) -> dict:
        return self.post("objects/tags", json_body={"name": name})

    def create_tagged_object(self, tag_id, object_type, object_id):
        return self.post(
            "objects/tagged-objects",
            json_body={
                "tagId": tag_id,
                "objectType": object_type,
                "objectId": object_id,
            },
        )

    def delete_tagged_object(self, tagged_object_id):
        return self.delete(f"objects/tagged-objects/{tagged_object_id}")


def get_sf_client():
    """Get a simple-salesforce client using the django-salesforce connection's session."""
    from django.db import connections
    from simple_salesforce import Salesforce

    sf_conn = connections["salesforce"]
    sf_conn.ensure_connection()
    sf_session = sf_conn.sf_session
    instance_url = sf_session.auth.instance_url

    log.debug("Creating simple-salesforce client for %s", instance_url)
    return Salesforce(instance_url=instance_url, session_id=sf_session.auth.get_token())
