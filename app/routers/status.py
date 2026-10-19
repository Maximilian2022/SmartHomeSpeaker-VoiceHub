import time
from typing import Dict, Any
from fastapi import APIRouter, Request
from app.config import settings
from app.services.tts_service import tts_service
from app.services.devices_service import device_manager
from app.services.alexa_service import alexa_service
from app.services.homepod_service import homepod_service
from app.core.security import is_tunnel_request

router = APIRouter()
START_TIME = time.time()

@router.get("/api/status")
async def get_system_status(request: Request) -> Dict[str, Any]:
    def_ip = device_manager.get_default_device_ip()
    def_dev = device_manager.find_device(def_ip) if def_ip else None
    def_name = def_dev.get("name") if def_dev else ""

    import sys
    is_tunnel = is_tunnel_request(request)
    # 外部トンネル経由の場合は生トークンを決して返さない
    token_str = None if is_tunnel else (settings.webhook_token or None)

    return {
        "serverIp": settings.effective_wireless_ip,
        "port": settings.server_port,
        "defaultDeviceIp": def_ip,
        "defaultDeviceName": def_name,
        "tunnelDomain": settings.tunnel_domain or None,
        "cacheStats": tts_service.get_cache_stats(),
        "alexaEnabled": alexa_service.is_enabled(),
        "alexaConfigured": alexa_service.is_enabled(),
        "homepodCount": len(homepod_service.devices_cache),
        "pythonVersion": sys.version.split()[0],
        "uptime": int(time.time() - START_TIME),
        "hasWebhookToken": bool(settings.webhook_token),
        "webhookToken": token_str
    }

@router.get("/api/voices")
async def get_voices() -> Dict[str, Any]:
    voices = await tts_service.get_voices()
    return {
        "voices": voices,
        "defaultVoice": tts_service.get_default_voice_id(),
        "isAzureActive": tts_service.is_azure_active()
    }

