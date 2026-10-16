from fastapi import APIRouter
from app.services.calendar_service import calendar_service

router = APIRouter()

@router.get("/api/calendar/events")
async def get_events():
    return calendar_service.cached_events

@router.post("/api/calendar/sync")
async def sync_calendar():
    events = await calendar_service.sync_all()
    return {"success": True, "count": len(events), "events": events}
