import asyncio
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.dnd_service import dnd_service
from app.services.calendar_service import calendar_service
from app.services.settings_service import settings_manager
from app.services.speech_service import speech_service
from app.services.ai_service import ai_service
from app.services.mqtt_service import mqtt_service
from app.core.logger import get_logger

log = get_logger("DndRouter")
router = APIRouter()

class MuteRequest(BaseModel):
    durationMinutes: Optional[int] = None
    until: Optional[float] = None
    reason: Optional[str] = "手動ミュート"

@router.get("/api/dnd/status")
async def get_dnd_status():
    status = dnd_service.get_global_status()
    return status

@router.post("/api/dnd/mute")
async def mute_dnd(req: MuteRequest = MuteRequest()):
    now_ts = time.time()
    if req.until:
        until_ts = req.until
    elif req.durationMinutes:
        until_ts = now_ts + (req.durationMinutes * 60)
    else:
        until_ts = now_ts + (365 * 24 * 3600)  # 時間省略時は無期限手動ミュート

    dnd_conf = settings_manager.get().get("dnd", {})
    settings_manager.update({
        "dnd": {
            **dnd_conf,
            "manualUntil": until_ts,
            "manualReason": req.reason or "手動ミュート"
        }
    })
    log.info(f"DND muted until {until_ts} (reason: {req.reason})")
    asyncio.create_task(mqtt_service.publish_dnd_state())
    return {"success": True, "manualUntil": until_ts}

@router.post("/api/dnd/unmute")
async def unmute_dnd():
    dnd_conf = settings_manager.get().get("dnd", {})
    settings_manager.update({
        "dnd": {
            **dnd_conf,
            "manualUntil": None,
            "manualReason": ""
        }
    })
    log.info("DND unmuted.")
    # キューがあれば消化
    asyncio.create_task(dnd_service.check_and_flush_queue())
    asyncio.create_task(mqtt_service.publish_dnd_state())
    return {"success": True}

@router.post("/api/dnd/toggle")
async def toggle_dnd():
    status = dnd_service.get_global_status()
    if status.get("isActive", False):
        return await unmute_dnd()
    else:
        return await mute_dnd()


@router.post("/api/dnd/quick")
async def quick_dnd(req: Dict[str, Any]):
    raw_minutes = req.get("minutes", 60)
    reason = req.get("reason", "手動サイレント (即時)")
    now_ts = time.time()

    if raw_minutes in ("indefinite", -1, "-1"):
        until_ts = now_ts + (365 * 24 * 3600) # 実質無期限
    else:
        try:
            m = int(raw_minutes)
        except (ValueError, TypeError):
            m = 60
        if m == 0:
            # 0分指定は解除
            return await unmute_dnd()
        until_ts = now_ts + (m * 60)

    dnd_conf = settings_manager.get().get("dnd", {})
    settings_manager.update({
        "dnd": {
            **dnd_conf,
            "manualUntil": until_ts,
            "manualReason": reason
        }
    })
    log.info(f"Quick DND enabled: minutes={raw_minutes}, until={until_ts}, reason={reason}")
    asyncio.create_task(mqtt_service.publish_dnd_state())
    return {"success": True, "manualUntil": until_ts, "reason": reason}

@router.get("/api/dnd/history")
async def get_dnd_history():
    return dnd_service.get_history()

@router.delete("/api/dnd/history")
async def clear_dnd_history():
    dnd_service.clear_history()
    log.info("DND history cleared.")
    return {"success": True}

@router.get("/api/dnd/queue")
async def get_dnd_queue():
    return dnd_service.get_queue()

@router.get("/api/queue")
async def get_general_queue():
    """旧Node版互換: 永続化キュー状態確認 API"""
    q = dnd_service.get_queue()
    return {
        "dndQueue": q,
        "webhookQueue": []
    }

@router.post("/api/dnd/queue/release")
async def release_dnd_queue():
    released = await dnd_service.check_and_flush_queue()
    return {"success": True, "released": released or 0}

