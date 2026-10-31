import asyncio
from typing import Dict, Any, Optional, List
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.services.devices_service import device_manager
from app.services.settings_service import settings_manager

router = APIRouter()

class DefaultDeviceRequest(BaseModel):
    id: Optional[str] = None
    ip: Optional[str] = None

class DeviceFavoritesRequest(BaseModel):
    favorites: List[str]

class DeviceFavoriteToggleRequest(BaseModel):
    ip: Optional[str] = None
    id: Optional[str] = None

class DeviceDisabledToggleRequest(BaseModel):
    ip: Optional[str] = None
    id: Optional[str] = None

class DeviceLabelRequest(BaseModel):
    id: Optional[str] = None
    deviceId: Optional[str] = None
    ip: Optional[str] = None
    label: Optional[str] = None

@router.get("/api/devices")
async def get_devices():
    devs = await device_manager.get_devices()
    return {
        "devices": devs,
        "defaultIp": device_manager.get_default_device_ip(),
        "favorites": settings_manager.get_favorite_devices(),
        "disabledDevices": settings_manager.get_disabled_devices(),
        "labels": settings_manager.get_device_labels()
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
        "defaultIp": device_manager.get_default_device_ip(),
        "favorites": settings_manager.get_favorite_devices(),
        "disabledDevices": settings_manager.get_disabled_devices(),
        "labels": settings_manager.get_device_labels()
    }

@router.get("/api/devices/default")
async def get_default_device():
    return {"defaultDeviceId": device_manager.get_default_device_ip()}

@router.post("/api/devices/default")
async def set_default_device(req: DefaultDeviceRequest):
    dev_id = req.id or req.ip or ""
    saved = device_manager.set_default_device_ip(dev_id)
    return {"success": True, "defaultDeviceId": saved}

@router.get("/api/devices/favorites")
async def get_favorite_devices():
    return {"favorites": settings_manager.get_favorite_devices()}

@router.post("/api/devices/favorites")
async def set_favorite_devices(req: DeviceFavoritesRequest):
    saved = settings_manager.set_favorite_devices(req.favorites)
    return {"success": True, "favorites": saved}

@router.post("/api/devices/favorite/toggle")
async def toggle_favorite_device(req: DeviceFavoriteToggleRequest):
    target = req.ip or req.id or ""
    if not target:
        return {"success": False, "error": "ip or id is required"}
    is_fav = settings_manager.toggle_favorite_device(target)
    return {
        "success": True,
        "target": target,
        "isFavorite": is_fav,
        "favorites": settings_manager.get_favorite_devices()
    }

@router.get("/api/devices/disabled")
async def get_disabled_devices():
    return {"disabledDevices": settings_manager.get_disabled_devices()}

@router.post("/api/devices/disabled/toggle")
@router.post("/api/devices/toggle-disabled")
async def toggle_disabled_device(req: DeviceDisabledToggleRequest):
    target = req.id or req.ip or ""
    if not target:
        return {"success": False, "error": "id or ip is required"}
    is_dis = settings_manager.toggle_disabled_device(target)
    return {
        "success": True,
        "target": target,
        "disabled": is_dis,
        "disabledDevices": settings_manager.get_disabled_devices()
    }

@router.get("/api/devices/labels")
async def get_device_labels():
    return {"labels": settings_manager.get_device_labels()}

@router.post("/api/devices/label")
async def set_device_label(req: DeviceLabelRequest):
    dev_id = req.deviceId or req.id or req.ip or ""
    alt_id = req.ip if (req.deviceId or req.id) and req.ip != dev_id else (req.id if req.ip and req.id != dev_id else None)
    if not dev_id:
        return JSONResponse(status_code=400, content={"success": False, "error": "deviceId または ip が指定されていません"})

    ok, result_or_err = settings_manager.set_device_label(dev_id, req.label, alt_id=alt_id)
    if not ok:
        return JSONResponse(status_code=400, content={"success": False, "error": result_or_err})

    return {
        "success": True,
        "deviceId": dev_id,
        "label": result_or_err,
        "labels": settings_manager.get_device_labels()
    }

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
    elif dtype in ("client", "pc"):
        # クライアントスピーカー: 個別音量を保存（次回発話時の音量指示に反映）
        success = True
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
