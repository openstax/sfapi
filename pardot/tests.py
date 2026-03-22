import logging
import uuid
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from ninja.testing import TestClient

from api.models import SuperUser
from pardot import config
from pardot.db_compat import (
    _remap_tables,
    camel_to_snake,
    get_cursor,
    map_activity,
    map_prospect,
    snake_to_camel,
)
from pardot.models import (
    Campaign,
    CampaignMember,
    CampaignMemberCount,
    CampConfig,
    CustomRedirect,
    DailySnapshot,
    Folder,
    Form,
    LandingPage,
    List,
    ListEmail,
    OrphanRun,
    Prospect,
    ScoringCategory,
    SFHealth,
    SyncMeta,
    Tag,
    TaggedObject,
    Task,
    TeamMember,
    VisitorActivity,
)
from pardot.pardot_client import PardotAPIError, PardotClient
from pardot.views import router

logging.disable(logging.CRITICAL)

SUPER_USER_UUID = "f8a6b8b8-32f7-4b4d-b6f9-054ab6fb5623"
NON_SUPER_UUID = str(uuid.uuid4())


def mock_super_user(request):
    return SUPER_USER_UUID


def mock_regular_user(request):
    return NON_SUPER_UUID


# ══════════════════════════════════════════════════════════════
# Models
# ══════════════════════════════════════════════════════════════


class ModelTests(TestCase):
    """Test that all pardot models can be created and have correct str representations."""

    def test_campaign_create(self):
        c = Campaign.objects.create(id=1, name="Test Campaign", cost=100)
        self.assertEqual(str(c), "Test Campaign")
        self.assertEqual(c.cost, 100)

    def test_campaign_str_no_name(self):
        c = Campaign.objects.create(id=2)
        self.assertEqual(str(c), "Campaign 2")

    def test_prospect_create(self):
        p = Prospect.objects.create(id=1001, email="test@example.com", score=75, grade="B")
        self.assertEqual(str(p), "test@example.com")
        self.assertEqual(p.score, 75)

    def test_prospect_str_no_email(self):
        p = Prospect.objects.create(id=1002)
        self.assertEqual(str(p), "Prospect 1002")

    def test_visitor_activity_create(self):
        va = VisitorActivity.objects.create(id=5001, type=1, type_name="Visit", prospect_id=1001)
        self.assertEqual(str(va), "Activity 5001 (Visit)")

    def test_list_create(self):
        lst = List.objects.create(id=10, name="My List", is_dynamic=True)
        self.assertTrue(lst.is_dynamic)
        self.assertEqual(str(lst), "My List")

    def test_form_create(self):
        f = Form.objects.create(id=20, name="Contact Form", campaign_id=1)
        self.assertEqual(str(f), "Contact Form")

    def test_landing_page_create(self):
        lp = LandingPage.objects.create(id=30, name="Promo Page", url="https://example.com")
        self.assertEqual(str(lp), "Promo Page")

    def test_list_email_create(self):
        e = ListEmail.objects.create(id=40, name="Newsletter", subject="Weekly Update", is_sent=True)
        self.assertTrue(e.is_sent)
        self.assertEqual(str(e), "Newsletter")

    def test_custom_redirect_create(self):
        cr = CustomRedirect.objects.create(id=50, name="CTA Link", url="https://example.com/go")
        self.assertEqual(str(cr), "CTA Link")

    def test_folder_create(self):
        f = Folder.objects.create(id=60, name="Assets")
        self.assertEqual(str(f), "Assets")

    def test_sf_health_create(self):
        h = SFHealth.objects.create(
            total_leads=1000, total_contacts=2000, leads_with_pardot=500, contacts_with_pardot=800
        )
        self.assertIn("SF Health", str(h))

    def test_daily_snapshot_create(self):
        ds = DailySnapshot.objects.create(snapshot_date=date.today(), total_campaigns=50, total_forms=20)
        self.assertEqual(str(ds), f"Snapshot {date.today()}")

    def test_task_create(self):
        t = Task.objects.create(assignee="Alice", title="Fix forms", priority="high", status="open")
        self.assertIn("Fix forms", str(t))
        self.assertIn("Alice", str(t))
        self.assertIn("open", str(t))

    def test_tag_create(self):
        t = Tag.objects.create(id=70, name="Region: East", object_count=5)
        self.assertEqual(str(t), "Region: East")

    def test_tagged_object_create(self):
        to = TaggedObject.objects.create(id=80, tag_id=70, object_type="Campaign", object_id=1)
        self.assertEqual(str(to), "Campaign:1")

    def test_sync_meta_create(self):
        sm = SyncMeta.objects.create(entity_type="campaigns", last_sync_mode="incremental", last_sync_count=50)
        self.assertEqual(str(sm), "campaigns")

    def test_orphan_run_create(self):
        o = OrphanRun.objects.create(pardot_missing_crm=10, sf_missing_pardot=5)
        self.assertIn("Orphan Run", str(o))

    def test_scoring_category_create(self):
        sc = ScoringCategory.objects.create(prospect_id=1001, category_name="A", score=10.5)
        self.assertEqual(str(sc), "1001: A = 10.5")

    def test_campaign_member_count_create(self):
        cmc = CampaignMemberCount.objects.create(
            campaign_sf_id="7010000000001", total_members=100, responded_members=25
        )
        self.assertIn("100 members", str(cmc))

    def test_campaign_member_create(self):
        cm = CampaignMember.objects.create(id="00v0000000001", campaign_sf_id="7010000000001", status="Sent")
        self.assertEqual(str(cm), "Member 00v0000000001")

    def test_team_member_create(self):
        tm = TeamMember.objects.create(name="Alice", role="Admin", owns=["campaigns"], sort_order=0)
        self.assertEqual(str(tm), "Alice (Admin)")

    def test_camp_config_create(self):
        cc = CampConfig.objects.create(key="test_key", value={"setting": True})
        self.assertEqual(str(cc), "test_key")


