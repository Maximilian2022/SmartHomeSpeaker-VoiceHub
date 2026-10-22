import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.settings_service import settings_manager
from app.core.security import ACTIVE_SESSIONS, generate_session_token, get_effective_admin_password
from app.services.ai_service import ai_service, DEFAULT_GEMINI_MODELS

class TestAuditFixes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.original_settings = dict(settings_manager.get())
        ACTIVE_SESSIONS.clear()

    def tearDown(self):
        settings_manager.update(self.original_settings)
        ACTIVE_SESSIONS.clear()

    def test_health_check_endpoint(self):
        """1-1: /health および /api/health がパスワード設定下でも認証不要で200 OKを返すこと"""
        settings_manager.set_admin_password("super-secret-1234")
        
        # /health
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("status"), "ok")
        self.assertEqual(res.json().get("app"), "SmartHomeSpeaker-VoiceHub")

        # /api/health
        res_api = self.client.get("/api/health")
        self.assertEqual(res_api.status_code, 200)
        self.assertEqual(res_api.json().get("status"), "ok")

        # /api/status は管理者パスワード設定時は401保護されること (情報保護)
        res_status = self.client.get("/api/status")
        self.assertEqual(res_status.status_code, 401)

    @patch("httpx.AsyncClient.post")
    def test_openai_call_no_nameerror(self, mock_post):
        """1-2: OpenAI API呼び出しで url / headers が正しく定義され NameError が起きないこと"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "OpenAIテスト要約完了"}}]
        }
        mock_post.return_value = mock_resp

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            text, err = loop.run_until_complete(
                ai_service._call_openai_with_err("sk-test-key", "gpt-4o-mini", "こんにちは")
            )
            self.assertEqual(text, "OpenAIテスト要約完了")
            self.assertIsNone(err)
            self.assertTrue(mock_post.called)
            # 引数に url と headers が渡されていることを検証
            called_args, called_kwargs = mock_post.call_args
            self.assertEqual(called_args[0], "https://api.openai.com/v1/chat/completions")
            self.assertIn("Authorization", called_kwargs.get("headers", {}))
            self.assertEqual(called_kwargs["headers"]["Authorization"], "Bearer sk-test-key")
        finally:
            loop.close()

    @patch("httpx.AsyncClient.get")
    def test_gemini_dynamic_model_filtering(self, mock_get):
        """1-3: Geminiモデル動的取得で、不要モデル(embedding/aqa/日付スナップショット等)が厳格に除外されること"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [
                {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"], "displayName": "Gemini 2.5 Flash"},
                {"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"], "displayName": "Gemini 2.5 Pro"},
                {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"], "displayName": "Text Embedding"},
                {"name": "models/aqa", "supportedGenerationMethods": ["generateAnswer"], "displayName": "Attributed QA"},
                {"name": "models/gemini-1.5-flash-001", "supportedGenerationMethods": ["generateContent"], "displayName": "Snapshot"},
                {"name": "models/imagen-3.0-generate", "supportedGenerationMethods": ["imageGeneration"], "displayName": "Imagen"},
            ]
        }
        mock_get.return_value = mock_resp

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            ai_service._gemini_models_cache = {"key_hash": "", "fetched_at": 0.0, "models": []}
            models = loop.run_until_complete(ai_service.get_gemini_models("valid-key"))
            model_ids = [m["id"] for m in models]

            # 含まれるべき主力モデル
            self.assertIn("gemini-2.5-flash", model_ids)
            self.assertIn("gemini-2.5-pro", model_ids)

            # 除外されるべき不要モデル
            self.assertNotIn("text-embedding-004", model_ids)
            self.assertNotIn("aqa", model_ids)
            self.assertNotIn("gemini-1.5-flash-001", model_ids)
            self.assertNotIn("imagen-3.0-generate", model_ids)
        finally:
            loop.close()

    def test_mcp_authentication_enforcement(self):
        """2-4: /mcp が管理者パスワード設定時に無認証アクセスを拒否し、認証時のみ許可すること"""
        settings_manager.set_admin_password("mcp-admin-pass")
        settings_manager.update({"webhookToken": "mcp-wh-token"})

        # 1. 無認証 GET /mcp -> 401
        res = self.client.get("/mcp")
        self.assertEqual(res.status_code, 401)

        # 2. Bearer 管理者パスワード -> 200
        res_authed = self.client.get("/mcp", headers={"Authorization": "Bearer mcp-admin-pass"})
        self.assertEqual(res_authed.status_code, 200)

        # 3. Bearer Webhook トークン -> 200
        res_wh = self.client.get("/mcp", headers={"Authorization": "Bearer mcp-wh-token"})
        self.assertEqual(res_wh.status_code, 200)

        # 4. ?token= Webhook トークン -> 200
        res_q = self.client.get("/mcp?token=mcp-wh-token")
        self.assertEqual(res_q.status_code, 200)

    def test_settings_masking_and_atomic_save(self):
        """2-5 & 2-9: GET /api/settings で秘密情報がマスクされ、PUT で adminPassword 直接変更が禁止されること"""
        settings_manager.set_admin_password("pass-secret")
        settings_manager.update({
            "webhookToken": "secret-wh-token",
            "ai": {"geminiApiKey": "AIzaSy-secret-key", "openaiApiKey": "sk-secret-key"}
        })

        # 認証付きで GET /api/settings
        res = self.client.get("/api/settings", headers={"x-admin-password": "pass-secret"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["adminPassword"], "********")
        self.assertEqual(data["webhookToken"], "********")
        self.assertEqual(data["ai"]["geminiApiKey"], "********")
        self.assertEqual(data["ai"]["openaiApiKey"], "********")

        # PUT /api/settings で adminPassword を書き換えようとしても無視されること
        res_put = self.client.put(
            "/api/settings",
            json={"adminPassword": "hacked-password", "chime": "chime_simple"},
            headers={"x-admin-password": "pass-secret"}
        )
        self.assertEqual(res_put.status_code, 200)
        # 管理者パスワードは元のまま維持されていること
        self.assertEqual(settings_manager.get_admin_password(), "pass-secret")
        self.assertEqual(settings_manager.get().get("chime"), "chime_simple")

    def test_password_change_invalidates_all_sessions(self):
        """2-8: パスワード変更時に既存の全セッションが一括失効すること"""
        settings_manager.set_admin_password("old-password-1")
        old_token = generate_session_token("old-password-1")
        self.assertIn(old_token, ACTIVE_SESSIONS)

        # パスワード変更 API を実行
        res = self.client.post(
            "/api/auth/password",
            json={"currentPassword": "old-password-1", "newPassword": "new-password-2"},
            cookies={"auth_token": old_token}
        )
        self.assertEqual(res.status_code, 200)
        # 古いトークンは失効していること
        self.assertNotIn(old_token, ACTIVE_SESSIONS)
        self.assertEqual(settings_manager.get_admin_password(), "new-password-2")

if __name__ == "__main__":
    unittest.main()
