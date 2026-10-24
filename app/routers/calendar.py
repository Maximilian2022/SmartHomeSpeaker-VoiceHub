from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from app.services.calendar_service import calendar_service
from app.core.logger import get_logger

log = get_logger("CalendarRouter")
router = APIRouter()

@router.get("/api/calendar/events")
async def get_events():
    return calendar_service.cached_events

@router.post("/api/calendar/sync")
async def sync_calendar():
    log.info("Manual calendar sync triggered.")
    events = await calendar_service.sync_all()
    return {"success": True, "count": len(events), "events": events}

@router.post("/api/calendar/summary")
async def calendar_daily_summary():
    log.info("Manual calendar daily summary speech triggered.")
    try:
        res = await calendar_service.speak_daily_summary()
        return res
    except Exception as e:
        log.error(f"Calendar daily summary error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to execute daily summary")
