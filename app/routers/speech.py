from typing import Optional, List, Union
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from app.services.speech_service import speech_service
from app.services.tts_service import tts_service
from app.core.security import validate_webhook_token, check_tunnel_access, is_tunnel_request

router = APIRouter()

class SayRequest(BaseModel):
    text: str
    devices: Optional[Union[str, List[str]]] = None
    targets: Optional[Union[str, List[str]]] = None
    voice: Optional[str] = None
    rate: Optional[str] = None
    pitch: Optional[str] = None
    volumeLevel: Optional[Union[float, int, str]] = None
    chime: Optional[str] = None
    async_mode: Optional[bool] = Field(default=None, alias="async")
    wait: Optional[bool] = None
    urgent: Optional[bool] = False
    bypassDnd: Optional[bool] = None
    client: Optional[str] = None
    token: Optional[str] = None

@router.post("/api/say")
@router.post("/api/webhook")
async def api_say_post(
    req: SayRequest,
    request: Request,
    background_tasks: BackgroundTasks
):
    check_tunnel_access(request)
    validate_webhook_token(request, req.token)

    targets = req.targets or req.devices
    client_name = req.client or request.headers.get("user-agent", "Webhook").split("/")[0]
    is_urgent = bool(req.urgent or req.bypassDnd)

    # 外部トンネル・外部Webhook経由、または明示的に async が指定されたときは即時応答
    is_tunnel = is_tunnel_request(request)
    is_explicit_sync = (req.wait is True)
    is_explicit_async = (req.async_mode is True or req.wait is False)
    should_run_async = is_explicit_async or (is_tunnel and not is_explicit_sync)

    if should_run_async:
        background_tasks.add_task(
            speech_service.speak,
            text=req.text,
            targets=targets,
            voice=req.voice,
            rate=req.rate,
            pitch=req.pitch,
            volume_level=req.volumeLevel,
            chime=req.chime,
            client_name=client_name,
            urgent=is_urgent
        )
        norm_targets = targets if isinstance(targets, list) else ([targets] if targets else ["default"])
        return {
            "success": True,
            "status": "success",
            "message": "Speech request accepted for async processing",
            "text": req.text,
            "results": [{"target": str(t), "status": "success"} for t in norm_targets]
        }
    else:
        result = await speech_service.speak(
            text=req.text,
            targets=targets,
            voice=req.voice,
            rate=req.rate,
            pitch=req.pitch,
            volume_level=req.volumeLevel,
            chime=req.chime,
            client_name=client_name,
            urgent=is_urgent
        )
        return result

@router.get("/api/preview")
async def api_preview_get(
    text: str,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    pitch: Optional[str] = None
):
    """ブラウザでの事前試聴プレビュー用"""
    if not text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    try:
        speech = await tts_service.synthesize(
            text=text,
            voice=voice or "ja-JP-NanamiNeural",
            rate=rate or "+0%",
            pitch=pitch or "+0Hz",
            chime="none"
        )
        return FileResponse(speech["filepath"], media_type="audio/mp3")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/say")
async def api_say_get(
    text: str,
    request: Request,
    devices: Optional[str] = None,
    targets: Optional[str] = None,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    pitch: Optional[str] = None,
    volumeLevel: Optional[str] = None,
    chime: Optional[str] = None,
    urgent: bool = False
):
    check_tunnel_access(request)
    validate_webhook_token(request)

    target_val = targets or devices
    result = await speech_service.speak(
        text=text,
        targets=target_val,
        voice=voice,
        rate=rate,
        pitch=pitch,
        volume_level=volumeLevel,
        chime=chime,
        client_name="GET-API",
        urgent=urgent
    )
    return result

@router.get("/api/tts/voices")
async def api_tts_voices():
    return tts_service.get_voices()
