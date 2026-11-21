import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.rain_alarm_service import RainAlarmService
from app.services.settings_service import settings_manager, normalize_rain_alarm_lead_minutes


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
        self.assertIn("approachingLeadMinutes", data["config"])
        self.assertEqual(data["config"]["approachingLeadMinutes"], 20)
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

    def test_alert_logic_approaching_lead_minutes_filter(self):
        """指定したリードタイム（デフォルト20分）を超える先の雨雲接近はスキップされ、範囲内で通知されることを検証"""
        service = RainAlarmService()
        timeline_50m = [
            {"time": "20:00", "minutesAhead": 0, "rainfall": 0.0, "isObservation": True},
            {"time": "20:10", "minutesAhead": 10, "rainfall": 0.0, "isObservation": False},
            {"time": "20:20", "minutesAhead": 20, "rainfall": 0.0, "isObservation": False},
            {"time": "20:50", "minutesAhead": 50, "rainfall": 2.5, "isObservation": False},
        ]

        # 1. デフォルト(20分)の場合は50分後の雨を通知しない
        with patch.object(service, "fetch_forecast", new_callable=AsyncMock) as mock_fetch, \
             patch("app.services.rain_alarm_service.speech_service.speak", new_callable=AsyncMock) as mock_speak, \
             patch.dict(settings_manager.settings, {"rainAlarm": {
                 "enabled": True, "thresholdMm": 0.5, "heavyThresholdMm": 10.0,
                 "notifyApproaching": True, "approachingLeadMinutes": 20,
                 "notifyHeavy": True, "notifyClearing": True,
                 "cooldownMinutes": 30, "targetScope": "all", "targetDevices": ["ALL"],
                 "chime": "notice_info"
             }}):
            mock_fetch.return_value = (0.0, timeline_50m, "TestProvider")
            res = asyncio.run(service.check_and_notify())
            self.assertEqual(res["status"], "ok")
            self.assertFalse(res["alertTriggered"])
            self.assertIsNone(res["alertType"])
            mock_speak.assert_not_awaited()

        # 2. リードタイムを50分に設定した場合は50分後の雨を通知する
        with patch.object(service, "fetch_forecast", new_callable=AsyncMock) as mock_fetch, \
             patch("app.services.rain_alarm_service.speech_service.speak", new_callable=AsyncMock) as mock_speak, \
             patch.dict(settings_manager.settings, {"rainAlarm": {
                 "enabled": True, "thresholdMm": 0.5, "heavyThresholdMm": 10.0,
                 "notifyApproaching": True, "approachingLeadMinutes": 50,
                 "notifyHeavy": True, "notifyClearing": True,
                 "cooldownMinutes": 30, "targetScope": "all", "targetDevices": ["ALL"],
                 "chime": "notice_info"
             }}):
            mock_fetch.return_value = (0.0, timeline_50m, "TestProvider")
            mock_speak.return_value = {"status": "ok"}
            res = asyncio.run(service.check_and_notify())
            self.assertTrue(res["alertTriggered"])
            self.assertEqual(res["alertType"], "approaching")
            self.assertIn("まもなく約50分後に雨が降り始める見込みです", res["alertMessage"])
            mock_speak.assert_awaited_once()

    def test_alert_logic_heavy_ignores_approaching_lead_minutes(self):
        """案A仕様: approachingLeadMinutes=20 でも、50分後の激しい雨（豪雨警戒）は従来通り通知されることを検証"""
        service = RainAlarmService()
        timeline_heavy_50m = [
            {"time": "20:00", "minutesAhead": 0, "rainfall": 0.0, "isObservation": True},
            {"time": "20:20", "minutesAhead": 20, "rainfall": 0.0, "isObservation": False},
            {"time": "20:50", "minutesAhead": 50, "rainfall": 15.0, "isObservation": False},
        ]

        with patch.object(service, "fetch_forecast", new_callable=AsyncMock) as mock_fetch, \
             patch("app.services.rain_alarm_service.speech_service.speak", new_callable=AsyncMock) as mock_speak, \
             patch.dict(settings_manager.settings, {"rainAlarm": {
                 "enabled": True, "thresholdMm": 0.5, "heavyThresholdMm": 10.0,
                 "notifyApproaching": True, "approachingLeadMinutes": 20,
                 "notifyHeavy": True, "notifyClearing": True,
                 "cooldownMinutes": 30, "targetScope": "all", "targetDevices": ["ALL"],
                 "chime": "notice_info"
             }}):
            mock_fetch.return_value = (0.0, timeline_heavy_50m, "TestProvider")
            mock_speak.return_value = {"status": "ok"}
            res = asyncio.run(service.check_and_notify())
            self.assertTrue(res["alertTriggered"])
            self.assertEqual(res["alertType"], "heavy")
            self.assertIn("約50分後に毎時約15.0ミリの強い雨", res["alertMessage"])
            mock_speak.assert_awaited_once()

    def test_approaching_lead_minutes_normalization_and_settings_api(self):
        """リードタイムのクランプ・異常値フォールバックおよび API 保存反映を検証"""
        self.assertEqual(normalize_rain_alarm_lead_minutes(None), 20)
        self.assertEqual(normalize_rain_alarm_lead_minutes(""), 20)
        self.assertEqual(normalize_rain_alarm_lead_minutes(True), 20)
        self.assertEqual(normalize_rain_alarm_lead_minutes("invalid"), 20)
        self.assertEqual(normalize_rain_alarm_lead_minutes(float("nan")), 20)
        self.assertEqual(normalize_rain_alarm_lead_minutes(2), 5)
        self.assertEqual(normalize_rain_alarm_lead_minutes(120), 60)
        self.assertEqual(normalize_rain_alarm_lead_minutes("15"), 15)

        backup_rain = dict(settings_manager.get().get("rainAlarm", {}))
        backup_disaster = dict(settings_manager.get().get("disaster", {}))
        try:
            with patch.object(settings_manager, "get_admin_password", return_value=""):
                resp = self.client.put("/api/disaster/settings", json={
                    "enabled": True,
                    "rainAlarm": {
                        "enabled": True,
                        "approachingLeadMinutes": 15
                    }
                })
                self.assertEqual(resp.status_code, 200)
                status_resp = self.client.get("/api/rain-alarm/status")
                self.assertEqual(status_resp.status_code, 200)
                self.assertEqual(status_resp.json()["config"]["approachingLeadMinutes"], 15)

                # 範囲外の値は保存時にクランプされること
                resp_clamp = self.client.put("/api/disaster/settings", json={
                    "enabled": True,
                    "rainAlarm": {
                        "enabled": True,
                        "approachingLeadMinutes": 999
                    }
                })
                self.assertEqual(resp_clamp.status_code, 200)
                status_resp2 = self.client.get("/api/rain-alarm/status")
                self.assertEqual(status_resp2.json()["config"]["approachingLeadMinutes"], 60)
        finally:
            settings_manager.update({"rainAlarm": backup_rain, "disaster": backup_disaster})


if __name__ == "__main__":
    import asyncio
    unittest.main()
