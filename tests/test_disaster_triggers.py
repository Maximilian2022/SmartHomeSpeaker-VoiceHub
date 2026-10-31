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

    def test_eew_min_scale_filtering(self):
        """EEW受信時の予想震度フィルタリング (eewMinScale) の動作を検証"""
        spoken_messages = []
        async def mock_speak(text, urgent=False, volume=None):
            spoken_messages.append(text)

        disaster_service.speak = mock_speak

        # 設定: 東京都、local、eewMinScale=30 (震度3以上)
        settings = {
            "enabled": True,
            "area": {"prefName": "東京都"},
            "earthquake": {
                "enabled": True,
                "eewEnabled": True,
                "targetScope": "local",
                "eewMinScale": 30
            }
        }

        # ケース1: 東京の予想震度が20 (震度2) -> 発報されないこと
        data_low = {
            "code": 556,
            "id": "eew_test_low_001",
            "cancelled": False,
            "areas": [
                {"name": "東京都２３区", "pref": "東京", "scaleFrom": 10, "scaleTo": 20},
                {"name": "千葉県北東部", "pref": "千葉", "scaleFrom": 40, "scaleTo": 50}
            ]
        }
        spoken_messages.clear()
        asyncio.run(disaster_service._handle_p2p_message(data_low))
        self.assertEqual(len(spoken_messages), 0, "震度2以下の東京は発報されないこと")

        # ケース2: 東京の予想震度が40 (震度4) -> 発報されること
        data_high = {
            "code": 556,
            "id": "eew_test_high_002",
            "cancelled": False,
            "areas": [
                {"name": "東京都２３区", "pref": "東京", "scaleFrom": 30, "scaleTo": 40},
                {"name": "千葉県北東部", "pref": "千葉", "scaleFrom": 40, "scaleTo": 50}
            ]
        }
        spoken_messages.clear()
        asyncio.run(disaster_service._handle_p2p_message(data_high))
        self.assertEqual(len(spoken_messages), 1, "震度4の東京は発報されること")
        self.assertIn("緊急地震速報", spoken_messages[0])


if __name__ == "__main__":
    unittest.main()
