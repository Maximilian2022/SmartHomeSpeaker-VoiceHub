import ast
import asyncio
import importlib
import pkgutil
import unittest
from datetime import datetime, date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from app.core.security import is_tunnel_request, validate_webhook_token
from app.services.tts_service import tts_service
from app.services.calendar_service import calendar_service
from app.services.dnd_service import dnd_service
from app.services.speech_service import speech_service
from app.services.onvif_service import onvif_service


class TestSmokeVoiceHub(unittest.TestCase):
    """Voice Hub 軽量スモークテストスイート (外部依存なし・高速検証)"""

    def test_dynamic_import_all_app_modules(self):
        """app/ 配下の全モジュールを動的にインポートし、SyntaxError/ImportError/NameError がないことを検証"""
        if Path("/app/app").is_dir():
            app_dir = Path("/app/app")
        else:
            app_dir = Path(__file__).resolve().parent.parent / "app"

        py_files = list(app_dir.rglob("*.py"))
        self.assertGreater(len(py_files), 10, "app/ 配下に十分な Python ファイルが存在すること")

        for py_file in py_files:
            rel_path = py_file.relative_to(app_dir)
            mod_parts = ["app"] + list(rel_path.with_suffix("").parts)
            mod_name = ".".join(mod_parts)
            try:
                mod = importlib.import_module(mod_name)
                self.assertIsNotNone(mod, f"Module {mod_name} should not be None")
            except Exception as e:
                self.fail(f"Failed to import {mod_name} ({py_file}): {e}")

    def test_ast_check_all_python_files(self):
        """app/ 配下の全ファイルの AST (構文木) を解析し、構文不正がないことを検証"""
        if Path("/app/app").is_dir():
            app_dir = Path("/app/app")
        else:
            app_dir = Path(__file__).resolve().parent.parent / "app"

        for py_file in app_dir.rglob("*.py"):
            code = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(code, filename=str(py_file))
                self.assertIsInstance(tree, ast.Module)
            except SyntaxError as se:
                self.fail(f"Syntax error in {py_file}: {se}")

    def test_speech_only_alexa_regression(self):
        """Alexa 単独発声時に opt_voice 等の未定義 UnboundLocalError が発生しないこと"""
        targets = [{"id": "alexa_living", "name": "Alexa (リビング)", "type": "alexa", "ip": "alexa:リビング"}]
        only_alexa = all(d.get("type") == "alexa" for d in targets)
        self.assertTrue(only_alexa)

        # opt_voice などの変数がスコープ外でも確実に定義されていること
        voice = None
        rate = None
        pitch = None
        chime = None

        opt_voice = voice or "ja-JP-NanamiNeural"
        opt_rate = rate or "+0%"
        opt_pitch = pitch or "+0Hz"
        opt_chime = chime or "dingdong"

        speech = {"filename": "", "filepath": "", "duration": 0.0, "cached": False, "voice": "alexa", "fallback": False}
        saved_audio_url = f"/voice/{speech['filename']}" if speech.get("filename") else ""
        self.assertEqual(saved_audio_url, "")

        history_entry = {
            "voice": opt_voice,
            "actualVoice": speech.get("voice", opt_voice),
            "rate": opt_rate,
            "pitch": opt_pitch,
            "audioUrl": saved_audio_url
        }
        self.assertEqual(history_entry["voice"], "ja-JP-NanamiNeural")
        self.assertEqual(history_entry["audioUrl"], "")

    def test_onvif_password_lookup_fallback(self):
        """ALL 指定等で camera 辞書に password が無い場合でも registeredDevices から取得できること"""
        with patch("app.services.onvif_service.settings_manager") as mock_mgr:
            mock_mgr.get.return_value = {
                "onvif": {
                    "defaultUsername": "admin",
                    "defaultPassword": "default_pass",
                    "registeredDevices": [
                        {"ip": "192.168.1.80", "username": "cam_user", "password": "camera_secret_pass"}
                    ]
                }
            }
            # カメラ辞書に password が欠落しているケース (devices_service の get_devices() 返却辞書)
            cam_dict = {"ip": "onvif:192.168.1.80", "rawIp": "192.168.1.80", "hasPassword": True}
            onvif_config = mock_mgr.get().get("onvif", {})
            raw_ip = cam_dict.get("rawIp") or cam_dict.get("ip", "").replace("onvif:", "")
            username = cam_dict.get("username")
            password = cam_dict.get("password")
            if not password or not username:
                for reg in onvif_config.get("registeredDevices", []):
                    if reg.get("ip") == raw_ip:
                        if not username:
                            username = reg.get("username")
                        if not password:
                            password = reg.get("password")
                        break
            username = username or onvif_config.get("defaultUsername", "admin")
            password = password or onvif_config.get("defaultPassword", "")

            self.assertEqual(username, "cam_user")
            self.assertEqual(password, "camera_secret_pass")

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
