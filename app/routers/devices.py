import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.devices_service import device_manager
from app.services.settings_service import settings_manager

router = APIRouter()

class DefaultDeviceRequest(BaseModel):
    id: Optional[str] = None
    ip: Optional[str] = None

@router.get("/api/devices")
async def get_devices():
    devs = await device_manager.get_devices()
    return {
        "devices": devs,
        "defaultIp": device_manager.get_default_device_ip()
    }

@router.post("/api/devices/rescan-all")
@router.post("/api/devices/scan")
async def rescan_all_devices():
    await asyncio.to_thread(device_manager.scan_google_devices)
    devs = await device_manager.get_devices()
    return {
        "success": True,
        "count": len(devs),
        "devices": devs,
        "defaultIp": device_manager.get_default_device_ip()
    }

@router.get("/api/devices/default")
async def get_default_device():
    return {"defaultDeviceId": device_manager.get_default_device_ip()}

@router.post("/api/devices/default")
async def set_default_device(req: DefaultDeviceRequest):
    dev_id = req.id or req.ip or ""
    saved = device_manager.set_default_device_ip(dev_id)
    return {"success": True, "defaultDeviceId": saved}

@router.get("/api/groups")
async def get_device_groups():
    return settings_manager.get().get("deviceGroups", {})
