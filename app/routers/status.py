import time
from typing import Dict, Any
from fastapi import APIRouter, Request
from app.config import settings
from app.services.tts_service import tts_service
from app.services.devices_service import device_manager
from app.services.alexa_service import alexa_service
from app.services.homepod_service import homepod_service
from app.services.settings_service import settings_manager
from app.core.security import is_tunnel_request, ACTIVE_SESSIONS, get_effective_admin_password

router = APIRouter()
START_TIME = time.time()

@router.get("/health")
@router.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """コンテナ・プロキシ監視用の超軽量ヘルスチェックエンドポイント (無認証)"""
    return {
        "status": "ok",
        "app": "SmartHomeSpeaker-VoiceHub",
        "uptime": int(time.time() - START_TIME)
    }

@router.get("/api/status")
async def get_system_status(request: Request) -> Dict[str, Any]:
    def_ip = device_manager.get_default_device_ip()
    def_dev = device_manager.find_device(def_ip) if def_ip else None
    def_name = def_dev.get("name") if def_dev else ""

    import sys
    is_tunnel = is_tunnel_request(request)
    effective_token = settings_manager.get_webhook_token()
    
    # セキュリティ方針:
    # - LAN / 直接接続: GUI設定・ビルダー表示のため生トークンを返却
    # - Cloudflare Tunnel (外部): 管理者セッション認証済み (auth_token Cookie) の場合のみトークンを返却。未認証外部アクセス時は隠蔽 (None)
    cookie_token = request.cookies.get("auth_token")
    is_admin_session = bool(cookie_token and cookie_token in ACTIVE_SESSIONS)
    
    if not is_tunnel or is_admin_session:
        token_str = effective_token or None
    else:
        token_str = None

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
        "hasWebhookToken": bool(effective_token),
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

