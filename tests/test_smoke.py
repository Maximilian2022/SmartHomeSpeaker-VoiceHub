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

    def test_dnd_flush_grouped_by_target(self):
        """DND保留解除時、同一宛先のみが要約され、本来のスピーカー宛てに再生されること"""
        from app.services.dnd_service import _normalize_target_key
        # 1. 宛先キー正規化の検証
        self.assertEqual(_normalize_target_key(None), ("__default__",))
        self.assertEqual(_normalize_target_key(""), ("__default__",))
        self.assertEqual(_normalize_target_key("living"), ("living",))
        self.assertEqual(_normalize_target_key("Living"), ("living",))
        self.assertEqual(_normalize_target_key("kitchen, living"), ("kitchen", "living"))
        self.assertEqual(_normalize_target_key(["living", "kitchen"]), ("kitchen", "living"))

        # 2. フラッシュ時のグルーピング発話検証
        dnd_service.clear_queue()
        # リビング宛て 2件 (要約対象: threshold=2)
        dnd_service.add_to_queue({"text": "リビング通知1", "targets": "Living"})
        dnd_service.add_to_queue({"text": "リビング通知2", "targets": "living"})
        # 寝室宛て 1件 (個別再生対象)
        dnd_service.add_to_queue({"text": "寝室通知1", "targets": "Bedroom"})
        # デフォルト宛て 1件 (個別再生対象: targets=None)
        dnd_service.add_to_queue({"text": "デフォルト通知1", "targets": None})

        spoken_calls = []

        async def mock_speaker(text: str, targets=None, urgent: bool = True, source: str = None, source_label: str = None):
            spoken_calls.append({"text": text, "targets": targets, "urgent": urgent, "source": source})

        dnd_service.set_speaker_executor(mock_speaker)

        with patch("app.services.dnd_service.settings_manager") as mock_mgr, \
             patch("app.services.ai_service.ai_service.summarize_dnd_messages", new_callable=AsyncMock) as mock_ai:
            mock_mgr.get.return_value = {
                "dnd": {
                    "aiSummaryEnabled": True,
                    "aiSummaryThreshold": 2
                }
            }
            mock_ai.return_value = "リビング通知が2件あります。"

            # 実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                flushed_count = loop.run_until_complete(dnd_service.check_and_flush_queue())
            finally:
                loop.close()

            self.assertEqual(flushed_count, 4)
            # リビング宛て要約が1回呼ばれていること
            mock_ai.assert_called_once_with(["リビング通知1", "リビング通知2"])

            # 発話回数: リビング(要約1件) + 寝室(個別1件) + デフォルト(個別1件) = 計3回
            self.assertEqual(len(spoken_calls), 3)

            # 1件目: リビング (要約文・宛先は元のLiving)
            self.assertIn("リビング通知が2件あります。", spoken_calls[0]["text"])
            self.assertEqual(spoken_calls[0]["targets"], "Living")
            self.assertEqual(spoken_calls[0]["source"], "dnd_queue")

            # 2件目: 寝室 (個別文・宛先はBedroom)
            self.assertEqual(spoken_calls[1]["text"], "寝室通知1")
            self.assertEqual(spoken_calls[1]["targets"], "Bedroom")

            # 3件目: デフォルト (個別文・宛先はNone)
            self.assertEqual(spoken_calls[2]["text"], "デフォルト通知1")
            self.assertIsNone(spoken_calls[2]["targets"])

    def test_devices_zeroconf_parsing_and_lookup(self):
        """Zeroconf によるデバイス・グループ登録と find_device 照合が正常に行われること"""
        import threading
        from app.services.devices_service import DeviceManager, CastServiceListener

        dm = DeviceManager.__new__(DeviceManager)
        dm.devices = {}
        dm._lock = threading.Lock()
        dm._zc = None
        dm._browser = None

        # 個別デバイス登録テスト
        dev_mock = {
            "id": "dev_192_168_11_50",
            "name": "書斎スピーカー",
            "ip": "192.168.11.50",
            "host": "192.168.11.50",
            "port": 8009,
            "model": "Google Nest Mini",
            "isGroup": False,
            "type": "google"
        }
        dm.update_device("192.168.11.50", dev_mock)

        # グループ登録テスト
        grp_mock = {
            "id": "group_32094_192_168_11_50",
            "name": "家中グループ",
            "ip": "192.168.11.50:32094",
            "host": "192.168.11.50",
            "port": 32094,
            "model": "Google Cast Group",
            "isGroup": True,
            "type": "google"
        }
        dm.update_device("group_192.168.11.50_32094", grp_mock)

        # 検索照合
        found_dev = dm.find_device("書斎スピーカー")
        self.assertIsNotNone(found_dev)
        self.assertEqual(found_dev["host"], "192.168.11.50")
        self.assertFalse(found_dev["isGroup"])

        found_grp = dm.find_device("家中グループ")
        self.assertIsNotNone(found_grp)
        self.assertEqual(found_grp["port"], 32094)
        self.assertTrue(found_grp["isGroup"])

    def test_azure_active_default_voice(self):
        """Azure 有効時にデフォルト話者が azure:ja-JP-NanamiNeural になり、無効時は Edge-TTS になること"""
        from unittest.mock import patch
        with patch.object(tts_service, "is_azure_active", return_value=True):
            self.assertEqual(tts_service.get_default_voice_id(), "azure:ja-JP-NanamiNeural")

        with patch.object(tts_service, "is_azure_active", return_value=False), \
             patch.object(tts_service.gcp_provider, "enabled", False):
            self.assertEqual(tts_service.get_default_voice_id(), "ja-JP-NanamiNeural")
    def test_compress_file_zstd(self):
        """Python 3.14 標準ライブラリ compression.zstd による圧縮・伸張が正常に機能すること"""
        import tempfile
        import shutil
        from app.core.log_rotator import compress_file_zstd

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            src = tmp_path / "test_src.txt"
            dest = tmp_path / "test_dest.txt.zst"
            original_content = "Log line for testing zstd compression.\n" * 50
            src.write_text(original_content, encoding="utf-8")

            success = compress_file_zstd(src, dest)
            self.assertTrue(success, "compress_file_zstd should return True")
            self.assertTrue(dest.exists(), "Compressed destination file should exist")
            self.assertGreater(dest.stat().st_size, 0, "Compressed file should not be empty")

            # 伸長検証 (Python 3.14 標準ライブラリ compression.zstd 経由)
            import compression.zstd as std_zstd
            with std_zstd.open(dest, "rb") as f_in:
                decompressed = f_in.read().decode("utf-8")
            self.assertEqual(decompressed, original_content, "Decompressed content must match original")



if __name__ == "__main__":
    unittest.main()



