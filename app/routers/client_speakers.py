import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import StreamingResponse, JSONResponse
from app.core.security import check_admin_auth, extract_client_ip
from app.services.client_speaker_service import client_speaker_service
from app.core.logger import get_logger

router = APIRouter()
log = get_logger("ClientSpeakersRouter")

@router.get("/api/client-speakers/stream")
async def client_speakers_stream(
    request: Request,
    name: str = Query(default="PC Speaker", description="クライアントスピーカーの表示名"),
    id: Optional[str] = Query(default=None, description="一意のクライアントID（未指定時はIP等から自動生成）"),
    platform: str = Query(default="pc", description="プラットフォーム (macos, windows, linux, pc)"),
    _auth = Depends(check_admin_auth)
):
    """
    Windows / Mac / Linux PC 用の超軽量スピーカークライアントが常駐接続する
    Server-Sent Events (SSE) ストリーミングエンドポイント。
    接続中は自動的に VoiceHub のスピーカー一覧に登録され、切断時に自動解除される。
    """
    client_ip = extract_client_ip(request)
    client_id = id.strip() if id and id.strip() else f"pc_{client_ip.replace('.', '_')}"
    
    queue = await client_speaker_service.register(
        client_id=client_id,
        name=name.strip(),
        ip=client_ip,
        platform=platform.strip().lower()
    )

    async def event_generator():
        try:
            # 接続直後の初期ウェルカムイベント
            welcome_data = {
                "status": "connected",
                "clientId": client_id,
                "name": name,
                "serverTime": asyncio.get_event_loop().time()
            }
            yield f"event: connected\ndata: {json.dumps(welcome_data, ensure_ascii=False)}\n\n"

            while True:
                try:
                    # 最大15秒待機。タイムアウト時は keepalive を送信して接続を維持
                    item = await asyncio.wait_for(queue.get(), timeout=15.0)
                    ev_name = item.get("event", "play")
                    ev_data = item.get("data", {})
                    yield f"event: {ev_name}\ndata: {json.dumps(ev_data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            await client_speaker_service.unregister(client_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/api/client-speakers")
async def list_client_speakers(_auth = Depends(check_admin_auth)):
    """現在接続中のクライアントスピーカー一覧を返却"""
    devices = client_speaker_service.get_active_devices()
    return JSONResponse(content={"count": len(devices), "devices": devices})
