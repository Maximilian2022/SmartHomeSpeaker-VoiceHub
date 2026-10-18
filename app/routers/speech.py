from typing import Optional, List, Union, Dict, Any
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
    voices = await tts_service.get_voices()
    return voices

@router.get("/api/tts/providers")
async def api_tts_providers(request: Request):
    return tts_service.get_providers_status()

class TtsProviderTestRequest(BaseModel):
    provider: str
    type: Optional[str] = None
    engineType: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    baseUrl: Optional[str] = None
    apiKey: Optional[str] = None
    region: Optional[str] = None
    timeoutSeconds: Optional[float] = None
    preload: Optional[bool] = None

@router.post("/api/tts/providers/test")
async def api_tts_providers_test(req: TtsProviderTestRequest, request: Request):
    from app.services.tts import (
        VoicevoxProvider,
        SharevoxProvider,
        CoeiroinkProvider,
        GcpTtsProvider,
        AzureTtsProvider
    )

    pid = req.provider.lower()
    conf = dict(req.config or {})
    for k in ["baseUrl", "apiKey", "region", "timeoutSeconds", "preload", "type", "engineType"]:
        val = getattr(req, k, None)
        if val is not None and k not in conf:
            conf[k] = val

    # エンジン種別の判定 (pid または type / engineType)
    resolved_type = (conf.get("type") or conf.get("engineType") or pid).lower()

    try:
        if resolved_type in ["voicevox", "voicevox_family"] or "voicevox" in pid:
            url = conf.get("baseUrl") or "http://127.0.0.1:50021"
            timeout = float(conf.get("timeoutSeconds") or 5.0)
            p = VoicevoxProvider(base_url=url, enabled=True, timeout_seconds=timeout)
            if not await p.is_available():
                return {"success": False, "isAvailable": False, "message": f"VOICEVOX サーバー ({url}) に接続できませんでした。URLまたはサーバー稼働状態を確認してください。"}
            voices = await p.get_voices()
            init_ok = await p.initialize_speaker("voicevox:2")
            return {
                "success": True,
                "isAvailable": True,
                "message": f"VOICEVOX 接続成功！{len(voices)} 件の話者・スタイルを検出しました（四国めたん事前初期化: {'完了' if init_ok else 'スキップ'}）。",
                "voicesCount": len(voices),
                "voices": voices
            }

        elif resolved_type == "sharevox" or "sharevox" in pid:
            url = conf.get("baseUrl") or "http://127.0.0.1:50025"
            timeout = float(conf.get("timeoutSeconds") or 5.0)
            p = SharevoxProvider(base_url=url, enabled=True, timeout_seconds=timeout)
            if not await p.is_available():
                return {"success": False, "isAvailable": False, "message": f"SHAREVOX サーバー ({url}) に接続できませんでした。URLを確認してください。"}
            voices = await p.get_voices()
            init_ok = await p.initialize_speaker("sharevox:21")
            return {
                "success": True,
                "isAvailable": True,
                "message": f"SHAREVOX 接続成功！{len(voices)} 件の話者を検出しました（らごぱすブラック事前初期化: {'完了' if init_ok else 'スキップ'}）。",
                "voicesCount": len(voices),
                "voices": voices
            }

        elif resolved_type == "coeiroink" or "coeiroink" in pid:
            url = conf.get("baseUrl") or "http://127.0.0.1:50031"
            timeout = float(conf.get("timeoutSeconds") or 5.0)
            p = CoeiroinkProvider(base_url=url, enabled=True, timeout_seconds=timeout)
            if not await p.is_available():
                return {"success": False, "isAvailable": False, "message": f"COEIROINK サーバー ({url}) に接続できませんでした。URLを確認してください。"}
            voices = await p.get_voices()
            return {
                "success": True,
                "isAvailable": True,
                "message": f"COEIROINK 接続成功！{len(voices)} 件の話者・スタイルを検出しました。",
                "voicesCount": len(voices),
                "voices": voices
            }

        elif pid == "gcp":
            key = (conf.get("apiKey") or "").strip()
            if not key:
                return {"success": False, "isAvailable": False, "message": "GCP API Key を入力してください。"}
            p = GcpTtsProvider(api_key=key, enabled=True)
            if not await p.is_available():
                return {"success": False, "isAvailable": False, "message": "Google Cloud Text-to-Speech API に接続できませんでした。API Key の有効性と権限を確認してください。"}
            voices = await p.get_voices()
            return {
                "success": True,
                "isAvailable": True,
                "message": f"Google Cloud TTS 接続成功！{len(voices)} 件の日本語音声を認識しました。",
                "voicesCount": len(voices),
                "voices": voices
            }

        elif pid == "azure":
            key = (conf.get("apiKey") or "").strip()
            region = (conf.get("region") or "japaneast").strip()
            if not key:
                return {"success": False, "isAvailable": False, "message": "Azure Speech Key を入力してください。"}
            p = AzureTtsProvider(api_key=key, region=region, enabled=True)
            if not await p.is_available():
                return {"success": False, "isAvailable": False, "message": f"Azure Speech サービス (リージョン: {region}) に接続できませんでした。Key またはリージョンを確認してください。"}
            voices = await p.get_voices()
            return {
                "success": True,
                "isAvailable": True,
                "message": f"Azure Speech 接続成功！{len(voices)} 件の日本語音声を認識しました。",
                "voicesCount": len(voices),
                "voices": voices
            }

        else:
            return {"success": False, "message": f"未知のプロバイダーです: {pid}"}

    except Exception as e:
        return {"success": False, "message": f"テスト中にエラーが発生しました: {str(e)}"}

class TtsProvidersSettingsUpdateRequest(BaseModel):
    tts_providers: Dict[str, Any]

@router.put("/api/tts/providers/settings")
async def api_tts_providers_settings_update(req: TtsProvidersSettingsUpdateRequest, request: Request):
    from app.services.settings_service import settings_manager
    updated = settings_manager.update({"tts_providers": req.tts_providers})
    tts_service.sync_settings()
    return {"success": True, "settings": updated.get("tts_providers", {})}

