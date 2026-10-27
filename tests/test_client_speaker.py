import asyncio
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.client_speaker_service import client_speaker_service, ClientSpeakerInfo
from app.services.devices_service import device_manager
from app.services.speech_service import speech_service

class TestClientSpeakerIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # テスト開始前にクライアント辞書をクリア
        client_speaker_service._clients.clear()

    async def asyncTearDown(self):
        client_speaker_service._clients.clear()

    async def test_client_speaker_registration_and_unregister(self):
        """クライアントの登録、検索、デバイス辞書変換、切断解除のテスト"""
        queue = await client_speaker_service.register(
            client_id="test_pc_1",
            name="テストPC",
            ip="192.168.1.55",
            platform="windows"
        )
        self.assertIsNotNone(queue)
        
        # 検索
        client = client_speaker_service.find_client("test_pc_1")
        self.assertIsNotNone(client)
        self.assertEqual(client.name, "テストPC")
        self.assertEqual(client.platform, "windows")

        # 名前検索
        client_by_name = client_speaker_service.find_client("テストPC")
        self.assertEqual(client, client_by_name)

        # プレフィックス検索 (client:test_pc_1)
        client_by_prefix = client_speaker_service.find_client("client:test_pc_1")
        self.assertEqual(client, client_by_prefix)

        # デバイス一覧変換
        dev_list = client_speaker_service.get_active_devices()
        self.assertEqual(len(dev_list), 1)
        self.assertEqual(dev_list[0]["id"], "client_test_pc_1")
        self.assertEqual(dev_list[0]["type"], "client")
        self.assertEqual(dev_list[0]["model"], "Windows Speaker")

        # 切断
        await client_speaker_service.unregister("test_pc_1")
        self.assertIsNone(client_speaker_service.find_client("test_pc_1"))
        self.assertEqual(len(client_speaker_service.get_active_devices()), 0)

    async def test_play_event_dispatch(self):
        """再生イベントがキューに正しく投入されるかのテスト"""
        queue = await client_speaker_service.register(
            client_id="mac_work",
            name="MacBook Pro",
            ip="192.168.1.60",
            platform="macos"
        )

        ok = await client_speaker_service.send_play_event(
            client_id="mac_work",
            audio_url="http://localhost:8080/voice/test.mp3",
            text="こんにちは",
            volume=0.8
        )
        self.assertTrue(ok)
        self.assertFalse(queue.empty())

        item = queue.get_nowait()
        self.assertEqual(item["event"], "play")
        self.assertEqual(item["data"]["audio_url"], "http://localhost:8080/voice/test.mp3")
        self.assertEqual(item["data"]["text"], "こんにちは")
        self.assertEqual(item["data"]["volume"], 0.8)

    async def test_devices_service_integration(self):
        """DeviceManager.get_devices() にクライアントスピーカーが反映されるかのテスト"""
        await client_speaker_service.register(
            client_id="linux_box",
            name="Ubuntu Desk",
            ip="192.168.1.70",
            platform="linux"
        )

        devices = await device_manager.get_devices()
        found = next((d for d in devices if d.get("id") == "client_linux_box"), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["name"], "Ubuntu Desk")
        self.assertEqual(found["type"], "client")
        self.assertEqual(found["model"], "Linux Speaker")

        # find_device による検索
        found_dev = device_manager.find_device("Ubuntu Desk")
        self.assertIsNotNone(found_dev)
        self.assertEqual(found_dev["id"], "client_linux_box")

    async def test_speech_service_target_resolution(self):
        """SpeechService.resolve_targets による PC:ALL マクロ解決テスト"""
        await client_speaker_service.register(
            client_id="pc1",
            name="PC 1",
            ip="192.168.1.81",
            platform="windows"
        )
        await client_speaker_service.register(
            client_id="pc2",
            name="PC 2",
            ip="192.168.1.82",
            platform="macos"
        )

        # PC:ALL マクロ
        targets = await speech_service.resolve_targets(["PC:ALL"])
        target_ids = [t["id"] for t in targets]
        self.assertIn("client_pc1", target_ids)
        self.assertIn("client_pc2", target_ids)

        # 個別指定
        targets_single = await speech_service.resolve_targets(["PC 1"])
        self.assertEqual(len(targets_single), 1)
        self.assertEqual(targets_single[0]["id"], "client_pc1")

    def test_api_client_speakers_list(self):
        """GET /api/client-speakers の API テスト"""
        client = TestClient(app)
        res = client.get("/api/client-speakers")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("count", data)
        self.assertIn("devices", data)
