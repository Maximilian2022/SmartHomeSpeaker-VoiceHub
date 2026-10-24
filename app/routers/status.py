import time
from typing import Dict, Any
from fastapi import APIRouter, Request
from app.config import settings
from app.services.tts_service import tts_service
from app.services.devices_service import device_manager
from app.services.alexa_service import alexa_service
from app.services.homepod_service import homepod_service
from app.services.settings_service import settings_manager
from app.services.update_service import update_service
from app.version import __version__
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
    # - 管理者パスワードが設定されている場合: 管理者セッション認証済み (Cookie auth_token) の場合のみトークン平文を返却し、未認証時は隠蔽 (None)
    # - 管理者パスワード未設定の場合: 宅内LAN直接アクセスのみ平文返却、Cloudflare Tunnel 経由時は隠蔽 (None)
    admin_pass = get_effective_admin_password()
    cookie_token = request.cookies.get("auth_token")
    is_admin_session = bool(cookie_token and cookie_token in ACTIVE_SESSIONS)
    
    if is_admin_session:
        token_str = effective_token or None
    elif not admin_pass and not is_tunnel:
        token_str = effective_token or None
    else:
        token_str = None

    gui_token = settings_manager.get().get("webhookToken")
    env_token = (settings.webhook_token or "").strip()
    token_source = "settings" if gui_token else ("env" if env_token else "none")

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
        "webhookToken": token_str,
        "webhookTokenSource": token_source,
        "version": f"v{__version__}",
        "latestVersion": (update_service._cached_release or {}).get("latestVersion", f"v{__version__}"),
        "hasUpdate": (update_service._cached_release or {}).get("hasUpdate", False)
    }

@router.get("/api/voices")
async def get_voices() -> Dict[str, Any]:
    voices = await tts_service.get_voices()
    return {
        "voices": voices,
        "defaultVoice": tts_service.get_default_voice_id(),
        "isAzureActive": tts_service.is_azure_active()
    }

