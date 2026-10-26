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

    async def test_resolve_fallback_targets_hierarchy(self):
        """フォールバック先の優先順位階層 (Group > 単体, GH > Alexa > HP > DLNA > ONVIF) の動作を検証"""
        from app.services.settings_service import settings_manager

        mock_devices = [
            {"name": "リビング GH", "ip": "192.168.1.10", "type": "google", "isGroup": False},
            {"name": "寝室 GH", "ip": "192.168.1.11", "type": "google", "isGroup": False},
            {"name": "ALL", "ip": "192.168.1.10", "port": 32094, "type": "google", "isGroup": True},
            {"name": "Echo Dot", "ip": "192.168.1.20", "type": "alexa", "isGroup": False},
            {"name": "Echo Group", "ip": "192.168.1.20", "type": "alexa", "isGroup": True},
            {"name": "HomePod mini", "ip": "192.168.1.30", "type": "homepod", "isGroup": False},
            {"name": "DLNA スピーカー", "ip": "192.168.1.40", "type": "dlna"},
            {"name": "玄関カメラ", "ip": "192.168.1.50", "type": "onvif"},
        ]

        # 1. auto: Google Cast Group (ALL) が最優先
        with patch.dict(settings_manager.settings, {"fallbackSpeaker": "auto"}):
            fb = await speech_service.resolve_fallback_targets(mock_devices)
            self.assertEqual(len(fb), 1)
            self.assertEqual(fb[0]["name"], "ALL")
            self.assertTrue(fb[0].get("isGroup"))
            self.assertIn("_fallback_members", fb[0])
            self.assertEqual(len(fb[0]["_fallback_members"]), 2)

        # 2. auto: Cast Group が無ければ Alexa Group
        no_cast_group = [d for d in mock_devices if not (d.get("type") == "google" and d.get("isGroup"))]
        with patch.dict(settings_manager.settings, {"fallbackSpeaker": "auto"}):
            fb = await speech_service.resolve_fallback_targets(no_cast_group)
            self.assertEqual(len(fb), 1)
            self.assertEqual(fb[0]["name"], "Echo Group")

        # 3. auto: グループが一切無ければ Google Cast 単体スピーカー群
        singles_only = [d for d in mock_devices if not d.get("isGroup")]
        with patch.dict(settings_manager.settings, {"fallbackSpeaker": "auto"}):
            fb = await speech_service.resolve_fallback_targets(singles_only)
            self.assertEqual(len(fb), 2)
            self.assertEqual([d["name"] for d in fb], ["リビング GH", "寝室 GH"])

        # 4. auto: Google Cast 単体も無ければ Alexa 単体
        no_google = [d for d in singles_only if d.get("type") != "google"]
        with patch.dict(settings_manager.settings, {"fallbackSpeaker": "auto"}):
            fb = await speech_service.resolve_fallback_targets(no_google)
            self.assertEqual(len(fb), 1)
            self.assertEqual(fb[0]["name"], "Echo Dot")

        # 5. auto: Alexa 単体も無ければ HomePod 単体
        no_alexa = [d for d in no_google if d.get("type") != "alexa"]
        with patch.dict(settings_manager.settings, {"fallbackSpeaker": "auto"}):
            fb = await speech_service.resolve_fallback_targets(no_alexa)
            self.assertEqual(len(fb), 1)
            self.assertEqual(fb[0]["name"], "HomePod mini")

        # 6. auto: HomePod も無ければ DLNA
        no_hp = [d for d in no_alexa if d.get("type") != "homepod"]
        with patch.dict(settings_manager.settings, {"fallbackSpeaker": "auto"}):
            fb = await speech_service.resolve_fallback_targets(no_hp)
            self.assertEqual(len(fb), 1)
            self.assertEqual(fb[0]["name"], "DLNA スピーカー")

        # 7. auto: ONVIF / Tapo のみがある環境なら ONVIF が返る
        onvif_only = [d for d in no_hp if d.get("type") != "dlna"]
        with patch.dict(settings_manager.settings, {"fallbackSpeaker": "auto"}):
            fb = await speech_service.resolve_fallback_targets(onvif_only)
            self.assertEqual(len(fb), 1)
            self.assertEqual(fb[0]["name"], "玄関カメラ")

        # 8. fallbackSpeaker: "none" の場合は空リスト
        with patch.dict(settings_manager.settings, {"fallbackSpeaker": "none"}):
            fb = await speech_service.resolve_fallback_targets(mock_devices)
            self.assertEqual(fb, [])

    async def test_cast_group_retry_and_fallback(self):
        """キャストグループ宛ての再生失敗時に2回リトライ後、個別スピーカーへフォールバックされることを検証"""
        from app.services.history_service import history_manager

        mock_group = {
            "name": "ALL",
            "ip": "192.168.1.10",
            "port": 32094,
            "type": "google",
            "isGroup": True,
            "_fallback_members": [
                {"name": "リビング", "ip": "192.168.1.10", "port": 8009, "type": "google", "isGroup": False},
                {"name": "キッチン", "ip": "192.168.1.11", "port": 8009, "type": "google", "isGroup": False}
            ]
        }

        call_log = []

        async def mock_play_audio(host, port, audio_url=None, volume_level=None, **kwargs):
            call_log.append((host, port))
            # ポートが32094 (グループ) は失敗し、8009 (個別) は成功するシミュレーション
            if port == 32094:
                return False
            return True

        mock_indiv1 = {"name": "リビング", "ip": "192.168.1.10", "port": 8009, "type": "google", "isGroup": False}
        mock_indiv2 = {"name": "キッチン", "ip": "192.168.1.11", "port": 8009, "type": "google", "isGroup": False}
        mock_devices = [mock_group, mock_indiv1, mock_indiv2]

        with patch("app.services.speech_service.tts_service.synthesize", new_callable=AsyncMock) as mock_tts, \
             patch("app.services.speech_service.cast_service.play_audio", side_effect=mock_play_audio), \
             patch("app.services.speech_service.cast_service.purge_cache") as mock_purge, \
             patch("app.services.devices_service.device_manager.get_devices", new_callable=AsyncMock) as mock_devs:

            mock_tts.return_value = {"filename": "test.mp3", "filepath": "/tmp/test.mp3", "duration": 1.0, "voice": "nanami", "fallback": False}
            mock_devs.return_value = mock_devices

            res = await speech_service.speak(
                text="グループフォールバックテスト",
                targets=["ALL"],
                urgent=False
            )

            # 最終結果は個別スピーカーへのフォールバックで成功
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("status"), "success")

            # 試行ログ: グループ(32094)で2回試行された後、個別2台(8009)へ送信されたこと
            group_calls = [c for c in call_log if c[1] == 32094]
            indiv_calls = [c for c in call_log if c[1] == 8009]
            self.assertEqual(len(group_calls), 2)
            self.assertEqual(len(indiv_calls), 2)
            self.assertTrue(mock_purge.called)

    async def test_cast_individual_retry_success(self):
        """個別スピーカー宛ての再生失敗時にDHCP再解決を含め最大3回リトライして成功することを検証"""
        call_log = []

        async def mock_play_audio(host, port, audio_url=None, volume_level=None, **kwargs):
            call_log.append((host, port))
            # 1回目・2回目は失敗、3回目に成功するシミュレーション
            if len(call_log) < 3:
                return False
            return True

        mock_spk = {"name": "寝室", "ip": "192.168.1.12", "port": 8009, "type": "google", "isGroup": False}

        with patch("app.services.speech_service.tts_service.synthesize", new_callable=AsyncMock) as mock_tts, \
             patch("app.services.speech_service.cast_service.play_audio", side_effect=mock_play_audio), \
             patch("app.services.speech_service.cast_service.purge_cache") as mock_purge, \
             patch("app.services.devices_service.device_manager.get_devices", new_callable=AsyncMock) as mock_devs:

            mock_tts.return_value = {"filename": "test.mp3", "filepath": "/tmp/test.mp3", "duration": 1.0, "voice": "nanami", "fallback": False}
            mock_devs.return_value = [mock_spk]

            res = await speech_service.speak(
                text="リトライ成功テスト",
                targets=["192.168.1.12"],
                urgent=False
            )

            self.assertTrue(res.get("success"))
            self.assertEqual(len(call_log), 3)
            self.assertTrue(mock_purge.called)
