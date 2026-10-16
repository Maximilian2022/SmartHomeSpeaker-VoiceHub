import time
from typing import Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.dnd_service import dnd_service
from app.services.calendar_service import calendar_service
from app.services.settings_service import settings_manager
from app.services.speech_service import speech_service
from app.services.ai_service import ai_service

router = APIRouter()

class MuteRequest(BaseModel):
    durationMinutes: Optional[int] = None
    until: Optional[float] = None
    reason: Optional[str] = "手動ミュート"

@router.get("/api/dnd/status")
async def get_dnd_status():
    meeting = calendar_service.get_current_meeting_title()
    status = dnd_service.evaluate(active_event_title=meeting)
    status["queueCount"] = len(dnd_service.get_queue())
    return status

@router.post("/api/dnd/mute")
async def mute_dnd(req: MuteRequest):
    now_ts = time.time()
    until_ts = req.until
    if req.durationMinutes:
        until_ts = now_ts + (req.durationMinutes * 60)

    dnd_conf = settings_manager.get().get("dnd", {})
    settings_manager.update({
        "dnd": {
            **dnd_conf,
            "manualUntil": until_ts,
            "manualReason": req.reason or "手動ミュート"
        }
    })
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
    return {"success": True}

@router.post("/api/dnd/quick")
async def quick_dnd(req: Dict[str, Any]):
    minutes = int(req.get("minutes", 60))
    reason = req.get("reason", "手動サイレント (即時)")
    now_ts = time.time()
    until_ts = now_ts + (minutes * 60)
    dnd_conf = settings_manager.get().get("dnd", {})
    settings_manager.update({
        "dnd": {
            **dnd_conf,
            "manualUntil": until_ts,
            "manualReason": reason
        }
    })
    return {"success": True, "manualUntil": until_ts, "reason": reason}

@router.get("/api/dnd/history")
async def get_dnd_history():
    return dnd_service.get_history()

@router.delete("/api/dnd/history")
async def clear_dnd_history():
    dnd_service.clear_history()
    return {"success": True}

@router.get("/api/dnd/queue")
async def get_dnd_queue():
    return dnd_service.get_queue()

@router.post("/api/dnd/queue/release")
async def release_dnd_queue():
    items = dnd_service.clear_queue()
    if not items:
        return {"success": True, "released": 0}

    messages = [item.get("text", "") for item in items if item.get("text")]
    dnd_conf = settings_manager.get().get("dnd", {})
    use_ai = dnd_conf.get("aiSummaryEnabled", True) and len(messages) >= dnd_conf.get("aiSummaryThreshold", 2)

    if use_ai:
        summary_text = await ai_service.summarize_dnd_messages(messages)
        await speech_service.speak(text=summary_text, targets="ALL", urgent=True)
    else:
        for m in messages:
            await speech_service.speak(text=m, targets="ALL", urgent=True)
            await asyncio.sleep(0.5)

    return {"success": True, "released": len(items)}
