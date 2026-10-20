import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.services.settings_service import settings_manager
from app.services.speech_service import speech_service
from app.services.devices_service import device_manager
from app.core.security import derive_tapo_auth_token

class TestTapoIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.original_settings = dict(settings_manager.get())

    def tearDown(self):
        settings_manager.update(self.original_settings)

    def test_tapo_auth_and_hashing(self):
        raw_pass = "TestPassword!123"
        test_email = "test@example.com"
        expected_token = derive_tapo_auth_token(raw_pass)

        # 1. 保存APIテスト (email + password)
        resp = self.client.post("/api/onvif/tapo-auth", json={"email": test_email, "password": raw_pass})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))

        # 2. 設定取得確認
        cfg_resp = self.client.get("/api/onvif/config")
        self.assertEqual(cfg_resp.status_code, 200)
        cfg = cfg_resp.json()
        self.assertTrue(cfg.get("tapoAuthConfigured"))
        self.assertEqual(cfg.get("tapoEmail"), test_email)

        # 3. 内部設定に大文字SHA256ハッシュおよびemailが存在すること
        saved_cfg = settings_manager.get().get("onvif", {})
        self.assertEqual(saved_cfg.get("tapoPasswordHash"), expected_token)
        self.assertEqual(saved_cfg.get("tapoEmail"), test_email)

    def test_tapo_register_and_device_dispatch(self):
        # Tapo デバイスの登録
        dev_ip = "192.168.11.235"
        reg_resp = self.client.post("/api/onvif/register", json={
            "device": {
                "ip": dev_ip,
                "name": "テストTapoスピーカー",
                "type": "tapo",
                "model": "C212 (Tapo)"
            }
        })
        self.assertEqual(reg_resp.status_code, 200)

        # devices_service で認識されること
        dev = device_manager.find_device(f"tapo:{dev_ip}")
        self.assertIsNotNone(dev)
        self.assertEqual(dev["type"], "tapo")
        self.assertEqual(dev["rawIp"], dev_ip)

        # speech_service マクロ展開テスト
        import asyncio
        all_devs = [
            {"id": "g1", "name": "Google Nest", "ip": "192.168.11.10", "type": "google"},
            {"id": "o1", "name": "ONVIF Cam", "ip": "onvif:192.168.11.20", "type": "onvif"},
            {"id": "t1", "name": "Tapo Cam", "ip": "tapo:192.168.11.235", "type": "tapo"}
        ]
        expanded = asyncio.run(speech_service.resolve_targets(["CAM:ALL"], all_devs))
        self.assertEqual(len(expanded), 2)
        self.assertTrue(any(d["type"] == "onvif" for d in expanded))
        self.assertTrue(any(d["type"] == "tapo" for d in expanded))

        expanded_tapo = asyncio.run(speech_service.resolve_targets(["TAPO:ALL"], all_devs))
        self.assertEqual(len(expanded_tapo), 2)

if __name__ == "__main__":
    unittest.main()
