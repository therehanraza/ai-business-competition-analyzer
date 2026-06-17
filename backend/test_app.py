import json
import tempfile
import unittest
from pathlib import Path

import app as app_module


class BackendApiTest(unittest.TestCase):
    def setUp(self):
        self.original_gemini_key = app_module.os.environ.pop("GEMINI_API_KEY", None)
        self.tempdir = tempfile.TemporaryDirectory()
        data_path = Path(self.tempdir.name) / "test_data.json"
        app_module.store = app_module.LocalStore(data_path)
        app_module.store_name = "Test Local JSON"
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def tearDown(self):
        if self.original_gemini_key is not None:
            app_module.os.environ["GEMINI_API_KEY"] = self.original_gemini_key
        self.tempdir.cleanup()

    def post_json(self, path, payload=None):
        return self.client.post(path, data=json.dumps(payload or {}), content_type="application/json")

    def put_json(self, path, payload=None):
        return self.client.put(path, data=json.dumps(payload or {}), content_type="application/json")

    def patch_json(self, path, payload=None):
        return self.client.patch(path, data=json.dumps(payload or {}), content_type="application/json")

    def test_health_and_dashboard(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/api/health").json["store"], "Test Local JSON")
        dashboard = self.client.get("/api/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        self.assertGreaterEqual(dashboard.json["metrics"]["tracked_competitors"], 3)

    def test_business_analyzer_returns_ranked_strategy(self):
        payload = {
            "business_name": "Nova Retail AI",
            "category": "Retail Analytics",
            "region": "North America",
            "price": 179,
            "product_score": 82,
            "target_customer": "mid-market retailers",
            "advantage": "faster deployment and simple dashboards",
        }
        response = self.post_json("/api/analyze", payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["business_profile"]["business_name"], "Nova Retail AI")
        self.assertIn("competition_pressure_score", response.json)
        self.assertIn(response.json["threat_level"], ["High", "Medium", "Low"])
        self.assertTrue(response.json["top_threats"])
        self.assertTrue(response.json["swot"]["strengths"])
        self.assertTrue(response.json["action_plan"])

    def test_competitor_crud_and_duplicate_validation(self):
        payload = {
            "name": "Acme Intel",
            "category": "Retail Analytics",
            "region": "North America",
            "current_price": 300,
            "market_share": 12,
        }
        created = self.post_json("/api/competitors", payload)
        self.assertEqual(created.status_code, 201)
        competitor_id = created.json["_id"]
        self.assertEqual(self.post_json("/api/competitors", payload).status_code, 409)

        detail = self.client.get(f"/api/competitors/{competitor_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.json["price_history"])

        updated = self.put_json(f"/api/competitors/{competitor_id}", {"current_price": 250})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["current_price"], 250)
        self.assertEqual(updated.json["previous_price"], 300)

        deleted = self.client.delete(f"/api/competitors/{competitor_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json["deleted"])

    def test_price_crud_validates_competitor_and_syncs_latest_price(self):
        bad = self.post_json("/api/prices", {"competitor_id": "missing", "date": "2026-07", "price": 199})
        self.assertEqual(bad.status_code, 400)

        created = self.post_json("/api/prices", {"competitor_id": "c_marketpulse", "date": "2026-07", "price": 219})
        self.assertEqual(created.status_code, 201)
        price_id = created.json["_id"]
        competitor = self.client.get("/api/competitors/c_marketpulse").json
        self.assertEqual(competitor["current_price"], 219)

        updated = self.put_json(f"/api/prices/{price_id}", {"price": 209})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["price"], 209)

        self.assertEqual(self.client.delete(f"/api/prices/{price_id}").status_code, 200)

    def test_market_signal_crud(self):
        created = self.post_json(
            "/api/market-signals",
            {"area": "Mumbai", "demand": 88, "trend": "Rising", "category": "Retail Analytics"},
        )
        self.assertEqual(created.status_code, 201)
        signal_id = created.json["_id"]
        updated = self.put_json(f"/api/market-signals/{signal_id}", {"demand": 91, "trend": "Stable"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["demand"], 91)
        self.assertEqual(self.client.delete(f"/api/market-signals/{signal_id}").status_code, 200)

    def test_activity_signal_updates_competitor_intelligence(self):
        payload = {
            "competitor_id": "c_marketpulse",
            "type": "Hiring",
            "sentiment": "Positive",
            "summary": "Opened several enterprise sales roles.",
            "impact_score": 78,
            "metric_value": 22,
            "source": "Careers page",
        }
        created = self.post_json("/api/activity-signals", payload)
        self.assertEqual(created.status_code, 201)
        signal_id = created.json["_id"]
        competitor = self.client.get("/api/competitors/c_marketpulse").json
        self.assertEqual(competitor["hiring_activity"], 22)

        intelligence = self.client.get("/api/intelligence")
        self.assertEqual(intelligence.status_code, 200)
        self.assertTrue(intelligence.json["top_watch"])
        self.assertTrue(intelligence.json["auto_alerts"])
        self.assertEqual(self.client.delete(f"/api/activity-signals/{signal_id}").status_code, 200)

    def test_copilot_returns_positioning_answer_without_gemini(self):
        response = self.post_json("/api/copilot", {"question": "Who is the biggest growth threat?"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("answer", response.json)
        self.assertTrue(response.json["bullets"])

    def test_ai_enrichment_and_tracking_flow(self):
        enriched = self.post_json(
            "/api/enrich-competitor",
            {"name": "ChatGPT", "website": "https://chatgpt.com", "region": "India"},
        )
        self.assertEqual(enriched.status_code, 200)
        self.assertEqual(enriched.json["profile"]["name"], "ChatGPT")
        self.assertEqual(enriched.json["profile"]["region"], "India")
        self.assertTrue(enriched.json["insights"])
        self.assertIn("activity_signal", enriched.json)
        plan_names = [plan["name"] for plan in enriched.json["profile"]["pricing_plans"]]
        self.assertIn("Free", plan_names)
        self.assertIn("Plus", plan_names)
        self.assertIn("Enterprise", plan_names)

        tracked = self.post_json("/api/track-competitor", {"enrichment": enriched.json})
        self.assertEqual(tracked.status_code, 201)
        competitor_id = tracked.json["competitor"]["_id"]
        self.assertEqual(tracked.json["competitor"]["name"], "ChatGPT")

        detail = self.client.get(f"/api/competitors/{competitor_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.json["price_history"])

        activity = self.client.get(f"/api/activity-signals?competitor_id={competitor_id}")
        self.assertEqual(activity.status_code, 200)
        self.assertTrue(activity.json)

    def test_alert_status_flow(self):
        created = self.post_json(
            "/api/alerts",
            {"severity": "High", "title": "New launch", "message": "Competitor shipped a new analytics module."},
        )
        self.assertEqual(created.status_code, 201)
        alert_id = created.json["_id"]
        closed = self.patch_json(f"/api/alerts/{alert_id}/status", {"status": "Closed"})
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(closed.json["status"], "Closed")
        self.assertIn("closed_at", closed.json)

    def test_reports_and_export(self):
        created = self.post_json("/api/reports", {"title": "Board Brief"})
        self.assertEqual(created.status_code, 201)
        report_id = created.json["_id"]
        detail = self.client.get(f"/api/reports/{report_id}")
        self.assertEqual(detail.status_code, 200)
        exported = self.client.get(f"/api/reports/{report_id}/export")
        self.assertEqual(exported.status_code, 200)
        self.assertEqual(exported.mimetype, "application/json")

    def test_battlecard_history(self):
        created = self.post_json(
            "/api/battlecards",
            {"competitor_id": "c_pricehawk", "objective": "Defend an active renewal"},
        )
        self.assertEqual(created.status_code, 201)
        card_id = created.json["_id"]
        self.assertEqual(created.json["competitor_name"], "PriceHawk")
        cards = self.client.get("/api/battlecards?competitor_id=c_pricehawk")
        self.assertEqual(cards.status_code, 200)
        self.assertEqual(len(cards.json), 1)
        self.assertEqual(self.client.delete(f"/api/battlecards/{card_id}").status_code, 200)


if __name__ == "__main__":
    unittest.main()
