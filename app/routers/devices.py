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

class DeviceVolumeRequest(BaseModel):
    volume: float
    id: Optional[str] = None
    ip: Optional[str] = None

@router.post("/api/devices/{device_id}/volume")
@router.post("/api/devices/volume")
async def set_device_volume(req: DeviceVolumeRequest, device_id: Optional[str] = None):
    target_id = device_id or req.id or req.ip or ""
    if not target_id:
        return {"success": False, "error": "device_id is required"}

    dev = device_manager.find_device(target_id)
    if not dev:
        return {"success": False, "error": f"Device not found: {target_id}"}

    dtype = dev.get("type", "google")
    vol_input = req.volume
    vol_ratio = vol_input / 100.0 if vol_input > 1.0 else vol_input
    vol_percent = int(vol_ratio * 100)

    from app.services.cast_service import cast_service
    from app.services.alexa_service import alexa_service
    from app.services.homepod_service import homepod_service

    success = False
    if dtype == "google":
        ip_val = str(dev.get("ip", ""))
        host = ip_val.split(":")[0] if ":" in ip_val else ip_val
        port = int(dev.get("port", 8009))
        success = await cast_service.set_volume(host, port, vol_ratio)
    elif dtype == "alexa":
        success = await alexa_service.set_volume(dev.get("name", ""), vol_percent)
    elif dtype == "homepod":
        raw_ip = dev.get("rawIp") or dev.get("ip", "")
        success = await homepod_service.set_volume(raw_ip, vol_percent)
    else:
        success = True

    # 個別音量キャッシュを保存
    settings = settings_manager.get()
    dev_vols = settings.get("deviceVolumes", {})
    dev_vols[target_id] = vol_percent
    settings_manager.update({"deviceVolumes": dev_vols})

    return {
        "success": success,
        "deviceId": target_id,
        "volume": vol_percent,
        "type": dtype
    }
