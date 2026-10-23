import unittest
import tempfile
import time
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.settings_service import settings_manager
from app.core.security import PersistentSessionSet, ACTIVE_SESSIONS


class TestSessionPersistence(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.orig_admin_password = settings_manager.get().get("adminPassword", "")
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_session_file = Path(self.tmp_dir.name) / "sessions.json"

    def tearDown(self):
        settings_manager.set_admin_password(self.orig_admin_password)
        ACTIVE_SESSIONS.clear()
        self.tmp_dir.cleanup()

    def test_persistent_session_set_crud(self):
        """PersistentSessionSet の基本操作およびファイル保存を検証"""
        store = PersistentSessionSet(file_path=self.tmp_session_file, default_ttl=3600)
        token = "test_token_123456"

        self.assertNotIn(token, store)
        store.add(token)
        self.assertIn(token, store)
        self.assertTrue(self.tmp_session_file.exists())

        # 別インスタンスで再読込 (再起動のシミュレーション)
        store2 = PersistentSessionSet(file_path=self.tmp_session_file, default_ttl=3600)
        self.assertIn(token, store2)

        # 削除
        store2.remove(token)
        self.assertNotIn(token, store2)

        # さらに再読込して削除が反映されていること
        store3 = PersistentSessionSet(file_path=self.tmp_session_file, default_ttl=3600)
        self.assertNotIn(token, store3)

    def test_session_expiry(self):
        """有効期限切れセッションが自動パージされることを検証"""
        store = PersistentSessionSet(file_path=self.tmp_session_file, default_ttl=1)
        token = "expiring_token_789"
        store.add(token, ttl=1)
        self.assertIn(token, store)

        # 1.1秒待機して期限切れ
        time.sleep(1.1)
        self.assertNotIn(token, store)

        # 再読込時にも読み込まれないこと
        store2 = PersistentSessionSet(file_path=self.tmp_session_file, default_ttl=3600)
        self.assertNotIn(token, store2)

    def test_auth_persistence_across_restart(self):
        """ログイン後のセッションが再起動 (ファイル再読込) 後も有効であることを検証"""
        settings_manager.set_admin_password("pass_secure_999")
        ACTIVE_SESSIONS.clear()

        # ログインを実行
        login_res = self.client.post("/api/auth/login", json={"password": "pass_secure_999"})
        self.assertEqual(login_res.status_code, 200)
        auth_cookie = login_res.cookies.get("auth_token")
        self.assertTrue(bool(auth_cookie))

        # ログイン直後のステータス確認 (200 & authenticated: True)
        self.client.cookies.set("auth_token", auth_cookie)
        status_res = self.client.get("/api/auth/status")
        self.assertEqual(status_res.status_code, 200)
        self.assertTrue(status_res.json().get("authenticated"))

        # 再起動シミュレーション: ACTIVE_SESSIONS の内部データを再ロード
        ACTIVE_SESSIONS._load()

        # 再ロード後も Cookie での保護APIアクセス (PUT /api/settings) が 200 で通ること
        settings_res = self.client.put(
            "/api/settings",
            json={"chime": "classic_doorbell"},
            cookies={"auth_token": auth_cookie}
        )
        self.assertEqual(settings_res.status_code, 200)

    def test_password_change_revokes_all_sessions(self):
        """パスワード変更時に全セッションが失効することを検証"""
        settings_manager.set_admin_password("initial_pass_123")
        ACTIVE_SESSIONS.clear()

        # ログイン
        login_res = self.client.post("/api/auth/login", json={"password": "initial_pass_123"})
        auth_cookie = login_res.cookies.get("auth_token")
        self.assertIn(auth_cookie, ACTIVE_SESSIONS)

        # パスワードを変更
        change_res = self.client.post(
            "/api/auth/password",
            json={"currentPassword": "initial_pass_123", "newPassword": "new_pass_456"},
            cookies={"auth_token": auth_cookie}
        )
        self.assertEqual(change_res.status_code, 200)

        # 旧セッションが ACTIVE_SESSIONS から失効していること
        self.assertNotIn(auth_cookie, ACTIVE_SESSIONS)

        # 再読込しても旧セッションが存在しないこと
        ACTIVE_SESSIONS._load()
        self.assertNotIn(auth_cookie, ACTIVE_SESSIONS)


if __name__ == "__main__":
    unittest.main()
