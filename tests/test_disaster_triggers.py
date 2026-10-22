import unittest
import json
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.services.disaster_service import disaster_service
from app.services.rain_alarm_service import rain_alarm_service
from app.services.mqtt_service import mqtt_service


class TestDisasterTriggers(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_disaster_triggers_endpoint(self):
        """GET /api/disaster/triggers が正常に応答し、3つのトリガー状態を含むことを検証"""
        res = self.client.get("/api/disaster/triggers")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("eew", data)
        self.assertIn("warning", data)
        self.assertIn("rain", data)
        self.assertIn("active", data["eew"])
        self.assertIn("active", data["warning"])
        self.assertIn("active", data["rain"])

    def test_test_disaster_trigger_eew(self):
        """POST /api/disaster/triggers/test で EEW をテスト発動できることを検証"""
        res = self.client.post("/api/disaster/triggers/test", json={"target": "eew", "duration": 5})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("target"), "eew")

        status_res = self.client.get("/api/disaster/triggers")
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.json()
        self.assertTrue(status_data["eew"]["active"])

    def test_test_disaster_trigger_warning(self):
        """POST /api/disaster/triggers/test で気象警報をテスト発動できることを検証"""
        res = self.client.post("/api/disaster/triggers/test", json={"target": "warning", "duration": 5})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("target"), "warning")

        status_res = self.client.get("/api/disaster/triggers")
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.json()
        self.assertTrue(status_data["warning"]["active"])

    def test_test_disaster_trigger_rain(self):
        """POST /api/disaster/triggers/test で雨雲接近をテスト発動できることを検証"""
        res = self.client.post("/api/disaster/triggers/test", json={"target": "rain", "duration": 5})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("target"), "rain")

        status_res = self.client.get("/api/disaster/triggers")
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.json()
        self.assertTrue(status_data["rain"]["active"])

    def test_mqtt_publish_disaster_state_safe(self):
        """MQTT ブローカー未接続時でも publish_disaster_state が例外を投げず安全に終了することを検証"""
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(mqtt_service.publish_disaster_state("eew", True, {"test": True}))
            loop.run_until_complete(mqtt_service.publish_disaster_state("warning", False))
            loop.run_until_complete(mqtt_service.publish_disaster_state("rain", True))
        finally:
            loop.close()

    def test_locales_symmetry_for_disaster_triggers(self):
        """ja.json と en.json の settingsDisaster トリガー関連キーが完全に対称であることを検証"""
        with open("public/locales/ja.json", "r", encoding="utf-8") as f:
            ja = json.load(f).get("settingsDisaster", {})
        with open("public/locales/en.json", "r", encoding="utf-8") as f:
            en = json.load(f).get("settingsDisaster", {})

        check_keys = [
            "triggerTitle",
            "triggerSub",
            "triggerDesc",
            "triggerEewName",
            "triggerEewDesc",
            "triggerWarnName",
            "triggerWarnDesc",
            "triggerRainName",
            "triggerRainDesc",
            "btnTriggerTest10s"
        ]

        for k in check_keys:
            self.assertIn(k, ja, f"Missing key in ja.json: {k}")
            self.assertIn(k, en, f"Missing key in en.json: {k}")
            self.assertTrue(len(ja[k]) > 0)
            self.assertTrue(len(en[k]) > 0)


if __name__ == "__main__":
    unittest.main()
