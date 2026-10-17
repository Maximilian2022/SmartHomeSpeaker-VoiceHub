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
    from_user: Optional[str] = Field(default=None, alias="from")
    sender: Optional[str] = None
    source: Optional[str] = None
    sourceLabel: Optional[str] = None
    token: Optional[str] = None

def extract_client_ip(request: Request) -> str:
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    x_forwarded = request.headers.get("x-forwarded-for")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"

def detect_user_agent_client(ua: str) -> str:
    ua_lower = ua.lower()
    if "discord" in ua_lower:
        return "Discord"
    if "slack" in ua_lower:
        return "Slack"
    if "ifttt" in ua_lower:
        return "IFTTT"
    if "homeassistant" in ua_lower or "home-assistant" in ua_lower or "hass" in ua_lower:
        return "Home Assistant"
    if "curl" in ua_lower:
        return "curl"
    if "postman" in ua_lower:
        return "Postman"
    if "python-requests" in ua_lower or "httpx" in ua_lower or "aiohttp" in ua_lower:
        return "Python Script"
    if "node" in ua_lower or "axios" in ua_lower:
        return "Node.js Script"
    return ""

def resolve_client_metadata(request: Request, req_client: Optional[str] = None, req_source: Optional[str] = None, req_source_label: Optional[str] = None):
    from app.services.settings_service import settings_manager
    client_ip = extract_client_ip(request)
    ua = request.headers.get("user-agent", "")
    
    # 経路判定 (source)
    is_tunnel = is_tunnel_request(request)
    source = req_source
    if not source:
        if is_tunnel:
            source = "tunnel_webhook"
        else:
            referer = request.headers.get("referer", "")
            origin = request.headers.get("origin", "")
            sec_fetch = request.headers.get("sec-fetch-site", "")
            if ":8080" in referer or ":8080" in origin or sec_fetch == "same-origin":
                source = "web_ui"
            else:
                source = "api"

    # ラベル構築 (sourceLabel)
    source_label = req_source_label
    if not source_label:
        if source == "tunnel_webhook":
            source_label = "Cloudflare Tunnel"
        elif source == "web_ui":
            source_label = "Web UI (即時発言)"
        elif source == "schedule":
            source_label = "定期スケジュール"
        elif source == "calendar":
            source_label = "カレンダー連携"
        else:
            source_label = "外部 API / Webhook"

    # クライアント名判定 (clientName)
    ip_aliases = settings_manager.get().get("ipAliases", {})
    alias_name = ip_aliases.get(client_ip)
    ua_client = detect_user_agent_client(ua)

    if req_client and req_client.strip():
        client_name = req_client.strip()
    elif alias_name:
        client_name = alias_name
    elif ua_client:
        client_name = ua_client
    elif source == "web_ui":
        client_name = "Web UI"
    elif client_ip and client_ip not in ("127.0.0.1", "::1"):
        client_name = client_ip
    else:
        client_name = "Webhook"

    return client_ip, client_name, source, source_label

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
    raw_client = req.client or req.from_user or req.sender
    client_ip, client_name, source, source_label = resolve_client_metadata(request, raw_client, req.source, req.sourceLabel)
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
            client_ip=client_ip,
            source=source,
            source_label=source_label,
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
            client_ip=client_ip,
            source=source,
            source_label=source_label,
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
    client_ip, client_name, source, source_label = resolve_client_metadata(request, None, None, None)
    result = await speech_service.speak(
        text=text,
        targets=target_val,
        voice=voice,
        rate=rate,
        pitch=pitch,
        volume_level=volumeLevel,
        chime=chime,
        client_name=client_name,
        client_ip=client_ip,
        source=source,
        source_label=source_label,
        urgent=urgent
    )
    return result

@router.get("/api/tts/voices")
async def api_tts_voices():
    return tts_service.get_voices()