# ══════════════════════════════════════════════════════════════
# DB Compat
# ══════════════════════════════════════════════════════════════


class DBCompatTests(TestCase):
    """Test the db_compat utility functions."""

    def test_camel_to_snake(self):
        self.assertEqual(camel_to_snake("firstName"), "first_name")
        self.assertEqual(camel_to_snake("salesforceId"), "salesforce_id")
        self.assertEqual(camel_to_snake("id"), "id")

    def test_snake_to_camel(self):
        self.assertEqual(snake_to_camel("first_name"), "firstName")
        self.assertEqual(snake_to_camel("salesforce_id"), "salesforceId")
        self.assertEqual(snake_to_camel("id"), "id")

    def test_map_prospect(self):
        api_record = {
            "id": 123,
            "email": "test@example.com",
            "firstName": "Test",
            "lastName": "User",
            "score": 80,
            "unknownField": "ignored",
        }
        result = map_prospect(api_record)
        self.assertEqual(result["id"], 123)
        self.assertEqual(result["email"], "test@example.com")
        self.assertEqual(result["first_name"], "Test")
        self.assertEqual(result["score"], 80)
        self.assertNotIn("unknownField", result)
        self.assertNotIn("unknown_field", result)

    def test_map_activity(self):
        api_record = {
            "id": 456,
            "type": 1,
            "typeName": "Visit",
            "prospectId": 123,
            "createdAt": "2026-01-01T00:00:00Z",
        }
        result = map_activity(api_record)
        self.assertEqual(result["id"], 456)
        self.assertEqual(result["type_name"], "Visit")
        self.assertEqual(result["prospect_id"], 123)

    def test_remap_tables(self):
        self.assertEqual(_remap_tables("SELECT * FROM campaigns"), "SELECT * FROM pardot_campaigns")
        self.assertEqual(
            _remap_tables("SELECT * FROM prospects WHERE id = 1"), "SELECT * FROM pardot_prospects WHERE id = 1"
        )
        # Already-prefixed tables should not be double-remapped
        self.assertEqual(_remap_tables("SELECT * FROM pardot_campaigns"), "SELECT * FROM pardot_campaigns")

    def test_get_cursor_dict_rows(self):
        """Cursor should return dict rows."""
        Campaign.objects.create(id=99, name="Cursor Test")
        with get_cursor() as cur:
            cur.execute("SELECT id, name FROM pardot_campaigns WHERE id = 99")
            row = cur.fetchone()
        self.assertIsInstance(row, dict)
        self.assertEqual(row["id"], 99)
        self.assertEqual(row["name"], "Cursor Test")

    def test_get_cursor_fetchall(self):
        Campaign.objects.create(id=97, name="A")
        Campaign.objects.create(id=98, name="B")
        with get_cursor() as cur:
            cur.execute("SELECT id, name FROM pardot_campaigns WHERE id IN (97, 98) ORDER BY id")
            rows = cur.fetchall()
        self.assertEqual(len(rows), 2)
        self.assertIsInstance(rows[0], dict)

    def test_get_cursor_fetchone_empty(self):
        with get_cursor() as cur:
            cur.execute("SELECT * FROM pardot_campaigns WHERE id = -1")
            row = cur.fetchone()
        self.assertIsNone(row)


