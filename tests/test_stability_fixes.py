import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.tts.voicevox_provider import VoicevoxFamilyProvider, CoeiroinkProvider
from app.services.tts_service import TtsService
from app.services.cast_service import CastService
from app.core.resolver import MDNSResolver
from app.core.security import ACTIVE_SESSIONS, login_rate_limiter
from app.services.settings_service import settings_manager


class TestStabilityFixes(unittest.TestCase):
    def test_voicevox_prefix_extraction_for_custom_engine_ids(self):
        """カスタムエンジンIDでも voicevox:/sharevox:/coeiroink: 等が安全に剥がれ ValueError が起きないこと"""
        vv = VoicevoxFamilyProvider(
            provider_id="engine_1792329772027",
            display_name="PC GPU VOICEVOX",
            default_voice_id="voicevox:2"
        )
        self.assertEqual(vv.extract_raw_voice_id("voicevox:2"), "2")
        self.assertEqual(vv.extract_raw_voice_id("sharevox:21"), "21")
        self.assertEqual(vv.extract_raw_voice_id("engine_1792329772027:8"), "8")
        self.assertEqual(vv._resolve_speaker_int("voicevox:2"), 2)
        self.assertEqual(vv._resolve_speaker_int("invalid:abc"), 2)

        sample_uuid = "37dd027e-1234-5678-9abc-1234567890ab"
        ci = CoeiroinkProvider(base_url="http://127.0.0.1:50031", default_voice_id="coeiroink:140")
        ci.provider_id = "engine_1793503367974"
        self.assertEqual(ci.extract_raw_voice_id("coeiroink:140"), "140")
        self.assertEqual(ci.extract_raw_voice_id(f"{sample_uuid}:10"), f"{sample_uuid}:10")
        self.assertEqual(ci.extract_raw_voice_id(f"engine_1793503367974:{sample_uuid}:10"), f"{sample_uuid}:10")

    def test_coeiroink_synthesize_resolves_uuid_from_style_and_uses_provider_id(self):
        """COEIROINK カスタムエンジンでも UUID を正しく解決し speakerUuid に生プレフィックスを送らないこと"""
        sample_uuid = "37dd027e-1234-5678-9abc-1234567890ab"
        ci = CoeiroinkProvider(base_url="http://127.0.0.1:50031", enabled=True, default_voice_id="coeiroink:2")
        ci.provider_id = "engine_207c"
        ci._style_to_uuid[2] = sample_uuid
        ci._fallback_uuid = sample_uuid
        ci._fallback_style_id = 2

        posted_payloads = []

        class MockResp:
            def __init__(self, status_code, content=b"RIFF", json_data=None):
                self.status_code = status_code
                self.content = content
                self._json = json_data
                self.text = ""
            def json(self):
                return self._json

        class MockAsyncClient:
            def __init__(self, *args, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return False
            async def post(self, url, json=None, headers=None):
                posted_payloads.append(json)
                return MockResp(200, content=b"WAVDATA")

        with patch("app.services.tts.voicevox_provider.httpx.AsyncClient", MockAsyncClient), \
             patch.object(ci, "_wav_to_mp3", new_callable=AsyncMock, return_value=b"MP3DATA"):
            audio = asyncio.run(ci.synthesize("テスト", "coeiroink:2"))

        self.assertEqual(audio, b"MP3DATA")
        self.assertEqual(len(posted_payloads), 1)
        self.assertEqual(posted_payloads[0]["speakerUuid"], sample_uuid)
        self.assertEqual(posted_payloads[0]["styleId"], 2)

        # 未存在 styleId (999) を指定した場合でも、実在する fallback (sample_uuid, 2) ペアに揃えてフォールバックすること
        posted_payloads.clear()
        with patch("app.services.tts.voicevox_provider.httpx.AsyncClient", MockAsyncClient), \
             patch.object(ci, "_wav_to_mp3", new_callable=AsyncMock, return_value=b"MP3DATA"):
            audio2 = asyncio.run(ci.synthesize("テスト2", "coeiroink:999"))
        self.assertEqual(audio2, b"MP3DATA")
        self.assertEqual(posted_payloads[0]["speakerUuid"], sample_uuid)
        self.assertEqual(posted_payloads[0]["styleId"], 2)

    def test_tts_get_voices_does_not_trigger_warmup(self):
        """get_voices キャッシュ更新時に毎度バックグラウンドウォームアップが再発火しないこと"""
        svc = TtsService()
        with patch.object(svc, "sync_settings") as mock_sync, \
             patch.object(svc.edge_provider, "get_voices", new_callable=AsyncMock, return_value=[]):
            asyncio.run(svc.get_voices(force_refresh=True))
            mock_sync.assert_called_once_with(trigger_warmup=False)

    def test_cast_service_volume_timeout_does_not_abort_playback(self):
        """Cast 音量調整がタイムアウトしても音声再生自体は中断せず成功すること"""
        svc = CastService()
        mock_cast = MagicMock()
        mock_cast.socket_client.is_connected = True
        mock_cast.set_volume.side_effect = RuntimeError("Execution of set volume timed out after 2.0 s.")
        mock_mc = MagicMock()
        mock_cast.media_controller = mock_mc
        svc._cast_cache["192.168.11.176:32156"] = mock_cast

        ok = svc._sync_play("192.168.11.176", 32156, "http://192.168.11.244:8080/voice/a.mp3", volume_level=0.5)
        self.assertTrue(ok)
        mock_mc.play_media.assert_called_once_with("http://192.168.11.244:8080/voice/a.mp3", "audio/mpeg")
        mock_mc.block_until_active.assert_called_once()

    def test_cast_service_disconnects_on_wait_timeout_and_uses_tries_1(self):
        """Cast 接続タイムアウト時に tries=1 かつ cast.disconnect が確実に呼ばれてスレッドリークしないこと"""
        svc = CastService()
        mock_cast = MagicMock()
        mock_cast.wait.side_effect = TimeoutError("Execution of wait timed out after 3.5 s.")

        with patch("app.services.cast_service.pychromecast.get_chromecast_from_host", return_value=mock_cast) as mock_get:
            res = svc._get_cast("192.168.11.188", 8009)

        self.assertIsNone(res)
        self.assertEqual(mock_get.call_args.kwargs.get("tries"), 1)
        mock_cast.disconnect.assert_called_once()

    def test_resolver_os_fallback_and_async_safety(self):
        """MDNSResolver が Zeroconf 未検出時に OS 解決へフォールバックし安全に IP を返すこと"""
        res = MDNSResolver(ttl=10.0)
        mock_addr_resolver = MagicMock()
        mock_addr_resolver.request.return_value = False
        mock_addr_resolver.parsed_addresses.return_value = []

        with patch("app.core.resolver.AddressResolver", return_value=mock_addr_resolver), \
             patch.object(res, "_resolve_via_os", return_value="192.168.11.115"):
            ip = asyncio.run(res.resolve_host("MasterProDesk400G5.local", timeout=0.1))

        self.assertEqual(ip, "192.168.11.115")

    def test_expired_cookie_alone_does_not_trigger_rate_limit_lockout(self):
        """期限切れの auth_token Cookie だけを持つ未認証ポーリングで 429 IPロックが誤爆しないこと"""
        client = TestClient(app)
        orig_pass = settings_manager.get().get("adminPassword", "")
        ACTIVE_SESSIONS.clear()
        login_rate_limiter.attempts.clear()
        login_rate_limiter.lockouts.clear()
        try:
            settings_manager.set_admin_password("test_admin_pass_123")
            client.cookies.set("auth_token", "expired_stale_cookie_token")
            for _ in range(8):
                r = client.get("/api/dnd/status")
                self.assertEqual(r.status_code, 401)
            self.assertEqual(len(login_rate_limiter.lockouts), 0)
        finally:
            settings_manager.set_admin_password(orig_pass)
            ACTIVE_SESSIONS.clear()
            login_rate_limiter.attempts.clear()
            login_rate_limiter.lockouts.clear()


if __name__ == "__main__":
    unittest.main()
