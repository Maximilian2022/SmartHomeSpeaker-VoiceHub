import asyncio
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, Depends, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse
from app.core.security import check_admin_auth, extract_client_ip
from app.services.client_speaker_service import client_speaker_service
from app.services.settings_service import settings_manager
from app.core.logger import get_logger

router = APIRouter()
log = get_logger("ClientSpeakersRouter")


def _get_server_script_hash() -> str:
    """サーバー上の最新 voicehub_speaker.py の SHA-256 ハッシュ（先頭16文字）を算出"""
    candidates = [
        Path("/app/public/clients/speaker/voicehub_speaker.py"),
        Path("/app/clients/speaker/voicehub_speaker.py"),
        Path("public/clients/speaker/voicehub_speaker.py"),
        Path("clients/speaker/voicehub_speaker.py"),
    ]
    for p in candidates:
        try:
            if p.exists():
                return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        except Exception:
            pass
    return ""


@router.get("/api/client-speakers/stream")
async def client_speakers_stream(
    request: Request,
    name: str = Query(default="PC Speaker", description="クライアントスピーカーの表示名"),
    id: Optional[str] = Query(default=None, description="一意のクライアントID（未指定時はIP等から自動生成）"),
    platform: str = Query(default="pc", description="プラットフォーム (macos, windows, linux, pc)"),
    outputs: Optional[str] = Query(default=None, description="検出されたオーディオ出力デバイス一覧のJSON文字列"),
    script_hash: Optional[str] = Query(default=None, description="クライアント側のスクリプトハッシュ"),
    _auth = Depends(check_admin_auth)
):
    """
    Windows / Mac / Linux PC 用の超軽量スピーカークライアントが常駐接続する
    Server-Sent Events (SSE) ストリーミングエンドポイント。
    接続中は自動的に VoiceHub のスピーカー一覧に登録され、切断時に自動解除される。
    """
    client_ip = extract_client_ip(request)
    client_id = id.strip() if id and id.strip() else f"pc_{client_ip.replace('.', '_')}"

    parsed_outputs: List[Dict[str, Any]] = []
    if outputs:
        try:
            raw = json.loads(outputs)
            if isinstance(raw, list):
                parsed_outputs = [x for x in raw if isinstance(x, dict)]
        except Exception as e:
            log.warning(f"Failed to parse client outputs JSON for {client_id}: {e}")

    queue = await client_speaker_service.register(
        client_id=client_id,
        name=name.strip(),
        ip=client_ip,
        platform=platform.strip().lower(),
        outputs=parsed_outputs,
        script_hash=(script_hash or "").strip()
    )

    async def event_generator():
        try:
            srv_hash = _get_server_script_hash()
            # 接続直後の初期ウェルカムイベント（scriptHash によりクライアント側の自動自己更新をトリガー）
            welcome_data = {
                "status": "connected",
                "clientId": client_id,
                "name": name,
                "scriptHash": srv_hash,
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
    """現在接続中のクライアントスピーカー一覧と各PCの全オーディオ出力設定を返却"""
    srv_hash = _get_server_script_hash()
    devices = client_speaker_service.get_active_devices(include_disabled=False)
    all_outputs = client_speaker_service.get_active_devices(include_disabled=True)
    clients = client_speaker_service.get_connected_clients_summary(server_script_hash=srv_hash)
    return JSONResponse(content={
        "count": len(devices),
        "pcCount": len(clients),
        "devices": devices,
        "allOutputs": all_outputs,
        "clients": clients,
        "scriptHash": srv_hash
    })


@router.post("/api/client-speakers/outputs")
async def report_client_speaker_outputs(
    payload: Dict[str, Any] = Body(...),
    _auth = Depends(check_admin_auth)
):
    """クライアントからのオーディオ出力デバイス再スキャン結果を受け取って即時反映"""
    client_id = str(payload.get("clientId") or "").strip()
    outputs = payload.get("outputs")
    script_hash = payload.get("scriptHash")
    if not client_id or not isinstance(outputs, list):
        return JSONResponse(status_code=400, content={"error": "clientId and outputs list are required"})

    ok = await client_speaker_service.update_outputs(client_id, outputs, script_hash=script_hash)
    return JSONResponse(content={"success": ok, "clientId": client_id, "outputCount": len(outputs)})


@router.post("/api/client-speakers/config")
async def update_client_speaker_config(
    payload: Dict[str, Any] = Body(...),
    _auth = Depends(check_admin_auth)
):
    """
    Web UI から特定の PC 出力デバイスの有効/無効 (enabled)、表示名 (customName)、
    メイン出力指定 (isPrimary: ALL / PC:ALL 一斉再生時の対象) を更新して永続化
    """
    client_id = str(payload.get("clientId") or "").strip()
    output_key = str(payload.get("outputKey") or "").strip()
    if not client_id or not output_key:
        return JSONResponse(status_code=400, content={"error": "clientId and outputKey are required"})

    enabled = payload.get("enabled")
    custom_name = payload.get("customName")
    is_primary = payload.get("isPrimary")

    settings_manager.update_pc_speaker_output(
        client_id=client_id,
        output_key=output_key,
        enabled=enabled,
        custom_name=custom_name,
        is_primary=is_primary
    )

    srv_hash = _get_server_script_hash()
    devices = client_speaker_service.get_active_devices(include_disabled=False)
    clients = client_speaker_service.get_connected_clients_summary(server_script_hash=srv_hash)
    return JSONResponse(content={
        "success": True,
        "count": len(devices),
        "pcCount": len(clients),
        "devices": devices,
        "clients": clients
    })


@router.post("/api/client-speakers/rescan")
async def rescan_and_update_client_speakers(
    payload: Optional[Dict[str, Any]] = Body(default=None),
    _auth = Depends(check_admin_auth)
):
    """接続中の PC クライアントへ出力デバイス再スキャン (rescan) およびスクリプト自動更新チェック (self_update) を送信"""
    target_id = str((payload or {}).get("clientId") or "").strip() or None
    srv_hash = _get_server_script_hash()
    sent_rescan = await client_speaker_service.broadcast_control_event("rescan", {}, target_client_id=target_id)
    sent_update = 0
    if srv_hash:
        sent_update = await client_speaker_service.broadcast_control_event(
            "self_update",
            {"scriptHash": srv_hash},
            target_client_id=target_id
        )
    return JSONResponse(content={
        "success": True,
        "rescanSent": sent_rescan,
        "updateCheckSent": sent_update,
        "scriptHash": srv_hash
    })