# ══════════════════════════════════════════════════════════════
# Config
# ══════════════════════════════════════════════════════════════


class ConfigTests(TestCase):
    """Test config module defaults and DB overrides."""

    def setUp(self):
        config.invalidate_cache()

    def test_default_team(self):
        team = config.get_team(None)
        self.assertIsInstance(team, list)
        self.assertTrue(len(team) > 0)
        self.assertIn("name", team[0])

    def test_team_from_db(self):
        TeamMember.objects.create(name="TestUser", role="Tester", owns=["forms"], sort_order=0)
        config.invalidate_cache()
        team = config.get_team(None)
        self.assertEqual(len(team), 1)
        self.assertEqual(team[0]["name"], "TestUser")

    def test_default_demerits(self):
        demerits = config.get_demerits(None)
        self.assertIn("campaigns_no_sf", demerits)
        self.assertIsInstance(demerits["campaigns_no_sf"], float)

    def test_default_camp_dates(self):
        start, end = config.get_camp_dates(None)
        self.assertIsInstance(start, date)
        self.assertIsInstance(end, date)
        self.assertLessEqual(start, end)

    def test_camp_dates_from_db(self):
        CampConfig.objects.create(key="camp_start", value="2026-06-01")
        CampConfig.objects.create(key="camp_end", value="2026-06-30")
        config.invalidate_cache()
        start, end = config.get_camp_dates(None)
        self.assertEqual(start, date(2026, 6, 1))
        self.assertEqual(end, date(2026, 6, 30))

    def test_default_grade_thresholds(self):
        grades = config.get_grade_map(None)
        self.assertIsInstance(grades, list)
        self.assertEqual(grades[0], (90, "A"))

    def test_default_activity_lookback(self):
        days = config.get_activity_lookback_days(None)
        self.assertEqual(days, 30)

    def test_default_cleanup_config(self):
        cfg = config.get_cleanup_config(None)
        self.assertIn("prefix", cfg)
        self.assertIn("actions", cfg)

    def test_get_all_config(self):
        result = config.get_all_config(None)
        self.assertIn("demerits", result)
        self.assertIn("camp_start", result)
        self.assertIn("grade_thresholds", result)

    def test_cache_invalidation(self):
        """Config cache should be cleared after invalidate_cache()."""
        config.get_team(None)  # populate cache
        self.assertIn("team", config._cache)
        config.invalidate_cache()
        self.assertEqual(len(config._cache), 0)


# ══════════════════════════════════════════════════════════════
# PardotClient
# ══════════════════════════════════════════════════════════════


