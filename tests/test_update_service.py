import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.settings_service import settings_manager
from app.services.update_service import parse_semver, is_newer_version, update_service
from app.core.security import ACTIVE_SESSIONS, generate_session_token

class TestUpdateService(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.orig_admin_pw = settings_manager.get().get("adminPassword", "")
        settings_manager.set_admin_password("")
        ACTIVE_SESSIONS.clear()
        update_service._cached_release = None
        update_service._last_checked_time = 0.0

    def tearDown(self):
        settings_manager.set_admin_password(self.orig_admin_pw)
        ACTIVE_SESSIONS.clear()
        update_service._cached_release = None
        update_service._last_checked_time = 0.0

    def test_semver_parsing_and_comparison(self):
        """セマンティックバージョンのパースおよび比較検証"""
        self.assertEqual(parse_semver("v1.0.11"), (1, 0, 11))
        self.assertEqual(parse_semver("1.2.3"), (1, 2, 3))
        self.assertEqual(parse_semver("v2.0"), (2, 0, 0))
        self.assertEqual(parse_semver(""), (0, 0, 0))

        # バージョン比較
        self.assertTrue(is_newer_version("v1.0.12", "v1.0.11"))
        self.assertTrue(is_newer_version("1.1.0", "1.0.11"))
        self.assertTrue(is_newer_version("v2.0.0", "1.9.9"))
        self.assertFalse(is_newer_version("v1.0.11", "v1.0.11"))
        self.assertFalse(is_newer_version("v1.0.10", "v1.0.11"))

    def test_check_for_updates_cache_and_api(self):
        """GitHub Releases API の取得・キャッシュ (24時間)・更新判定の検証"""
        mock_gh_data = {
            "tag_name": "v1.0.12",
            "name": "v1.0.12 - 新機能リリース",
            "body": "・新機能追加\n・バグ修正",
            "html_url": "https://github.com/Maximilian2022/SmartHomeSpeaker-VoiceHub/releases/tag/v1.0.12",
            "published_at": "2026-10-25T00:00:00Z"
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gh_data

        with patch("httpx.AsyncClient.get", return_value=mock_resp) as mock_get:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 1回目: API を叩いて取得
                res1 = loop.run_until_complete(update_service.check_for_updates(force_refresh=False))
                self.assertTrue(res1["hasUpdate"])
                self.assertEqual(res1["latestVersion"], "v1.0.12")
                self.assertEqual(res1["status"], "update_available")
                self.assertEqual(mock_get.call_count, 1)

                # 2回目: 24時間キャッシュから返り、API は再呼び出しされない
                res2 = loop.run_until_complete(update_service.check_for_updates(force_refresh=False))
                self.assertEqual(res2["latestVersion"], "v1.0.12")
                self.assertEqual(mock_get.call_count, 1)

                # 3回目: force_refresh=True で再取得
                res3 = loop.run_until_complete(update_service.check_for_updates(force_refresh=True))
                self.assertEqual(mock_get.call_count, 2)
            finally:
                loop.close()

    def test_watchtower_health_check(self):
        """Watchtower HTTP API の稼働確認ロジックの検証"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 正常待機中 (405 Method Not Allowed / 200 OK)
            mock_resp_405 = MagicMock(status_code=405)
            with patch("httpx.AsyncClient.get", return_value=mock_resp_405):
                health = loop.run_until_complete(update_service.check_watchtower_health())
                self.assertTrue(health["available"])
                self.assertIn("待機中", health["message"])

            # 未実行 (ConnectError)
            import httpx
            with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
                health_off = loop.run_until_complete(update_service.check_watchtower_health())
                self.assertFalse(health_off["available"])
                self.assertIn("起動していません", health_off["message"])
        finally:
            loop.close()

    def test_api_system_version_and_update(self):
        """/api/system/version および /api/system/update エンドポイントの検証"""
        # 1. GET /api/system/version
        res_v = self.client.get("/api/system/version")
        self.assertEqual(res_v.status_code, 200)
        data_v = res_v.json()
        self.assertIn("currentVersion", data_v)
        self.assertIn("watchtower", data_v)
        self.assertIn("autoUpdate", data_v)

        # 2. 管理者パスワード設定時の POST /api/system/update 認証保護
        settings_manager.set_admin_password("super-sys-admin")
        
        # 未認証: 401
        res_unauth = self.client.post("/api/system/update")
        self.assertEqual(res_unauth.status_code, 401)

        # 管理者セッション Cookie 認証: Watchtower トリガーが呼ばれる
        session_token = generate_session_token("super-sys-admin")
        mock_wt_resp = MagicMock(status_code=200, text="OK")
        with patch("httpx.AsyncClient.post", return_value=mock_wt_resp):
            res_auth = self.client.post("/api/system/update", cookies={"auth_token": session_token})
            self.assertEqual(res_auth.status_code, 200)
            self.assertTrue(res_auth.json().get("success"))

if __name__ == "__main__":
    unittest.main()
