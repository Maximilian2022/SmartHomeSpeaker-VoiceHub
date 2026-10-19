from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.onvif_service import onvif_service
from app.services.dlna_service import dlna_service
from app.services.settings_service import settings_manager
from app.services.tts_service import tts_service

router = APIRouter()

class ScanRequest(BaseModel):
    timeoutMs: Optional[int] = 3500
    username: Optional[str] = None
    password: Optional[str] = None

class RegisterRequest(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    ip: str
    port: Optional[int] = 8000
    model: Optional[str] = None
    type: Optional[str] = "onvif"
    username: Optional[str] = None
    password: Optional[str] = None
    controlUrl: Optional[str] = None
    renderingControlUrl: Optional[str] = None
    delete: Optional[bool] = False
    enabled: Optional[bool] = True

class TestRequest(BaseModel):
    ip: str
    text: Optional[str] = "こちらはスピーカーのテスト発話です"
    voice: Optional[str] = "ja-JP-NanamiNeural"
    volumeLevel: Optional[float] = 1.0

class DefaultAuthRequest(BaseModel):
    defaultUsername: str = "admin"
    defaultPassword: Optional[str] = ""

@router.get("/api/onvif/scan")
@router.post("/api/onvif/scan")
@router.get("/api/onvif-dlna/scan")
@router.post("/api/onvif-dlna/scan")
@router.get("/api/dlna/scan")
@router.post("/api/dlna/scan")
async def scan_onvif_dlna(req: Optional[ScanRequest] = None):
    timeout_ms = req.timeoutMs if req and req.timeoutMs else 3500
    username = req.username if req and req.username else ""
    password = req.password if req and req.password else ""
    devices = await onvif_service.scan_all_devices(timeout_ms, username, password)
    return {
        "success": True,
        "devices": devices,
        "total": len(devices)
    }

@router.post("/api/dlna/probe")
async def probe_dlna(payload: Dict[str, Any]):
    """指定された IP と ポートの DLNA / UPnP MediaRenderer を直接検証"""
    ip = payload.get("ip", "").strip()
    port = int(payload.get("port", 80))
    if not ip:
        raise HTTPException(status_code=400, detail="IP address is required")
    location = payload.get("location") or f"http://{ip}:{port}/description.xml"
    
    import httpx
    async with httpx.AsyncClient(timeout=4.0) as client:
        info = await dlna_service._fetch_device_info(client, location)
        if not info:
            # 別のよくあるXMLパスも試行
            for fallback in [f"http://{ip}:{port}/rootDesc.xml", f"http://{ip}:{port}/devicedesc.xml", f"http://{ip}:{port}/"]:
                info = await dlna_service._fetch_device_info(client, fallback)
                if info:
                    break
    if not info:
        raise HTTPException(status_code=404, detail="DLNA MediaRenderer が見つかりませんでした (AVTransport未検出)")
    return {"success": True, "device": info}

@router.post("/api/dlna/register")
@router.post("/api/onvif/register")
async def register_device(raw_req: Dict[str, Any]):
    # { device: { ... } } 形式またはフラット形式の両方を吸収
    dev_data = raw_req.get("device", raw_req)
    clean_ip = str(dev_data.get("ip", "")).replace("onvif:", "").replace("dlna:", "")
    dev_id = dev_data.get("id") or raw_req.get("id")
    is_delete = raw_req.get("delete") or dev_data.get("delete", False)

    onvif_conf = settings_manager.get().get("onvif", {})
    reg_list: List[Dict[str, Any]] = list(onvif_conf.get("registeredDevices", []))

    if is_delete:
        reg_list = [d for d in reg_list if d.get("ip") != clean_ip and d.get("id") != dev_id]
    else:
        existing = next((d for d in reg_list if d.get("ip") == clean_ip or (dev_id and d.get("id") == dev_id)), None)
        dtype = dev_data.get("type", "onvif")

        # 既存デバイスの更新時にパスワードやユーザー名が未指定・空文字なら既存の値を引き継ぐ
        username = dev_data.get("username")
        if (username is None or str(username).strip() == "") and existing:
            username = existing.get("username")

        password = dev_data.get("password")
        if (password is None or str(password).strip() == "") and existing:
            password = existing.get("password")

        entry = {
            "id": dev_id or (existing.get("id") if existing else f"{dtype}_{clean_ip.replace('.', '_')}"),
            "name": dev_data.get("name") or (existing.get("name") if existing else f"{dtype.upper()} ({clean_ip})"),
            "ip": clean_ip,
            "port": dev_data.get("port") or (existing.get("port", 8000) if existing else 8000),
            "model": dev_data.get("model") or (existing.get("model") if existing else ("Speaker" if dtype == "onvif" else "DLNA Speaker")),
            "type": dtype,
            "username": username,
            "password": password,
            "controlUrl": dev_data.get("controlUrl") or (existing.get("controlUrl") if existing else None),
            "renderingControlUrl": dev_data.get("renderingControlUrl") or (existing.get("renderingControlUrl") if existing else None),
            "enabled": dev_data.get("enabled", True)
        }
        if existing:
            reg_list = [entry if (d.get("ip") == clean_ip or (dev_id and d.get("id") == dev_id)) else d for d in reg_list]
        else:
            reg_list.append(entry)

    settings_manager.update({"onvif": {**onvif_conf, "registeredDevices": reg_list}})
    return {"success": True, "registeredDevices": reg_list}

@router.post("/api/dlna/test")
@router.post("/api/onvif/test")
async def test_playback(req: TestRequest):
    onvif_conf = settings_manager.get().get("onvif", {})
    reg_list = onvif_conf.get("registeredDevices", [])
    clean_ip = req.ip.replace("onvif:", "").replace("dlna:", "")

    target_dev = next((d for d in reg_list if d.get("ip") == clean_ip or d.get("id") == req.ip), None)
    if not target_dev:
        # スキャン結果から探す
        target_dev = next((d for d in onvif_service.cached_scan_results if d.get("ip") == clean_ip), None)
        if not target_dev:
            target_dev = next((d for d in dlna_service.cached_devices if d.get("ip") == clean_ip), None)

    if not target_dev:
        target_dev = {"ip": clean_ip, "type": "onvif"}

    # 音声合成
    speech = await tts_service.synthesize(text=req.text or "テストです", voice=req.voice or "ja-JP-NanamiNeural")
    dev_type = target_dev.get("type", "onvif")

    if dev_type == "dlna":
        from app.config import settings
        audio_url = f"http://{settings.effective_wireless_ip}:{settings.server_port}/voice/{speech['filename']}"
        success = await dlna_service.play_audio(target_dev, audio_url, req.volumeLevel)
        if not success:
            raise HTTPException(status_code=500, detail="DLNA playback failed")
        return {"success": True, "message": "Playback started"}
    else:
        return await onvif_service.play_audio(target_dev, speech["filepath"], speech["duration"], req.volumeLevel)

@router.post("/api/onvif/default-auth")
async def save_default_auth(req: DefaultAuthRequest):
    onvif_conf = settings_manager.get().get("onvif", {})
    update_data = {
        **onvif_conf,
        "defaultUsername": req.defaultUsername
    }
    if req.defaultPassword is not None:
        update_data["defaultPassword"] = req.defaultPassword

    settings_manager.update({"onvif": update_data})
    return {"success": True}
