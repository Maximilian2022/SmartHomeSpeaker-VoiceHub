import unittest
import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app
from app.services.event_service import EventService, event_service
from app.services.dnd_service import dnd_service
from app.services.settings_service import settings_manager
from app.core.security import ACTIVE_SESSIONS

class TestSseEvents(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.orig_admin_password = settings_manager.get().get("adminPassword", "")
        self.orig_dnd = dict(settings_manager.get().get("dnd", {}))
        # テスト実行中は管理者パスワードを一時退避し、時刻依存の定時スケジュール・カレンダー連動を無効化
        settings_manager.set_admin_password("")
        dnd_conf = dict(self.orig_dnd)
        dnd_conf["scheduleEnabled"] = False
        dnd_conf["calendarEnabled"] = False
        settings_manager.update({"dnd": dnd_conf})
        ACTIVE_SESSIONS.clear()

    def tearDown(self):
        settings_manager.set_admin_password(self.orig_admin_password)
        settings_manager.update({"dnd": self.orig_dnd})
        ACTIVE_SESSIONS.clear()

    def test_event_service_pubsub(self):
        """EventService の subscribe / broadcast / unsubscribe を検証"""
        async def run_test():
            svc = EventService()
            q1 = await svc.subscribe()
            q2 = await svc.subscribe()
            self.assertEqual(len(svc._listeners), 2)

            await svc.broadcast("dnd_status", {"isActive": True, "reason": "テストミュート"})

            ev1 = q1.get_nowait()
            ev2 = q2.get_nowait()
            self.assertEqual(ev1["event"], "dnd_status")
            self.assertEqual(ev1["data"]["reason"], "テストミュート")
            self.assertEqual(ev2["event"], "dnd_status")

            await svc.unsubscribe(q1)
            self.assertEqual(len(svc._listeners), 1)
            await svc.unsubscribe(q2)
            self.assertEqual(len(svc._listeners), 0)

        asyncio.run(run_test())

    def test_sse_endpoint_headers_and_initial_event(self):
        """GET /api/events が text/event-stream で初期 dnd_status イベントを返すことを検証"""
        with self.client.stream("GET", "/api/events") as response:
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/event-stream", response.headers.get("content-type", ""))
            self.assertEqual(response.headers.get("cache-control"), "no-cache")
            self.assertEqual(response.headers.get("x-accel-buffering"), "no")

            # 最初のチャンクを読み込む (初期 dnd_status イベント)
            first_chunk = next(response.iter_text())
            self.assertIn("event: dnd_status", first_chunk)
            self.assertIn("data:", first_chunk)

    def test_dnd_mute_and_unmute_broadcast(self):
        """ミュートおよび解除API実行時に SSE イベントが発火することを検証"""
        async def run_test():
            q = await event_service.subscribe()
            try:
                # 1. ミュート実行
                res_mute = self.client.post("/api/dnd/mute", json={"durationMinutes": 15, "reason": "テスト即時ミュート"})
                self.assertEqual(res_mute.status_code, 200)

                # broadcast は asyncio.create_task で非同期実行されるため少し待つ
                await asyncio.sleep(0.05)
                self.assertFalse(q.empty())
                mute_ev = q.get_nowait()
                self.assertEqual(mute_ev["event"], "dnd_status")
                self.assertTrue(mute_ev["data"]["isActive"])
                self.assertEqual(mute_ev["data"]["reason"], "テスト即時ミュート")

                # 2. アンミュート実行
                res_unmute = self.client.post("/api/dnd/unmute")
                self.assertEqual(res_unmute.status_code, 200)

                await asyncio.sleep(0.05)
                self.assertFalse(q.empty())
                unmute_ev = q.get_nowait()
                self.assertEqual(unmute_ev["event"], "dnd_status")
                self.assertFalse(unmute_ev["data"]["isActive"])
            finally:
                await event_service.unsubscribe(q)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
