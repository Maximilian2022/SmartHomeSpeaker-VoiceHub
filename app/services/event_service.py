import asyncio
import json
from typing import Any, Dict, Set, Optional
from app.core.logger import get_logger

log = get_logger("Events")

class EventService:
    """
    Server-Sent Events (SSE) を用いて、サーバー側で発生したイベント
    (DND状態変化、音声再生状況等) を接続中のブラウザクライアントへ
    リアルタイムにプッシュ配信するサービス
    """

    def __init__(self):
        self._listeners: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        """新しいクライアント接続用のイベントキューを生成・登録"""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._listeners.add(queue)
            count = len(self._listeners)
        log.info(f"SSE client connected. Active listeners: {count}")
        return queue

    async def unsubscribe(self, queue: asyncio.Queue):
        """クライアント切断時にキューを削除"""
        async with self._lock:
            self._listeners.discard(queue)
            count = len(self._listeners)
        log.info(f"SSE client disconnected. Active listeners: {count}")

    async def broadcast(self, event_type: str, data: Any):
        """接続中の全クライアントにイベントをブロードキャスト"""
        async with self._lock:
            listeners = list(self._listeners)

        if not listeners:
            return

        payload = {
            "event": event_type,
            "data": data
        }

        for q in listeners:
            try:
                if q.full():
                    try:
                        q.get_nowait()  # 古い未受領イベントを押し出して詰まりを防止
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(payload)
            except Exception as e:
                log.debug(f"Failed to put event into queue: {e}")

    def broadcast_sync(self, event_type: str, data: Any):
        """非非同期コンテキストからブロードキャストを呼び出すヘルパー"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(event_type, data))
        except RuntimeError:
            pass

    async def event_generator(self, queue: asyncio.Queue, initial_events: Optional[list] = None):
        """
        FastAPI StreamingResponse 用の SSE イベントジェネレータ。
        定期的な keepalive ping を送信してプロキシやブラウザのタイムアウトを防ぐ。
        """
        try:
            # 初期イベントがあれば送信
            if initial_events:
                for ev in initial_events:
                    ev_name = ev.get("event", "message")
                    ev_data = ev.get("data", {})
                    yield f"event: {ev_name}\ndata: {json.dumps(ev_data, ensure_ascii=False)}\n\n"

            while True:
                try:
                    # 最大15秒待機。タイムアウトした場合は keepalive コメント行を送信
                    item = await asyncio.wait_for(queue.get(), timeout=15.0)
                    ev_name = item.get("event", "message")
                    ev_data = item.get("data", {})
                    yield f"event: {ev_name}\ndata: {json.dumps(ev_data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            await self.unsubscribe(queue)

event_service = EventService()
