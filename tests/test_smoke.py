import asyncio
import unittest
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from app.core.security import is_tunnel_request, validate_webhook_token
from app.services.tts_service import tts_service
from app.services.calendar_service import calendar_service
from app.services.dnd_service import dnd_service


class TestSmokeVoiceHub(unittest.TestCase):
    """Voice Hub 軽量スモークテストスイート (外部依存なし・高速検証)"""

    def test_security_tunnel_detection(self):
        """外部トンネル経由 (cf-connecting-ip等) の判定検証"""
        # 1. 宅内直接アクセス
        req_local = MagicMock()
        req_local.headers = {}
        req_local.client.host = "192.168.1.100"
        self.assertFalse(is_tunnel_request(req_local))

        # 2. Cloudflare Tunnel 経由
        req_tunnel = MagicMock()
        req_tunnel.headers = {"cf-connecting-ip": "203.0.113.195"}
        req_tunnel.client.host = "127.0.0.1"
        self.assertTrue(is_tunnel_request(req_tunnel))

    def test_security_tunnel_token_enforcement(self):
        """外部トンネル経由時のトークン認証強制検証 (宅内免除の完全無効化)"""
        with patch("app.core.security.settings") as mock_settings, \
             patch("app.services.settings_service.settings_manager") as mock_mgr:
            mock_settings.webhook_token = "secret-token-123"
            mock_mgr.get.return_value = {"webhookToken": "secret-token-123"}

            # 宅内LANからの未認証アクセス (ブラウザ同一オリジン) -> トークン免除が有効
            req_local = MagicMock()
            req_local.headers = {"sec-fetch-site": "same-origin"}
            req_local.query_params = {}
            req_local.client.host = "192.168.1.100"
            self.assertTrue(validate_webhook_token(req_local))

            # 外部トンネル経由からの未認証アクセス -> 免除が無効化されHTTPException(401)で拒絶される
            req_tunnel = MagicMock()
            req_tunnel.headers = {"cf-connecting-ip": "203.0.113.195"}
            req_tunnel.query_params = {}
            req_tunnel.client.host = "127.0.0.1"
            from fastapi import HTTPException
            with self.assertRaises(HTTPException):
                validate_webhook_token(req_tunnel)

            # 外部トンネル経由でも正しいトークンがあれば通過
            req_tunnel_authed = MagicMock()
            req_tunnel_authed.headers = {
                "cf-connecting-ip": "203.0.113.195",
                "x-webhook-token": "secret-token-123"
            }
            req_tunnel_authed.query_params = {}
            req_tunnel_authed.client.host = "127.0.0.1"
            self.assertTrue(validate_webhook_token(req_tunnel_authed))

    def test_tts_cache_key_generation(self):
        """TTS キャッシュキーの決定論的一意性"""
        k1 = tts_service._generate_cache_key("テスト", "ja-JP-NanamiNeural", "+0%", "+0Hz", "dingdong")
        k2 = tts_service._generate_cache_key("テスト", "ja-JP-NanamiNeural", "+0%", "+0Hz", "dingdong")
        k3 = tts_service._generate_cache_key("テスト2", "ja-JP-NanamiNeural", "+0%", "+0Hz", "dingdong")
        self.assertEqual(k1, k2)
        self.assertNotEqual(k1, k3)

    def test_calendar_multi_day_events_inclusion(self):
        """複数日にまたがる終日予定および時間指定予定が当日に正しく抽出されること"""
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        calendar_service.cached_events = [
            # 1. 昨日から明日までの終日予定 (出張・旅行等)
            {
                "id": "ev_trip",
                "summary": "東京出張",
                "start": datetime.combine(yesterday, datetime.min.time()),
                "end": datetime.combine(tomorrow + timedelta(days=1), datetime.min.time()),
                "isAllDay": True
            },
            # 2. 今日の時間指定予定
            {
                "id": "ev_meeting",
                "summary": "定例会議",
                "start": datetime.combine(today, datetime.min.time()) + timedelta(hours=14),
                "end": datetime.combine(today, datetime.min.time()) + timedelta(hours=15),
                "isAllDay": False
            },
            # 3. 昨日の過去予定
            {
                "id": "ev_past",
                "summary": "過去タスク",
                "start": datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=10),
                "end": datetime.combine(yesterday, datetime.min.time()) + timedelta(hours=11),
                "isAllDay": False
            }
        ]

        today_evs = calendar_service.get_today_events()
        summaries = [ev["summary"] for ev in today_evs]
        self.assertIn("東京出張", summaries)
        self.assertIn("定例会議", summaries)
        self.assertNotIn("過去タスク", summaries)

    def test_dnd_urgent_bypass(self):
        """DND モード発動中であっても urgent=True の緊急通知は通過すること"""
        with patch("app.services.dnd_service.settings_manager") as mock_mgr:
            mock_mgr.get.return_value = {
                "dnd": {
                    "enabled": True,
                    "manualUntil": 9999999999.0,  # 常に発動中
                    "urgentBypass": True
                }
            }
            # 通常発声 -> DND active (skip)
            eval_normal = dnd_service.evaluate(urgent=False)
            self.assertTrue(eval_normal["active"])

            # 緊急通知 -> DND active False (バイパス通過)
            eval_urgent = dnd_service.evaluate(urgent=True)
            self.assertFalse(eval_urgent["active"])


if __name__ == "__main__":
    unittest.main()
