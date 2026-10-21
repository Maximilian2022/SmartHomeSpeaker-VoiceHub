import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.rain_alarm_service import RainAlarmService
from app.services.settings_service import settings_manager


class TestRainAlarm(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_status_endpoint(self):
        """GET /api/rain-alarm/status が200を返し初期設定を含むことを検証"""
        resp = self.client.get("/api/rain-alarm/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("config", data)
        self.assertIn("state", data)
        self.assertIn("latitude", data["config"])
        self.assertIn("longitude", data["config"])
        self.assertIn("notifyApproaching", data["config"])
        self.assertIn("notifyHeavy", data["config"])
        self.assertIn("notifyClearing", data["config"])

    def test_radar_time_endpoint(self):
        """GET /api/rain-alarm/radar-time が配列を含む形式で返ることを検証"""
        with patch.object(
            RainAlarmService,
            "get_jma_radar_times",
            new_callable=AsyncMock
        ) as mock_jma:
            mock_jma.return_value = [{"basetime": "20261021195000", "validtime": "20261021200000"}]
            resp = self.client.get("/api/rain-alarm/radar-time")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertIn("times", data)
            self.assertEqual(len(data["times"]), 1)
            self.assertEqual(data["times"][0]["basetime"], "20261021195000")

    def test_test_alert_endpoint(self):
        """POST /api/rain-alarm/test がテスト発声を実行し200を返すことを検証"""
        with patch("app.services.rain_alarm_service.speech_service.speak", new_callable=AsyncMock) as mock_speak:
            mock_speak.return_value = {"status": "ok"}
            resp = self.client.post("/api/rain-alarm/test", json={"alertType": "approaching"})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["alertType"], "approaching")
            self.assertIn("雨雲接近テスト", data["message"])
            mock_speak.assert_awaited_once()

    def test_alert_logic_approaching(self):
        """雨雲接近・降り始めが正しく検知されることを単体検証"""
        service = RainAlarmService()
        dummy_timeline = [
            {"time": "20:00", "minutesAhead": 0, "rainfall": 0.0, "isObservation": True},
            {"time": "20:10", "minutesAhead": 10, "rainfall": 0.0, "isObservation": False},
            {"time": "20:20", "minutesAhead": 20, "rainfall": 2.5, "isObservation": False},
        ]

        with patch.object(service, "fetch_forecast", new_callable=AsyncMock) as mock_fetch, \
             patch("app.services.rain_alarm_service.speech_service.speak", new_callable=AsyncMock) as mock_speak, \
             patch.dict(settings_manager.settings, {"rainAlarm": {
                 "enabled": True, "thresholdMm": 0.5, "heavyThresholdMm": 10.0,
                 "notifyApproaching": True, "notifyHeavy": True, "notifyClearing": True,
                 "cooldownMinutes": 30, "targetScope": "all", "targetDevices": ["ALL"],
                 "chime": "notice_info"
             }}):

            mock_fetch.return_value = (0.0, dummy_timeline, "TestProvider")
            mock_speak.return_value = {"status": "ok"}

            res = asyncio.run(service.check_and_notify())
            self.assertEqual(res["status"], "ok")
            self.assertTrue(res["alertTriggered"])
            self.assertEqual(res["alertType"], "approaching")
            self.assertIn("まもなく約20分後に雨が降り始める見込みです", res["alertMessage"])
            mock_speak.assert_awaited_once()

    def test_alert_logic_heavy(self):
        """豪雨・強い雨が正しく優先検知されることを単体検証"""
        service = RainAlarmService()
        dummy_timeline = [
            {"time": "20:00", "minutesAhead": 0, "rainfall": 0.0, "isObservation": True},
            {"time": "20:10", "minutesAhead": 10, "rainfall": 15.0, "isObservation": False},
        ]

        with patch.object(service, "fetch_forecast", new_callable=AsyncMock) as mock_fetch, \
             patch("app.services.rain_alarm_service.speech_service.speak", new_callable=AsyncMock) as mock_speak, \
             patch.dict(settings_manager.settings, {"rainAlarm": {
                 "enabled": True, "thresholdMm": 0.5, "heavyThresholdMm": 10.0,
                 "notifyApproaching": True, "notifyHeavy": True, "notifyClearing": True,
                 "cooldownMinutes": 30, "targetScope": "all", "targetDevices": ["ALL"],
                 "chime": "notice_info"
             }}):

            mock_fetch.return_value = (0.0, dummy_timeline, "TestProvider")
            mock_speak.return_value = {"status": "ok"}

            res = asyncio.run(service.check_and_notify())
            self.assertEqual(res["status"], "ok")
            self.assertTrue(res["alertTriggered"])
            self.assertEqual(res["alertType"], "heavy")
            self.assertIn("大雨警戒", res["alertMessage"])
            mock_speak.assert_awaited_once()


if __name__ == "__main__":
    import asyncio
    unittest.main()
