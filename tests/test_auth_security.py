import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.settings_service import settings_manager
from app.core.security import ACTIVE_SESSIONS, login_rate_limiter

class TestAuthSecurity(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.orig_admin_password = settings_manager.get().get("adminPassword", "")
        self.orig_env_password = settings.admin_password
        # テスト開始前にセッションとレートリミッターをクリア
        ACTIVE_SESSIONS.clear()
        login_rate_limiter.attempts.clear()
        login_rate_limiter.lockouts.clear()

    def tearDown(self):
        # 設定を元に戻す
        settings_manager.set_admin_password(self.orig_admin_password)
        ACTIVE_SESSIONS.clear()
        login_rate_limiter.attempts.clear()
        login_rate_limiter.lockouts.clear()

    def test_security_headers_present(self):
        """全レスポンスにセキュリティヘッダーが付与されていることを検証"""
        res = self.client.get("/api/auth/status")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(res.headers.get("x-frame-options"), "DENY")
        self.assertEqual(res.headers.get("referrer-policy"), "strict-origin-when-cross-origin")

    def test_password_masking_in_settings(self):
        """GET /api/settings でパスワード平文が露出せずマスクされることを検証"""
        settings_manager.set_admin_password("supersecret123")
        res = self.client.get("/api/settings", headers={"x-admin-password": "supersecret123"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("hasAdminPassword"))
        self.assertEqual(data.get("adminPassword"), "********")

    def test_login_rate_limiter_lockout(self):
        """パスワード試行が5回失敗するとロックアウト (429) されることを検証"""
        settings_manager.set_admin_password("correct_pass_123")

        # 4回連続で誤ったパスワードを送信 (401)
        for i in range(4):
            res = self.client.post("/api/auth/login", json={"password": f"wrong_{i}"})
            self.assertEqual(res.status_code, 401)

        # 5回目の失敗でロックアウト (429)
        res5 = self.client.post("/api/auth/login", json={"password": "wrong_5"})
        self.assertEqual(res5.status_code, 429)
        self.assertIn("ロック", res5.json().get("detail", ""))

        # ロック中に正しいパスワードを送信しても 429 で遮断される
        res_correct = self.client.post("/api/auth/login", json={"password": "correct_pass_123"})
        self.assertEqual(res_correct.status_code, 429)

    def test_dynamic_tunnel_gating(self):
        """管理者パスワード未設定時は Tunnel 経由の GUI/API を 403 遮断し、設定時は許可 (401/200) することを検証"""
        tunnel_headers = {"cf-ray": "1234567890abcdef-NRT"}

        # 1. パスワード未設定時
        settings_manager.set_admin_password("")
        res_blocked = self.client.get("/api/settings", headers=tunnel_headers)
        self.assertEqual(res_blocked.status_code, 403)
        self.assertIn("Forbidden", res_blocked.json().get("detail", ""))

        # 2. パスワード設定時 (未ログインなので 401)
        settings_manager.set_admin_password("secure_pass_abc")
        res_allowed_auth_req = self.client.get("/api/settings", headers=tunnel_headers)
        self.assertEqual(res_allowed_auth_req.status_code, 401)

        # 3. パスワード設定時 (ログイン認証ヘッダー付きで 200 OK)
        res_ok = self.client.get("/api/settings", headers={**tunnel_headers, "x-admin-password": "secure_pass_abc"})
        self.assertEqual(res_ok.status_code, 200)

    def test_password_management_api(self):
        """POST /api/auth/password による設定・変更・解除を検証"""
        # 初回未設定状態からの設定
        settings_manager.set_admin_password("")
        res_set = self.client.post("/api/auth/password", json={"currentPassword": "", "newPassword": "new_password_999"})
        self.assertEqual(res_set.status_code, 200)
        self.assertTrue(res_set.json().get("authRequired"))
        self.assertEqual(settings_manager.get_admin_password(), "new_password_999")

        # 誤った currentPassword での変更は 401 で拒否
        res_fail = self.client.post("/api/auth/password", json={"currentPassword": "wrong", "newPassword": "fail"})
        self.assertEqual(res_fail.status_code, 401)

        # 正しい currentPassword でパスワード解除 (空文字)
        res_clear = self.client.post("/api/auth/password", json={"currentPassword": "new_password_999", "newPassword": ""})
        self.assertEqual(res_clear.status_code, 200)
        self.assertFalse(res_clear.json().get("authRequired"))
        self.assertEqual(settings_manager.get_admin_password(), "")

    def test_cookie_secure_flag_dynamic(self):
        """HTTP接続時は secure=False、Tunnel/HTTPS接続時は secure=True となることを検証"""
        settings_manager.set_admin_password("pass_flag_test")

        # HTTP
        res_http = self.client.post("/api/auth/login", json={"password": "pass_flag_test"})
        self.assertEqual(res_http.status_code, 200)
        cookie_header = res_http.headers.get("set-cookie", "")
        self.assertIn("auth_token=", cookie_header)
        self.assertIn("HttpOnly", cookie_header)
        self.assertNotIn("Secure", cookie_header)

        # Tunnel (HTTPS)
        res_tunnel = self.client.post(
            "/api/auth/login",
            json={"password": "pass_flag_test"},
            headers={"cf-ray": "abcdef123456"}
        )
        self.assertEqual(res_tunnel.status_code, 200)
        cookie_header_tunnel = res_tunnel.headers.get("set-cookie", "")
        self.assertIn("auth_token=", cookie_header_tunnel)
        self.assertIn("Secure", cookie_header_tunnel)

if __name__ == "__main__":
    unittest.main()
