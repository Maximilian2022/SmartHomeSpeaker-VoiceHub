import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from app.main import app, lifespan
from app.services.disaster_service import disaster_service
from app.services.rain_alarm_service import rain_alarm_service
from app.services.speech_service import speech_service


class TestSpeechDispatch(unittest.IsolatedAsyncioTestCase):
    async def test_disaster_service_speech_dispatch_with_kwargs(self):
        """disaster_service から source等のkwargs付きで発話要求が来ても TypeError にならず speech_service に届くことを検証"""
        recorded_calls = []

        async def mock_speak(**kwargs):
            recorded_calls.append(kwargs)
            return {"status": "success", "results": []}

        with patch.object(speech_service, "speak", side_effect=mock_speak):
            # lifespan内のon_disaster_speech登録と同様のシグネチャを検証
            async def on_disaster_speech(text: str, targets=None, urgent: bool = True, volume_level: int = None, **kwargs):
                await speech_service.speak(text=text, targets=targets or "ALL", urgent=urgent, volume_level=volume_level, **kwargs)

            disaster_service.set_speech_executor(on_disaster_speech)

            # disaster_service.speak を実行 (source, source_label, client_name が渡される)
            await disaster_service.speak(
                text="テスト気象警報です",
                urgent=False
            )

            self.assertEqual(len(recorded_calls), 1)
            call_args = recorded_calls[0]
            self.assertEqual(call_args["text"], "テスト気象警報です")
            self.assertIsInstance(call_args["targets"], list)
            self.assertEqual(call_args["source"], "disaster")
            self.assertEqual(call_args["source_label"], "防災速報")
            self.assertEqual(call_args["client_name"], "防災速報サービス")

    async def test_rain_alarm_speak_alert_delegates_to_speech_service(self):
        """rain_alarm_service の _speak_alert が speech_service.speak を正しく呼び出すことを検証"""
        recorded_calls = []

        async def mock_speak(**kwargs):
            recorded_calls.append(kwargs)
            return {"status": "success", "results": []}

        with patch.object(speech_service, "speak", side_effect=mock_speak):
            await rain_alarm_service._speak_alert("テスト雨雲接近通知です", "approaching")

            self.assertEqual(len(recorded_calls), 1)
            call_args = recorded_calls[0]
            self.assertEqual(call_args["text"], "テスト雨雲接近通知です")
            self.assertEqual(call_args["source"], "rain_alarm")
            self.assertEqual(call_args["source_label"], "雨アラーム")
            self.assertEqual(call_args["client_name"], "雨アラームサービス")

    async def test_deduplication_skip_recorded_in_history(self):
        """重複排除でスキップされた通知でも履歴に status: skipped で残ることを検証"""
        from app.services.history_service import history_manager
        from app.services.settings_service import settings_manager
        from app.core.deduplication import deduplicator

        deduplicator.clear()
        initial_history_count = len(history_manager.history)

        with patch.dict(settings_manager.settings, {"deduplication": {"enabled": True, "cooldownSeconds": 30}}):
            # 1回目の発話 (成功)
            with patch("app.services.speech_service.tts_service.synthesize", new_callable=AsyncMock) as mock_tts, \
                 patch("app.services.speech_service.cast_service.play_audio", new_callable=AsyncMock) as mock_cast, \
                 patch("app.services.devices_service.device_manager.get_devices", new_callable=AsyncMock) as mock_devs:
                mock_tts.return_value = {"filename": "test.mp3", "filepath": "/tmp/test.mp3", "duration": 1.0, "voice": "nanami", "fallback": False}
                mock_cast.return_value = True
                mock_devs.return_value = [{"name": "Default Speaker", "ip": "192.168.1.50", "type": "google"}]

                res1 = await speech_service.speak(text="重複テストメッセージ", targets=["192.168.1.50"], client_name="TestClient", urgent=False)
                self.assertTrue(res1.get("success"))

                # 2回目の発話 (30秒以内なので重複スキップ)
                res2 = await speech_service.speak(text="重複テストメッセージ", targets=["192.168.1.50"], client_name="TestClient", urgent=False)
                self.assertEqual(res2.get("status"), "skipped")
                self.assertTrue(res2.get("deduplicated"))

                # 履歴の最新エントリが skipped として記録されていること
                latest = history_manager.history[0]
                self.assertEqual(latest["text"], "重複テストメッセージ")
                self.assertEqual(latest["status"], "skipped")
                self.assertIn("重複スキップ", latest["statusMessage"])

    async def test_no_valid_targets_recorded_in_history(self):
        """対象スピーカーが見つからないエラー時でも履歴に status: error で残ることを検証"""
        from app.services.history_service import history_manager

        with patch("app.services.devices_service.device_manager.get_devices", new_callable=AsyncMock) as mock_devs:
            mock_devs.return_value = []  # スピーカーゼロ

            res = await speech_service.speak(text="宛先なしテスト", targets=["non_existent_ip"], urgent=True)
            self.assertEqual(res.get("status"), "error")

            latest = history_manager.history[0]
            self.assertEqual(latest["text"], "宛先なしテスト")
            self.assertEqual(latest["status"], "error")
            self.assertIn("対象スピーカーが見つかりませんでした", latest["statusMessage"])

    async def test_tts_error_recorded_in_history(self):
        """TTS合成エラー時でも履歴に status: error で残ることを検証"""
        from app.services.history_service import history_manager

        with patch("app.services.speech_service.tts_service.synthesize", new_callable=AsyncMock) as mock_tts, \
             patch("app.services.devices_service.device_manager.get_devices", new_callable=AsyncMock) as mock_devs:
            mock_devs.return_value = [{"name": "Speaker", "ip": "192.168.1.50", "type": "google"}]
            mock_tts.side_effect = RuntimeError("TTS Connection Refused")

            res = await speech_service.speak(text="TTSエラーテスト", targets=["ALL"], urgent=True)
            self.assertEqual(res.get("status"), "error")

            latest = history_manager.history[0]
            self.assertEqual(latest["text"], "TTSエラーテスト")
            self.assertEqual(latest["status"], "error")
            self.assertIn("音声合成に失敗しました", latest["statusMessage"])

    def test_derive_source_labels(self):
        """各送信元キーに対応する適切な日本語ラベルが返ることを検証"""
        from app.services.history_service import history_manager

        self.assertEqual(history_manager.derive_source_label("rain_alarm"), "雨アラーム")
        self.assertEqual(history_manager.derive_source_label("disaster"), "防災速報")
        self.assertEqual(history_manager.derive_source_label("mcp"), "MCP連携")
        self.assertEqual(history_manager.derive_source_label("mqtt"), "MQTT連携")
        self.assertEqual(history_manager.derive_source_label("scheduled_speech"), "発声予約 (日時指定)")
        self.assertEqual(history_manager.derive_source_label("unknown_source"), "外部 API / Webhook")
