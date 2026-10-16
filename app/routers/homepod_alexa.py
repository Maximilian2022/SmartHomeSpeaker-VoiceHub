import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.homepod_service import homepod_service
from app.services.alexa_service import alexa_service
from app.config import settings

router = APIRouter()

class AlexaTokenRequest(BaseModel):
    token: str

@router.get("/api/homepod/status")
async def homepod_status():
    return {"devices": homepod_service.devices_cache}

@router.post("/api/homepod/scan")
async def homepod_scan():
    devs = await homepod_service.scan_devices(timeout=3)
    return {"devices": devs}

@router.get("/api/alexa/status")
async def alexa_status():
    host_ip = settings.wireless_ip or "127.0.0.1"
    return alexa_service.get_auth_status(host_ip)

@router.post("/api/alexa/auth/start")
async def alexa_auth_start():
    host_ip = settings.wireless_ip or "127.0.0.1"
    try:
        result = await alexa_service.start_proxy_auth(host_ip, port=8081)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/alexa/auth/stop")
async def alexa_auth_stop():
    alexa_service.stop_proxy_auth()
    return {"success": True}

@router.post("/api/alexa/token")
async def set_alexa_token(req: AlexaTokenRequest):
    token = req.token.strip()
    if not token.startswith("Atnr|"):
        raise HTTPException(status_code=400, detail="無効なリフレッシュトークン形式です (Atnr|... から始まる必要があります)")
    settings.refresh_token = token
    # alexa_credentials.json にも保存
    try:
        creds = {"refreshToken": token}
        alexa_service.credentials_path.write_text(json.dumps(creds, indent=2), encoding="utf-8")
    except Exception:
        pass
    return {"success": True}

@router.post("/api/alexa/logout")
async def alexa_logout():
    alexa_service.logout()
    return {"success": True}
