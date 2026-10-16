import time
from typing import Dict, Any
from fastapi import APIRouter
from app.config import settings
from app.services.tts_service import tts_service
from app.services.devices_service import device_manager
from app.services.alexa_service import alexa_service
from app.services.homepod_service import homepod_service

router = APIRouter()
START_TIME = time.time()

@router.get("/api/status")
async def get_system_status() -> Dict[str, Any]:
    return {
        "serverIp": settings.wireless_ip or "127.0.0.1",
        "port": settings.server_port,
        "defaultDeviceIp": device_manager.get_default_device_ip(),
        "tunnelDomain": settings.tunnel_domain or None,
        "cacheStats": tts_service.get_cache_stats(),
        "alexaEnabled": alexa_service.is_enabled(),
        "alexaConfigured": alexa_service.is_enabled(),
        "homepodCount": len(homepod_service.devices_cache),
        "pythonVersion": "3.12",
        "uptime": int(time.time() - START_TIME),
        "hasWebhookToken": bool(settings.webhook_token),
        "webhookToken": settings.webhook_token or None
    }

@router.get("/api/voices")
async def get_voices() -> Dict[str, Any]:
    return {
        "voices": tts_service.get_voices(),
        "defaultVoice": settings.default_voice
    }
