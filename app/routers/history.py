from fastapi import APIRouter
from app.services.speech_service import speech_service, HISTORY_LOG

router = APIRouter()

@router.get("/api/history")
async def get_history():
    return speech_service.get_history()

@router.delete("/api/history")
async def clear_history():
    global HISTORY_LOG
    HISTORY_LOG.clear()
    return {"success": True, "message": "History cleared"}
