import unittest
import json
import tempfile
import asyncio
from pathlib import Path
from app.core.log_rotator import SpeakLogRotator, MAX_ACTIVE_LINES
from app.services.history_service import HistoryManager
from app.services.dnd_service import DndService

class TestSpeakLog(unittest.TestCase):
    def test_speak_log_rotator_basic(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            rotator = SpeakLogRotator(log_dir=tmp_path)
            try:
                # 1. エントリ書き込み
                entry1 = {"id": "1", "text": "こんにちは", "status": "success"}
                entry2 = {"id": "2", "text": "テストです", "status": "queued"}
                rotator.write_entry(entry1)
                rotator.write_entry(entry2)

                # 2. ファイル存在と内容確認
                self.assertTrue(rotator.active_file.exists())
                lines = rotator.active_file.read_text(encoding="utf-8").strip().split("\n")
                self.assertEqual(len(lines), 2)
                self.assertEqual(json.loads(lines[0]), entry1)
                self.assertEqual(json.loads(lines[1]), entry2)

                # 3. 最新エントリ取得 (降順: 最新が先頭)
                latest = rotator.read_latest_entries(limit=10)
                self.assertEqual(len(latest), 2)
                self.assertEqual(latest[0]["id"], "2")
                self.assertEqual(latest[1]["id"], "1")
            finally:
                rotator.close()

    def test_speak_log_rotation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            rotator = SpeakLogRotator(log_dir=tmp_path)
            try:
                # MAX_ACTIVE_LINES (1000行) を超えるエントリを書き込み
                for i in range(MAX_ACTIVE_LINES + 5):
                    rotator.write_entry({"id": str(i), "text": f"メッセージ {i}"})

                # active_file が切り詰められ、archive_file に移動していること
                self.assertTrue(rotator.archive_file.exists())
                archive_lines = rotator.archive_file.read_text(encoding="utf-8").strip().split("\n")
                self.assertGreaterEqual(len(archive_lines), MAX_ACTIVE_LINES)

                active_lines = rotator.active_file.read_text(encoding="utf-8").strip().split("\n")
                self.assertEqual(len(active_lines), 5)

                # アーカイブからも最新20件が正しく取得できること
                latest = rotator.read_latest_entries(limit=20)
                self.assertEqual(len(latest), 20)
                self.assertEqual(latest[0]["id"], str(MAX_ACTIVE_LINES + 4))
                self.assertEqual(latest[1]["id"], str(MAX_ACTIVE_LINES + 3))
            finally:
                rotator.close()

    def test_history_manager_integration(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            rotator = SpeakLogRotator(log_dir=tmp_path)
            try:
                manager = HistoryManager()
                manager.rotator = rotator
                manager.history = []

                record = manager.add_entry({
                    "text": "統合テスト音声",
                    "targets": ["リビングTapo"],
                    "source": "api",
                    "status": "success"
                })

                self.assertEqual(record["text"], "統合テスト音声")
                self.assertEqual(len(manager.get_history()), 1)
                self.assertEqual(manager.get_history()[0]["targets"], ["リビングTapo"])

                # ディスク上の speak.log から再ロード
                entries = rotator.read_latest_entries(limit=10)
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]["text"], "統合テスト音声")
            finally:
                rotator.close()

    def test_history_manager_mark_queued_as_released(self):
        """DND保留エントリが再生完了（status: success, wasQueued: True）に更新されること"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            rotator = SpeakLogRotator(log_dir=tmp_path)
            try:
                manager = HistoryManager()
                manager.rotator = rotator
                manager.history = []

                rec1 = manager.add_entry({
                    "text": "保留メッセージ1",
                    "status": "queued",
                    "wasQueued": True,
                    "statusMessage": "DND保留中"
                })
                rec2 = manager.add_entry({
                    "text": "即時メッセージ2",
                    "status": "success",
                    "wasQueued": False
                })

                self.assertEqual(manager.get_history()[1]["status"], "queued")

                # 保留解除を実行
                manager.mark_queued_as_released([rec1["id"]], note="DND保留再生完了")

                # メモリ上での更新確認
                updated_rec1 = next(item for item in manager.get_history() if item["id"] == rec1["id"])
                self.assertEqual(updated_rec1["status"], "success")
                self.assertTrue(updated_rec1["wasQueued"])
                self.assertEqual(updated_rec1["statusMessage"], "DND保留再生完了")

                # ディスク上の speak.log から読み直しても反映されていること
                persisted_entries = rotator.read_latest_entries(limit=10)
                persisted_rec1 = next(item for item in persisted_entries if item["id"] == rec1["id"])
                self.assertEqual(persisted_rec1["status"], "success")
                self.assertTrue(persisted_rec1["wasQueued"])
            finally:
                rotator.close()

    def test_dnd_flush_queue_updates_history(self):
        """DNDキューをフラッシュした際に既存の履歴IDが指定されて再生・更新されること"""
        dnd = DndService()
        dnd.queue = []

        executed_calls = []

        async def mock_speaker_executor(text: str, **kwargs):
            executed_calls.append({"text": text, **kwargs})
            return {"success": True}

        dnd.set_speaker_executor(mock_speaker_executor)

        # テストキュー投入
        dnd.add_to_queue({
            "history_id": "hist_test_999",
            "text": "お風呂が沸きました",
            "targets": ["リビングTapo"]
        })

        self.assertEqual(len(dnd.get_queue()), 1)

        # フラッシュ実行
        flushed_count = asyncio.run(dnd.check_and_flush_queue())
        self.assertEqual(flushed_count, 1)
        self.assertEqual(len(dnd.get_queue()), 0)

        # mock_speaker_executor に existing_history_id が渡されたこと
        self.assertEqual(len(executed_calls), 1)
        self.assertEqual(executed_calls[0]["existing_history_id"], "hist_test_999")
        self.assertEqual(executed_calls[0]["text"], "お風呂が沸きました")
        self.assertTrue(executed_calls[0]["was_queued"])

if __name__ == "__main__":
    unittest.main()
