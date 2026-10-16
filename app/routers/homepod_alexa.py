from fastapi import APIRouter
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
    return {"enabled": alexa_service.is_enabled()}

@router.post("/api/alexa/token")
async def set_alexa_token(req: AlexaTokenRequest):
    settings.refresh_token = req.token.strip()
    return {"success": True}

@router.post("/api/alexa/logout")
async def alexa_logout():
    if alexa_service.cookie_path.exists():
        alexa_service.cookie_path.unlink()
    settings.refresh_token = ""
    return {"success": True}
