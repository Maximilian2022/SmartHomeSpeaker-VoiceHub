import asyncio
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from app.core.security import check_admin_auth
from app.services.event_service import event_service
from app.services.dnd_service import dnd_service
from app.core.logger import get_logger

router = APIRouter()
log = get_logger("EventsRouter")

@router.get("/api/events")
@router.get("/api/events/stream")
async def events_stream(request: Request, _auth = Depends(check_admin_auth)):
    """
    Server-Sent Events (SSE) ストリーミングエンドポイント。
    DND / ミュート状態の変更や各種リアルタイム更新イベントをブラウザへプッシュ配信する。
    """
    queue = await event_service.subscribe()

    # 接続直後に現在の初期状態 (DND ステータス) を送信
    current_dnd_status = dnd_service.get_global_status()
    initial_events = [
        {
            "event": "dnd_status",
            "data": current_dnd_status
        }
    ]

    return StreamingResponse(
        event_service.event_generator(queue, initial_events=initial_events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
