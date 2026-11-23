import asyncio
import importlib.util
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.settings_service import settings_manager
from app.services.client_speaker_service import client_speaker_service
from app.services.dnd_service import dnd_service
from app.services.speech_service import speech_service
from app.services.cast_service import cast_service


def _load_speaker_client_module():
    path = Path(__file__).resolve().parent.parent / "clients" / "speaker" / "voicehub_speaker.py"
    spec = importlib.util.spec_from_file_location("voicehub_speaker_mod", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRoomTagsAndVcMute(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(app)
        self._orig_tags = dict(settings_manager.get().get("deviceRoomTags", {}))
        self._orig_dnd = dict(settings_manager.get().get("dnd", {}))
        self._orig_disabled = list(settings_manager.get().get("disabledDevices", []))
        self._orig_queue = list(dnd_service.queue)
        self._orig_stop_exec = dnd_service._stop_executor
        self._orig_speak_exec = dnd_service._speaker_executor

        settings_manager.settings["deviceRoomTags"] = {}
        settings_manager.settings["disabledDevices"] = []
        dnd_service.queue = []
        client_speaker_service._clients.clear()
        speech_service._active_playbacks.clear()
        dnd_service.set_stop_executor(lambda room_tags=None: speech_service.stop_active_playbacks(room_tags=room_tags))
        dnd_service.set_speaker_executor(speech_service.speak)

    async def asyncTearDown(self):
        settings_manager.settings["deviceRoomTags"] = self._orig_tags
        settings_manager.settings["dnd"] = self._orig_dnd
        settings_manager.settings["disabledDevices"] = self._orig_disabled
        settings_manager._save(settings_manager.settings)
        dnd_service.queue = self._orig_queue
        dnd_service._save_queue()
        dnd_service._stop_executor = self._orig_stop_exec
        dnd_service._speaker_executor = self._orig_speak_exec
        client_speaker_service._clients.clear()
        speech_service._active_playbacks.clear()

    async def test_room_tag_assignment_and_pc_inheritance(self):
        """部屋タグの設定・複数デバイスへの同一タグ付与・PCクライアント本体からの継承を検証"""
        res1 = self.client.post("/api/devices/room-tag", json={"deviceId": "gh_1", "ip": "192.168.1.10", "roomTag": "自室"})
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["roomTag"], "自室")

        # PCクライアント本体に設定し、出力デバイスにも自動継承されるか確認
        res2 = self.client.post("/api/devices/room-tag", json={"clientId": "win_pc1", "roomTag": "自室"})
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(settings_manager.get_room_tag_for_device("client_win_pc1_out1", "client:win_pc1@out1", "win_pc1"), "自室")
        self.assertEqual(settings_manager.get_room_tag_for_device("client_win_pc1_out2", "client:win_pc1@out2", "win_pc1"), "自室")

        res3 = self.client.post("/api/devices/room-tag", json={"deviceId": "gh_2", "ip": "192.168.1.11", "roomTag": "リビング"})
        self.assertEqual(res3.status_code, 200)

        res_list = self.client.get("/api/devices/room-tags")
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(res_list.json()["rooms"], ["リビング", "自室"])

        # 空文字で解除
        res_del = self.client.post("/api/devices/room-tag", json={"deviceId": "gh_1", "ip": "192.168.1.10", "roomTag": ""})
        self.assertEqual(res_del.json()["roomTag"], "")
        self.assertEqual(settings_manager.get_room_tag_for_device("gh_1", "192.168.1.10"), "")

    async def test_vc_state_and_unregister_failsafe(self):
        """VC状態報告で即ミュート部屋に反映され、SSE切断(unregister)で安全に自動解除されること"""
        settings_manager.set_device_room_tag("client:pc_room", "書斎", client_id="pc_room")
        await client_speaker_service.register(client_id="pc_room", name="Work-PC", ip="192.168.1.90", platform="windows")

        with patch.object(speech_service, "stop_active_playbacks", new=AsyncMock(return_value=1)) as mock_stop:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.post("/api/client-speakers/vc-state", json={"clientId": "pc_room", "inVc": True, "app": "Discord"})
                self.assertEqual(res.status_code, 200)
                body = res.json()
                self.assertEqual(body["activatedRooms"], ["書斎"])
                self.assertEqual(body["vcMutedRooms"], ["書斎"])
                await asyncio.sleep(0.05)
                mock_stop.assert_awaited_once_with(room_tags={"書斎"})

                # DND mute / quick API からも即時停止が呼ばれることを確認
                mock_stop.reset_mock()
                res_mute = await ac.post("/api/dnd/mute", json={"reason": "テストミュート"})
                self.assertEqual(res_mute.status_code, 200)
                await asyncio.sleep(0.05)
                mock_stop.assert_awaited_once_with(room_tags=None)

                mock_stop.reset_mock()
                await ac.post("/api/dnd/unmute")
                res_quick = await ac.post("/api/dnd/quick", json={"minutes": 30})
                self.assertEqual(res_quick.status_code, 200)
                await asyncio.sleep(0.05)
                mock_stop.assert_awaited_once_with(room_tags=None)

        self.assertEqual(client_speaker_service.get_vc_muted_rooms(), {"書斎"})

        # SSE切断時に自動解除
        released = await client_speaker_service.unregister("pc_room")
        self.assertEqual(released, ["書斎"])
        self.assertEqual(client_speaker_service.get_vc_muted_rooms(), set())

    async def test_stop_active_playbacks_and_window_filtering(self):
        """DND ON時のアクティブ再生即停止（対象種別別）と期限切れセッション誤停止防止を検証"""
        # アクティブセッション登録（Google Cast + Client + DLNA）
        client_q = await client_speaker_service.register(client_id="pc_a", name="PC-A", ip="192.168.1.50", platform="windows")
        now_m = time.monotonic()
        speech_service._active_playbacks["sess_active"] = {
            "session_id": "sess_active",
            "started_at": now_m,
            "expected_end_at": now_m + 30.0,
            "audio_url": "http://192.168.1.100:8080/voice/test1.mp3",
            "stopped": False,
            "items": [
                {"dev": {"type": "google", "ip": "192.168.1.10", "host": "192.168.1.10", "port": 8009}, "room_tag": "自室", "host": "192.168.1.10", "port": 8009, "task": None, "stopped": False},
                {"dev": {"type": "client", "ip": "client:pc_a", "clientId": "pc_a"}, "room_tag": "自室", "host": None, "port": 8009, "task": None, "stopped": False},
                {"dev": {"type": "dlna", "ip": "dlna:192.168.1.20", "controlUrl": "http://192.168.1.20/AVTransport"}, "room_tag": "リビング", "host": None, "port": 8009, "task": None, "stopped": False},
            ],
        }
        # 期限切れの過去セッション
        speech_service._active_playbacks["sess_old"] = {
            "session_id": "sess_old",
            "started_at": now_m - 100.0,
            "expected_end_at": now_m - 50.0,
            "audio_url": "http://192.168.1.100:8080/voice/old.mp3",
            "stopped": False,
            "items": [
                {"dev": {"type": "google", "ip": "192.168.1.99", "host": "192.168.1.99", "port": 8009}, "room_tag": "寝室", "host": "192.168.1.99", "port": 8009, "task": None, "stopped": False},
            ],
        }

        with (
            patch("app.services.speech_service.cast_service.stop_playback", new=AsyncMock(return_value=True)) as mock_cast_stop,
            patch("app.services.speech_service.dlna_service.stop_playback", new=AsyncMock(return_value=True)) as mock_dlna_stop,
        ):
            # 1) 部屋指定 ("自室") 停止では自室の Cast & PC のみ止まり、リビングの DLNA や期限切れは止まらない
            cnt = await speech_service.stop_active_playbacks(room_tags={"自室"})
            self.assertEqual(cnt, 2)
            mock_cast_stop.assert_awaited_once_with("192.168.1.10", 8009, expected_media_url="http://192.168.1.100:8080/voice/test1.mp3")
            mock_dlna_stop.assert_not_awaited()
            ev = client_q.get_nowait()
            self.assertEqual(ev["event"], "stop")

            # 2) stopOnMute = False のときは notify_dnd_activated が停止しない
            settings_manager.settings["dnd"] = {**settings_manager.settings["dnd"], "stopOnMute": False}
            cnt_off = await dnd_service.notify_dnd_activated()
            self.assertEqual(cnt_off, 0)
            mock_dlna_stop.assert_not_awaited()

            # 3) stopOnMute = True のときは残っているアクティブ対象（リビング DLNA）のみ止まる（期限切れ 192.168.1.99 は対象外）
            settings_manager.settings["dnd"]["stopOnMute"] = True
            cnt_on = await dnd_service.notify_dnd_activated()
            self.assertEqual(cnt_on, 1)
            mock_dlna_stop.assert_awaited_once()
            self.assertEqual(mock_cast_stop.await_count, 1)

    def test_cast_sync_stop_guards_external_content(self):
        """Google Cast で YouTube 等他コンテンツ再生中は誤って stop() しないことを検証"""
        mock_cast = MagicMock()
        mock_cast.socket_client.is_connected = True
        mock_cast.media_controller.status.content_id = "https://www.youtube.com/watch?v=123"
        cast_service._cast_cache["192.168.1.10:8009"] = mock_cast
        try:
            ok_ext = cast_service._sync_stop("192.168.1.10", 8009, expected_media_url="http://192.168.1.100:8080/voice/v1.mp3")
            self.assertFalse(ok_ext)
            mock_cast.media_controller.stop.assert_not_called()

            mock_cast.media_controller.status.content_id = "http://192.168.1.100:8080/voice/v1.mp3"
            ok_vh = cast_service._sync_stop("192.168.1.10", 8009, expected_media_url="http://192.168.1.100:8080/voice/v1.mp3")
            self.assertTrue(ok_vh)
            mock_cast.media_controller.stop.assert_called_once()
        finally:
            cast_service._cast_cache.pop("192.168.1.10:8009", None)

    async def test_room_vc_mute_follows_dnd_action_and_flushes_on_leave(self):
        """VC中の部屋だけに DND アクション (skip/whisper/queue) が適用され、別部屋は通常発話、urgentは貫通することを検証"""
        settings_manager.set_device_room_tag("gh_room", "自室", alt_id="192.168.1.10")
        settings_manager.set_device_room_tag("gh_living", "リビング", alt_id="192.168.1.11")
        settings_manager.set_device_room_tag("client:pc_room", "自室", client_id="pc_room")

        await client_speaker_service.register(client_id="pc_room", name="SelfPC", ip="192.168.1.50", platform="windows")
        await client_speaker_service.update_vc_state("pc_room", True, app="Discord")

        fake_devices = [
            {"id": "group_all", "name": "全室", "ip": "192.168.1.10", "host": "192.168.1.10", "port": 42000, "type": "google", "isGroup": True, "roomTag": ""},
            {"id": "gh_room", "name": "自室Mini", "ip": "192.168.1.10", "host": "192.168.1.10", "port": 8009, "type": "google", "isGroup": False, "roomTag": "自室"},
            {"id": "gh_living", "name": "リビングHub", "ip": "192.168.1.11", "host": "192.168.1.11", "port": 8009, "type": "google", "isGroup": False, "roomTag": "リビング"},
        ]

        # グローバル DND は無効にして部屋 VC ミュートのみ検証
        settings_manager.settings["dnd"] = {
            **settings_manager.settings["dnd"],
            "enabled": True,
            "manualUntil": None,
            "calendarEnabled": False,
            "scheduleEnabled": False,
            "action": "skip",
            "whisperVolume": 12,
            "aiSummaryEnabled": False,
        }

        with (
            patch("app.services.speech_service.device_manager.get_devices", new=AsyncMock(return_value=fake_devices)),
            patch("app.services.speech_service.tts_service.synthesize", new=AsyncMock(return_value={"filename": "t.mp3", "filepath": "/tmp/t.mp3", "duration": 2.0, "voice": "v"})),
            patch("app.services.speech_service.cast_service.play_audio", new=AsyncMock(return_value=True)) as mock_play,
        ):
            # 1) action=skip で ALL 発話 -> グループ展開され「リビング」のみ鳴り、「自室」はスキップ
            res_skip = await speech_service.speak(text="宅配便です", targets="ALL")
            self.assertTrue(res_skip["success"])
            called_hosts = [c.args[0] for c in mock_play.await_args_list]
            self.assertEqual(called_hosts, ["192.168.1.11"])

            # 2) action=whisper で ALL 発話 -> 「リビング」は通常音量、「自室」は 0.12
            mock_play.reset_mock()
            settings_manager.settings["dnd"]["action"] = "whisper"
            await speech_service.speak(text="ご飯です", targets="ALL")
            calls_by_host = {c.args[0]: c.args[3] for c in mock_play.await_args_list}
            self.assertIn("192.168.1.10", calls_by_host)
            self.assertIn("192.168.1.11", calls_by_host)
            self.assertAlmostEqual(calls_by_host["192.168.1.10"], 0.12)

            # 3) action=queue で「自室」向けのみ発話 -> TTSせず部屋キューに保留され、VC退出時にフラッシュ
            mock_play.reset_mock()
            settings_manager.settings["dnd"]["action"] = "queue"
            res_q = await speech_service.speak(text="洗濯完了", targets=["192.168.1.10"])
            self.assertEqual(res_q["status"], "queued")
            self.assertEqual(len(dnd_service.queue), 1)
            self.assertEqual(dnd_service.queue[0]["room_tag"], "自室")
            mock_play.assert_not_awaited()

            # VC退出すると部屋キューがフラッシュされる
            await client_speaker_service.update_vc_state("pc_room", False)
            flushed = await dnd_service.check_and_flush_room_queue("自室")
            self.assertEqual(flushed, 1)
            self.assertEqual(len(dnd_service.queue), 0)
            self.assertTrue(any(c.args[0] == "192.168.1.10" for c in mock_play.await_args_list))

            # 4) urgent=True は VC 中でも貫通する
            await client_speaker_service.update_vc_state("pc_room", True, app="Discord")
            mock_play.reset_mock()
            res_urg = await speech_service.speak(text="緊急地震速報", targets=["192.168.1.10"], urgent=True)
            self.assertTrue(res_urg["success"])
            self.assertTrue(any(c.args[0] == "192.168.1.10" for c in mock_play.await_args_list))

    def test_client_windows_vc_watcher_and_audio_stop(self):
        """WindowsVcWatcher の Discord UDP / マイク判定と AudioPlayer.stop() の挙動を検証"""
        mod = _load_speaker_client_module()
        player = mod.AudioPlayer()
        self.assertEqual(player._play_gen, 0)
        player.stop()
        self.assertTrue(player._stop_event.is_set())
        self.assertEqual(player._play_gen, 1)

        with patch.object(mod, "IS_WIN", True):
            watcher = mod.WindowsVcWatcher()
            # 1) Discord プロセスなし & マイク未使用 -> False
            with (
                patch.object(watcher, "_list_running_processes", return_value={}),
                patch.object(watcher, "_check_win_microphone_in_use", return_value=([], [])),
            ):
                info = watcher.inspect()
                self.assertFalse(info["in_vc"])

            # 2) Discord で mDNS (5353) のみ -> False
            with (
                patch.object(watcher, "_list_running_processes", return_value={1234: "discord.exe"}),
                patch.object(watcher, "_get_udp_ports_for_pids", return_value=[5353]),
                patch.object(watcher, "_check_win_microphone_in_use", return_value=([], [])),
            ):
                info = watcher.inspect()
                self.assertFalse(info["in_vc"])

            # 3) Discord でエフェメラル UDP ポートが開いている (聞き専 VC) -> True
            with (
                patch.object(watcher, "_list_running_processes", return_value={1234: "discord.exe"}),
                patch.object(watcher, "_get_udp_ports_for_pids", return_value=[51234]),
                patch.object(watcher, "_check_win_microphone_in_use", return_value=([], [])),
            ):
                info = watcher.inspect()
                self.assertTrue(info["in_vc"])
                self.assertEqual(info["app"], "Discord")

            # 4) Zoom 等マイク使用中 -> True
            with (
                patch.object(watcher, "_list_running_processes", return_value={5678: "zoom.exe"}),
                patch.object(watcher, "_check_win_microphone_in_use", return_value=(["Zoom"], [])),
            ):
                info = watcher.inspect()
                self.assertTrue(info["in_vc"])
                self.assertEqual(info["app"], "Zoom")

            # 5) lghub_agent 等の常駐周辺機器ユーティリティや未起動ゴーストは VC 誤検知しない
            self.assertFalse(watcher._is_vc_mic_app("lghub_agent.exe", True, {"lghub_agent.exe", "discord.exe"}))
            self.assertFalse(watcher._is_vc_mic_app("Zoom.exe", True, {"discord.exe"}))
            self.assertTrue(watcher._is_vc_mic_app("Zoom.exe", True, {"zoom.exe"}))