class PardotClientTests(TestCase):
    """Test PardotClient methods with mocked HTTP."""

    def setUp(self):
        self.client = PardotClient.__new__(PardotClient)
        self.client.business_unit_id = "test_bu_id"
        self.client.session = MagicMock()

    @patch("pardot.pardot_client._get_sf_token", return_value="fake_token")
    def test_get_success(self, mock_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"values": []}'
        mock_resp.json.return_value = {"values": []}
        self.client.session.request.return_value = mock_resp

        result = self.client.get("objects/campaigns")
        self.assertEqual(result, {"values": []})

    @patch("pardot.pardot_client._get_sf_token", return_value="fake_token")
    def test_get_204_returns_empty(self, mock_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        self.client.session.request.return_value = mock_resp

        result = self.client.get("objects/campaigns/1")
        self.assertEqual(result, {})

    @patch("pardot.pardot_client._get_sf_token", return_value="fake_token")
    def test_get_raises_on_error(self, mock_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        self.client.session.request.return_value = mock_resp

        with self.assertRaises(PardotAPIError) as ctx:
            self.client.get("objects/campaigns")
        self.assertEqual(ctx.exception.status_code, 500)

    @patch("pardot.pardot_client._get_sf_token", return_value="fake_token")
    def test_get_all_pagination(self, mock_token):
        page1_resp = MagicMock()
        page1_resp.status_code = 200
        page1_resp.content = b"data"
        page1_resp.json.return_value = {"values": [{"id": 1}, {"id": 2}], "nextPageToken": "abc"}

        page2_resp = MagicMock()
        page2_resp.status_code = 200
        page2_resp.content = b"data"
        page2_resp.json.return_value = {"values": [{"id": 3}]}

        self.client.session.request.side_effect = [page1_resp, page2_resp]

        results = list(self.client.get_all("objects/campaigns", page_size=2))
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["id"], 1)
        self.assertEqual(results[2]["id"], 3)

    @patch("pardot.pardot_client._get_sf_token", return_value="fake_token")
    def test_post_success(self, mock_token):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.content = b'{"id": 1}'
        mock_resp.json.return_value = {"id": 1}
        self.client.session.request.return_value = mock_resp

        result = self.client.post("objects/tags", json_body={"name": "test"})
        self.assertEqual(result["id"], 1)

    def test_pardot_api_error_str(self):
        err = PardotAPIError(404, "Not Found")
        self.assertIn("404", str(err))
        self.assertIn("Not Found", str(err))


# ══════════════════════════════════════════════════════════════
# API Endpoints
# ══════════════════════════════════════════════════════════════


class PardotAPIBaseTest(TestCase):
    """Base class for pardot API endpoint tests."""

    def setUp(self):
        self.client = TestClient(router)
        self.super_user = SuperUser.objects.create(
            accounts_uuid=SUPER_USER_UUID,
            name="Test Super",
            is_active=True,
        )
        config.invalidate_cache()


class AuthorizationTests(PardotAPIBaseTest):
    """Test that all endpoints require SuperUser auth."""

    def test_no_auth_returns_401(self):
        response = self.client.get("/sf-health")
        self.assertEqual(response.status_code, 401)

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_regular_user)
    def test_non_super_user_returns_403(self, mock_auth):
        response = self.client.get("/sf-health")
        self.assertEqual(response.status_code, 403)


class SFHealthEndpointTests(PardotAPIBaseTest):
    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_sf_health_empty(self, mock_auth):
        response = self.client.get("/sf-health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_sf_health_with_data(self, mock_auth):
        SFHealth.objects.create(total_leads=1000, total_contacts=2000, leads_with_pardot=500, contacts_with_pardot=800)
        response = self.client.get("/sf-health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_leads"], 1000)
        self.assertEqual(data["contacts_with_pardot"], 800)


