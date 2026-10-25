import unittest
import asyncio
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
        self.orig_admin_password = settings_manager.get().get("adminPassword", "")
        settings_manager.set_admin_password("")
        ACTIVE_SESSIONS.clear()

    def tearDown(self):
        settings_manager.set_admin_password(self.orig_admin_password)
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

    @patch("httpx.AsyncClient.get")
    def test_ai_models_mask_key_protection(self, mock_get):
        """マスク文字列(********)がapiKeyとして渡されても外部APIに送信されず、保存済みキーが利用されること"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [
                {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
            ]
        }
        mock_get.return_value = mock_resp

        settings_manager.update({
            "ai": {
                "enabled": True,
                "provider": "gemini",
                "geminiApiKey": "AIzaSy-saved-real-key"
            }
        })

        # クエリパラメータに "********" (マスク値) を渡す
        ai_service._gemini_models_cache = {"api_key": "", "fetched_at": 0.0, "models": []}
        res = self.client.get("/api/ai/models?provider=gemini&apiKey=********&forceRefresh=true")
        self.assertEqual(res.status_code, 200)

        # mock_get が呼ばれたURLを確認: "********" ではなく saved_key ("AIzaSy-saved-real-key") が使用されていること
        mock_get.assert_called()
        call_url = mock_get.call_args[0][0]
        self.assertNotIn("key=********", call_url)
        self.assertIn("key=AIzaSy-saved-real-key", call_url)

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

    def test_dynamic_openai_models(self):
        """OpenAI モデル一覧の動的取得・不要モデル除外・ソート・フォールバックの検証"""
        from app.services.ai_service import ai_service, DEFAULT_OPENAI_MODELS
        from unittest.mock import patch, MagicMock

        mock_openai_data = {
            "object": "list",
            "data": [
                {"id": "gpt-4o-mini", "object": "model"},
                {"id": "gpt-4o", "object": "model"},
                {"id": "gpt-4o-2024-08-06", "object": "model"}, # スナップショット版 -> 除外
                {"id": "o3-mini", "object": "model"},
                {"id": "o1", "object": "model"},
                {"id": "whisper-1", "object": "model"}, # 音声 -> 除外
                {"id": "dall-e-3", "object": "model"}, # 画像 -> 除外
                {"id": "text-embedding-3-small", "object": "model"}, # 埋め込み -> 除外
                {"id": "babbage-002", "object": "model"}, # レガシー -> 除外
                {"id": "gpt-4o-realtime-preview", "object": "model"}, # リアルタイム -> 除外
                {"id": "ft:gpt-4o:my-org:custom", "object": "model"} # 微調整 -> 除外
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_openai_data

        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            # 1. 正常取得と不要モデル除外のテスト
            models = asyncio.run(ai_service.get_openai_models("sk-test-key", force_refresh=True))
            model_ids = [m["id"] for m in models]

            self.assertIn("gpt-4o-mini", model_ids)
            self.assertIn("gpt-4o", model_ids)
            self.assertIn("o3-mini", model_ids)
            self.assertIn("o1", model_ids)

            # 除外対象が含まれていないこと
            self.assertNotIn("gpt-4o-2024-08-06", model_ids)
            self.assertNotIn("whisper-1", model_ids)
            self.assertNotIn("dall-e-3", model_ids)
            self.assertNotIn("text-embedding-3-small", model_ids)
            self.assertNotIn("babbage-002", model_ids)
            self.assertNotIn("gpt-4o-realtime-preview", model_ids)

            # 推奨ソート順: gpt-4o-mini が先頭
            self.assertEqual(model_ids[0], "gpt-4o-mini")

            # 2. キャッシュの検証 (API を呼ばずに返却)
            cached_models = asyncio.run(ai_service.get_openai_models("sk-test-key", force_refresh=False))
            self.assertEqual(models, cached_models)

        # 3. エラー時のフォールバック検証
        mock_err_resp = MagicMock()
        mock_err_resp.status_code = 401
        mock_err_resp.text = "Invalid API key"

        with patch("httpx.AsyncClient.get", return_value=mock_err_resp):
            fallback_models = asyncio.run(ai_service.get_openai_models("sk-invalid-key", force_refresh=True))
            self.assertEqual(fallback_models, DEFAULT_OPENAI_MODELS)

        # 4. API エンドポイント /api/ai/models?provider=openai の検証
        res = self.client.get("/api/ai/models?provider=openai")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["provider"], "openai")
        self.assertIn("models", data)

    def test_oauth_protected_resource_metadata(self):
        """MCP クライアント (Claude / Cursor) の RFC 8414 リソースメタデータエンドポイントが 200 OK を返すこと"""
        res1 = self.client.get("/.well-known/oauth-protected-resource")
        self.assertEqual(res1.status_code, 200)
        self.assertIn("resource", res1.json())
        self.assertIn("scopes_supported", res1.json())

        res2 = self.client.get("/.well-known/oauth-protected-resource/mcp/sse")
        self.assertEqual(res2.status_code, 200)
        self.assertIn("resource", res2.json())

    def test_status_webhook_token_resolution_and_tunnel_masking(self):
        """GET /api/status での実効 Webhook トークン解決とトンネル経由マスクの検証"""
        with patch.object(settings_manager, "get_webhook_token", return_value="test-token-xyz"):
            # 1. LAN アクセス: トークンが平文で返る
            res_lan = self.client.get("/api/status")
            self.assertEqual(res_lan.status_code, 200)
            data_lan = res_lan.json()
            self.assertTrue(data_lan.get("hasWebhookToken"))
            self.assertEqual(data_lan.get("webhookToken"), "test-token-xyz")

            # 管理者パスワード設定時
            settings_manager.set_admin_password("test-admin-pw")
            try:
                tunnel_headers = {"cf-ray": "123456789-NRT"}
                
                # 2. 未ログイン Tunnel アクセス (Webhook Token 連携ヘッダー付き): 200 OK だが生トークンは隠蔽 (webhookToken=None)
                res_tunnel = self.client.get("/api/status", headers={**tunnel_headers, "x-webhook-token": "test-token-xyz"})
                self.assertEqual(res_tunnel.status_code, 200)
                data_tunnel = res_tunnel.json()
                self.assertTrue(data_tunnel.get("hasWebhookToken"))
                self.assertIsNone(data_tunnel.get("webhookToken"))

                # 3. 認証済み管理者セッション (Cookie) による Tunnel アクセス: トークンが平文で返る
                ACTIVE_SESSIONS.add("mock-session-token")
                try:
                    res_authed = self.client.get(
                        "/api/status",
                        headers=tunnel_headers,
                        cookies={"auth_token": "mock-session-token"}
                    )
                    self.assertEqual(res_authed.status_code, 200)
                    data_authed = res_authed.json()
                    self.assertTrue(data_authed.get("hasWebhookToken"))
                    self.assertEqual(data_authed.get("webhookToken"), "test-token-xyz")
                finally:
                    ACTIVE_SESSIONS.discard("mock-session-token")
            finally:
                settings_manager.set_admin_password("")

    def test_rain_alarm_forecast_graceful_error_handling(self):
        """外部気象 API 障害時でも GET /api/rain-alarm/forecast が 500 にならず 200 フォールバックを返し、内部例外が露出しないこと"""
        from unittest.mock import AsyncMock
        with patch("app.services.rain_alarm_service.rain_alarm_service.fetch_forecast", side_effect=RuntimeError("JMA Timeout")):
            res = self.client.get("/api/rain-alarm/forecast?lat=35.6&lon=139.7")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data.get("currentRainfall"), 0.0)
            self.assertEqual(data.get("timeline"), [])
            self.assertEqual(data.get("providerUsed"), "error")
            self.assertEqual(data.get("error"), "Failed to fetch weather forecast")
            self.assertNotIn("JMA Timeout", data.get("error", ""))

    def test_dnd_script_privilege_escalation_prevention(self):
        """DND スクリプト生成において、管理者パスワードの平文漏洩が防止され、Webhook トークンのみが安全に埋め込まれること"""
        settings_manager.set_admin_password("super-admin-secret-999")
        try:
            with patch.object(settings_manager, "get_webhook_token", return_value="webhook-safe-token-123"):
                # 1. 未認証 (または Webhook トークン連携) でのプレビュー要求: 管理者パスワードは絶対に漏洩せず、Webhook トークンのみ埋め込まれること
                res = self.client.get("/api/dnd/script/preview?format=vbs&action=toggle&token=webhook-safe-token-123")
                self.assertEqual(res.status_code, 200)
                content = res.json().get("content", "")
                self.assertNotIn("super-admin-secret-999", content)
                self.assertIn("webhook-safe-token-123", content)
                self.assertIn("token=", content)

                # PowerShell 形式でも検証
                res_ps = self.client.get("/api/dnd/script/preview?format=ps1&action=toggle&token=webhook-safe-token-123")
                self.assertEqual(res_ps.status_code, 200)
                ps_content = res_ps.json().get("content", "")
                self.assertNotIn("super-admin-secret-999", ps_content)
                self.assertIn("webhook-safe-token-123", ps_content)
                self.assertIn("&token=", ps_content)

                # 2. 認証済み管理者セッション Cookie の場合: 管理者パスワードの埋め込みが許可されること
                ACTIVE_SESSIONS.add("admin-session-ok")
                try:
                    res_admin = self.client.get(
                        "/api/dnd/script/preview?format=vbs&action=toggle",
                        cookies={"auth_token": "admin-session-ok"}
                    )
                    self.assertEqual(res_admin.status_code, 200)
                    admin_content = res_admin.json().get("content", "")
                    self.assertIn("super-admin-secret-999", admin_content)
                finally:
                    ACTIVE_SESSIONS.discard("admin-session-ok")
        finally:
            settings_manager.set_admin_password("")

    def test_tunnel_well_known_access_without_admin_password(self):
        """管理者パスワード未設定時でも、Cloudflare Tunnel 経由で RFC 8414 プローブ (/.well-known/) が 403 にならず 200 OK を返すこと"""
        tunnel_headers = {"cf-ray": "999888777-NRT"}
        res = self.client.get("/.well-known/oauth-protected-resource", headers=tunnel_headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("resource", res.json())

    def test_mcp_x_webhook_token_header_auth(self):
        """管理者パスワード設定下で、MCP クライアントが x-webhook-token ヘッダーで正常に認証通過すること"""
        settings_manager.set_admin_password("admin-pass-mcp")
        try:
            with patch.object(settings_manager, "get_webhook_token", return_value="mcp-valid-token-777"):
                # ヘッダーなし: 401
                res_no_auth = self.client.get("/mcp")
                self.assertEqual(res_no_auth.status_code, 401)

                # x-webhook-token ヘッダーあり: 200 OK
                res_header = self.client.get("/mcp", headers={"x-webhook-token": "mcp-valid-token-777"})
                self.assertEqual(res_header.status_code, 200)
                self.assertTrue(res_header.json().get("enabled"))
        finally:
            settings_manager.set_admin_password("")

    def test_integration_groups_and_history_auth(self):
        """管理者パスワード設定下で、連携トークンにより GET /api/groups および GET /api/history が許可され、DELETE /api/history は拒否されること"""
        settings_manager.set_admin_password("admin-pass-protect")
        try:
            with patch.object(settings_manager, "get_webhook_token", return_value="integration-token-888"):
                headers = {"x-webhook-token": "integration-token-888"}

                # GET /api/groups: トークンありで 200 OK
                res_groups = self.client.get("/api/groups", headers=headers)
                self.assertEqual(res_groups.status_code, 200)

                # GET /api/history: トークンありで 200 OK
                res_hist = self.client.get("/api/history", headers=headers)
                self.assertEqual(res_hist.status_code, 200)
                self.assertIn("history", res_hist.json())

                # DELETE /api/history: トークンのみでは 401 Unauthorized (管理者必須)
                res_del = self.client.delete("/api/history", headers=headers)
                self.assertEqual(res_del.status_code, 401)
        finally:
            settings_manager.set_admin_password("")

    def test_rain_alarm_forecast_cache(self):
        """降雨予測 API が 60 秒インメモリキャッシュにより同一座標への重複リクエストをキャッシュ返却すること"""
        from app.services.rain_alarm_service import rain_alarm_service
        import asyncio

        call_count = 0
        async def mock_fetch(lat, lon):
            nonlocal call_count
            call_count += 1
            return 1.5, [{"time": "12:00", "rainfall": 1.5}]

        rain_alarm_service._forecast_cache.clear()
        with patch.object(rain_alarm_service, "_fetch_openmeteo", side_effect=mock_fetch):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 1回目: mock_fetch が呼ばれる
                curr1, timeline1, prov1 = loop.run_until_complete(
                    rain_alarm_service.fetch_forecast(35.681, 139.767, provider="openmeteo")
                )
                self.assertEqual(call_count, 1)
                self.assertEqual(curr1, 1.5)

                # 2回目 (同一座標): キャッシュから返り call_count は増えない
                curr2, timeline2, prov2 = loop.run_until_complete(
                    rain_alarm_service.fetch_forecast(35.681, 139.767, provider="openmeteo")
                )
                self.assertEqual(call_count, 1)
                self.assertEqual(curr2, 1.5)
            finally:
                loop.close()
                rain_alarm_service._forecast_cache.clear()

if __name__ == "__main__":
    unittest.main()

