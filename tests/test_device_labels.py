import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.settings_service import settings_manager
from app.services.devices_service import device_manager

class TestDeviceLabels(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # テスト開始前に settings の deviceLabels と deviceGroups を退避
        self._orig_labels = dict(settings_manager.get().get("deviceLabels", {}))
        self._orig_groups = dict(settings_manager.get().get("deviceGroups", {}))
        # クリーンアップ
        settings_manager.settings["deviceLabels"] = {}
        settings_manager.settings["deviceGroups"] = {
            "LivingGroup": ["192.168.1.10", "192.168.1.11"]
        }

    def tearDown(self):
        # 復元
        settings_manager.settings["deviceLabels"] = self._orig_labels
        settings_manager.settings["deviceGroups"] = self._orig_groups
        settings_manager._save(settings_manager.settings)

    def test_settings_set_and_get_label(self):
        # 1. 正常なラベル設定
        ok, res = settings_manager.set_device_label("group_42000_192_168_1_50", "全体")
        self.assertTrue(ok)
        self.assertEqual(res, "全体")
        self.assertEqual(settings_manager.get_device_labels().get("group_42000_192_168_1_50"), "全体")
        self.assertEqual(settings_manager.get_label_for_device("group_42000_192_168_1_50"), "全体")

        # 2. 同一デバイスのラベル更新
        ok, res = settings_manager.set_device_label("group_42000_192_168_1_50", "家全体")
        self.assertTrue(ok)
        self.assertEqual(res, "家全体")
        self.assertEqual(settings_manager.get_label_for_device("group_42000_192_168_1_50"), "家全体")

        # 3. 空文字で解除
        ok, res = settings_manager.set_device_label("group_42000_192_168_1_50", "")
        self.assertTrue(ok)
        self.assertEqual(res, "")
        self.assertEqual(settings_manager.get_label_for_device("group_42000_192_168_1_50"), "")

    def test_duplicate_label_rejected(self):
        # デバイスAに「リビング」を設定
        ok, _ = settings_manager.set_device_label("dev_a", "リビング")
        self.assertTrue(ok)

        # デバイスBに同じ「リビング」を設定 -> 重複エラー
        ok, err = settings_manager.set_device_label("dev_b", "リビング")
        self.assertFalse(ok)
        self.assertIn("既に他のデバイスで使用されています", err)

        # 大文字小文字を区別せず重複禁止
        ok, _ = settings_manager.set_device_label("dev_c", "MainSpeaker")
        self.assertTrue(ok)
        ok, err = settings_manager.set_device_label("dev_d", "mainspeaker")
        self.assertFalse(ok)
        self.assertIn("既に他のデバイスで使用されています", err)

    def test_reserved_keywords_rejected(self):
        for kw in ["all", "ALL", "default", "GH:ALL", "pc:all", "dlna:all"]:
            ok, err = settings_manager.set_device_label("dev_x", kw)
            self.assertFalse(ok, f"Keyword '{kw}' should be rejected as reserved")
            self.assertIn("予約語", err)

    def test_group_name_conflict_rejected(self):
        # 既存グループ名 "LivingGroup"
        ok, err = settings_manager.set_device_label("dev_x", "LivingGroup")
        self.assertFalse(ok)
        self.assertIn("既存のグループ名と重複", err)

        # 大文字小文字無視
        ok, err = settings_manager.set_device_label("dev_x", "livinggroup")
        self.assertFalse(ok)
        self.assertIn("既存のグループ名と重複", err)

    def test_find_device_by_label_priority(self):
        # 同一表示名「Google Home」のデバイスが複数ある状況をシミュレート
        mock_devices = {
            "192.168.1.10": {
                "id": "group_42000_192_168_1_10",
                "ip": "192.168.1.10:42000",
                "name": "Google Home",
                "model": "Google Cast Group",
                "type": "google"
            },
            "192.168.1.20": {
                "id": "group_42001_192_168_1_20",
                "ip": "192.168.1.20:42001",
                "name": "Google Home",
                "model": "Google Cast Group",
                "type": "google"
            }
        }

        # 192.168.1.20 にラベル「2F全体」を付与
        settings_manager.set_device_label("group_42001_192_168_1_20", "2F全体")

        with patch.object(device_manager, "devices", mock_devices):
            # ラベル「2F全体」で検索
            found = device_manager.find_device("2F全体")
            self.assertIsNotNone(found)
            self.assertEqual(found.get("id"), "group_42001_192_168_1_20")

            # 大文字小文字や英数字でも検索可能
            settings_manager.set_device_label("group_42000_192_168_1_10", "MainGroup")
            found2 = device_manager.find_device("maingroup")
            self.assertIsNotNone(found2)
            self.assertEqual(found2.get("id"), "group_42000_192_168_1_10")

    def test_api_label_endpoints(self):
        # 1. POST /api/devices/label (正常系)
        res = self.client.post("/api/devices/label", json={
            "deviceId": "test_speaker_1",
            "label": "書斎"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["label"], "書斎")
        self.assertEqual(data["labels"]["test_speaker_1"], "書斎")

        # 2. GET /api/devices/labels
        get_res = self.client.get("/api/devices/labels")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["labels"]["test_speaker_1"], "書斎")

        # 3. POST /api/devices/label (重複エラー 400)
        dup_res = self.client.post("/api/devices/label", json={
            "deviceId": "test_speaker_2",
            "label": "書斎"
        })
        self.assertEqual(dup_res.status_code, 400)
        dup_data = dup_res.json()
        self.assertFalse(dup_data["success"])
        self.assertIn("既に他のデバイスで使用されています", dup_data["error"])

        # 4. POST /api/devices/label (解除)
        clear_res = self.client.post("/api/devices/label", json={
            "deviceId": "test_speaker_1",
            "label": ""
        })
        self.assertEqual(clear_res.status_code, 200)
        self.assertEqual(clear_res.json()["label"], "")
        self.assertNotIn("test_speaker_1", clear_res.json()["labels"])

    def test_device_disabled_toggle_api(self):
        """POST /api/devices/toggle-disabled によるデバイス無効化・有効化トグルの検証"""
        target_dev = "dev_192_168_11_200"

        # 1. 無効化 (初回トグル -> disabled=True)
        res1 = self.client.post("/api/devices/toggle-disabled", json={"id": target_dev})
        self.assertEqual(res1.status_code, 200)
        d1 = res1.json()
        self.assertTrue(d1["success"])
        self.assertTrue(d1["disabled"])
        self.assertIn(target_dev, d1["disabledDevices"])

        # 2. GET /api/devices/disabled で確認
        get_res = self.client.get("/api/devices/disabled")
        self.assertEqual(get_res.status_code, 200)
        self.assertIn(target_dev, get_res.json()["disabledDevices"])

        # 3. 再有効化 (2回目トグル -> disabled=False)
        res2 = self.client.post("/api/devices/toggle-disabled", json={"id": target_dev})
        self.assertEqual(res2.status_code, 200)
        d2 = res2.json()
        self.assertTrue(d2["success"])
        self.assertFalse(d2["disabled"])
        self.assertNotIn(target_dev, d2["disabledDevices"])

if __name__ == "__main__":
    unittest.main()