class TaskEndpointTests(PardotAPIBaseTest):
    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_list_tasks_empty(self, mock_auth):
        response = self.client.get("/tasks")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_create_task_missing_fields(self, mock_auth):
        response = self.client.post("/tasks", json={"title": "No assignee"})
        self.assertEqual(response.status_code, 400)

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_create_task_missing_title(self, mock_auth):
        response = self.client.post("/tasks", json={"assignee": "Alice"})
        self.assertEqual(response.status_code, 400)

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_update_task(self, mock_auth):
        task = Task.objects.create(assignee="Alice", title="Fix it", status="open")
        response = self.client.patch(f"/tasks/{task.id}", json={"status": "done"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "done")
        self.assertIsNotNone(data["completed_at"])

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_update_task_not_found(self, mock_auth):
        response = self.client.patch("/tasks/99999", json={"status": "done"})
        self.assertEqual(response.status_code, 404)

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_update_task_no_fields(self, mock_auth):
        task = Task.objects.create(assignee="Alice", title="Fix it")
        response = self.client.patch(f"/tasks/{task.id}", json={"invalid_field": "value"})
        self.assertEqual(response.status_code, 400)

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_delete_task(self, mock_auth):
        task = Task.objects.create(assignee="Alice", title="Delete me")
        response = self.client.delete(f"/tasks/{task.id}")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.filter(id=task.id).exists())

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_filter_tasks_by_status(self, mock_auth):
        Task.objects.create(assignee="Alice", title="Open task", status="open")
        Task.objects.create(assignee="Alice", title="Done task", status="done")
        response = self.client.get("/tasks?status=open")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["status"], "open")

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_filter_tasks_by_assignee(self, mock_auth):
        Task.objects.create(assignee="Alice", title="Alice's task")
        Task.objects.create(assignee="Bob", title="Bob's task")
        response = self.client.get("/tasks?assignee=Alice")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["assignee"], "Alice")


class TrailEndpointTests(PardotAPIBaseTest):
    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_trail_empty(self, mock_auth):
        response = self.client.get("/trail")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_trail_with_snapshots(self, mock_auth):
        DailySnapshot.objects.create(snapshot_date=date.today() - timedelta(days=1), total_campaigns=40)
        DailySnapshot.objects.create(snapshot_date=date.today(), total_campaigns=50)
        response = self.client.get("/trail")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)


class OrphansEndpointTests(PardotAPIBaseTest):
    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_orphans_empty(self, mock_auth):
        response = self.client.get("/orphans")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data["run"])

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_orphans_with_data(self, mock_auth):
        OrphanRun.objects.create(pardot_missing_crm=10, sf_missing_pardot=5)
        response = self.client.get("/orphans")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNotNone(data["run"])
        self.assertEqual(data["run"]["pardot_missing_crm"], 10)

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_orphans_history(self, mock_auth):
        OrphanRun.objects.create(pardot_missing_crm=10, sf_missing_pardot=5)
        response = self.client.get("/orphans/history")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)


