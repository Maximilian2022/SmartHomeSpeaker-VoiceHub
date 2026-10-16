from typing import Optional, List, Union
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from app.services.speech_service import speech_service
from app.services.tts_service import tts_service
from app.core.security import validate_webhook_token, check_tunnel_access

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
    wait: Optional[bool] = False
    urgent: Optional[bool] = False
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

    # Webhook 呼び出し時の即時応答 (async_mode またはデフォルト)
    is_async = req.async_mode if req.async_mode is not None else (not req.wait)

    if is_async:
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
            urgent=bool(req.urgent)
        )
        return {
            "status": "success",
            "message": "Speech request accepted for async processing",
            "text": req.text
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
            urgent=bool(req.urgent)
        )
        return result

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