class SyncStatusEndpointTests(PardotAPIBaseTest):
    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_sync_status_empty(self, mock_auth):
        response = self.client.get("/sync/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_sync_status_with_data(self, mock_auth):
        SyncMeta.objects.create(entity_type="campaigns", last_sync_mode="full", last_sync_count=50)
        response = self.client.get("/sync/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["entity_type"], "campaigns")


class AdminConfigEndpointTests(PardotAPIBaseTest):
    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_get_config(self, mock_auth):
        response = self.client.get("/admin/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("demerits", data)

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_put_config_valid_key(self, mock_auth):
        response = self.client.put("/admin/config/camp_start", json={"value": "2026-07-01"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        # Verify it was saved
        config.invalidate_cache()
        start, _ = config.get_camp_dates(None)
        self.assertEqual(start, date(2026, 7, 1))

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_put_config_invalid_key(self, mock_auth):
        response = self.client.put("/admin/config/invalid_key", json={"value": "test"})
        self.assertEqual(response.status_code, 400)

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_delete_config(self, mock_auth):
        CampConfig.objects.create(key="camp_start", value="2026-07-01")
        response = self.client.delete("/admin/config/camp_start")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["reset"])


class AdminTeamEndpointTests(PardotAPIBaseTest):
    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_get_team(self, mock_auth):
        response = self.client.get("/admin/team")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_put_team(self, mock_auth):
        team_data = [
            {"name": "Alice", "role": "Admin", "owns": [], "label": "All campaigns"},
            {"name": "Bob", "role": "Marketing", "owns": [], "label": "Forms"},
        ]
        response = self.client.put("/admin/team", json=team_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(TeamMember.objects.count(), 2)

    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    def test_put_team_invalid_data(self, mock_auth):
        response = self.client.put("/admin/team", json={"not": "a list"})
        self.assertEqual(response.status_code, 400)


class ConfigEndpointTests(PardotAPIBaseTest):
    @patch("api.auth.get_logged_in_user_uuid", side_effect=mock_super_user)
    @patch("pardot.views._sf_instance_url", return_value="https://test.salesforce.com")
    def test_get_config(self, mock_sf, mock_auth):
        response = self.client.get("/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["sf_instance_url"], "https://test.salesforce.com")
        self.assertIn("team", data)


# ══════════════════════════════════════════════════════════════
# Sync Engine
# ══════════════════════════════════════════════════════════════


class SyncEngineTests(TestCase):
    """Test SyncEngine utility methods with real DB."""

    def test_get_sync_status_empty(self):
        from pardot.sync import SyncEngine

        result = SyncEngine.get_sync_status(None)
        self.assertEqual(result, [])

    def test_get_sync_status_with_data(self):
        from pardot.sync import SyncEngine

        SyncMeta.objects.create(entity_type="campaigns", last_sync_mode="full", last_sync_count=100)
        SyncMeta.objects.create(entity_type="forms", last_sync_mode="incremental", last_sync_count=50)
        result = SyncEngine.get_sync_status(None)
        self.assertEqual(len(result), 2)

    def test_upsert_batch_insert_and_update(self):
        """Test that _upsert_batch can insert and update rows."""
        from pardot.sync import SyncEngine

        client = MagicMock()
        engine = SyncEngine(client, None)

        # Insert
        engine._upsert_batch(
            "campaigns",
            [
                {"id": 1, "name": "Campaign A"},
                {"id": 2, "name": "Campaign B"},
            ],
        )
        self.assertEqual(Campaign.objects.count(), 2)
        self.assertEqual(Campaign.objects.get(id=1).name, "Campaign A")

        # Update
        engine._upsert_batch(
            "campaigns",
            [
                {"id": 1, "name": "Updated Campaign A"},
            ],
        )
        self.assertEqual(Campaign.objects.get(id=1).name, "Updated Campaign A")
        # cached_at should be set
        self.assertIsNotNone(Campaign.objects.get(id=1).cached_at)

    def test_upsert_batch_empty(self):
        """Empty batch should be a no-op."""
        from pardot.sync import SyncEngine

        client = MagicMock()
        engine = SyncEngine(client, None)
        engine._upsert_batch("campaigns", [])
        self.assertEqual(Campaign.objects.count(), 0)

    def test_entity_aliases(self):
        from pardot.sync import SyncEngine

        self.assertEqual(SyncEngine.ENTITY_ALIASES["emails"], "list_emails")
        self.assertEqual(SyncEngine.ENTITY_ALIASES["lps"], "landing_pages")
        self.assertEqual(SyncEngine.ENTITY_ALIASES["redirects"], "custom_redirects")

    def test_entity_groups(self):
        from pardot.sync import SyncEngine

        self.assertIn("assets", SyncEngine.ENTITY_GROUPS)
        self.assertIn("campaigns", SyncEngine.ENTITY_GROUPS["assets"])
        self.assertIn("forms", SyncEngine.ENTITY_GROUPS["assets"])
