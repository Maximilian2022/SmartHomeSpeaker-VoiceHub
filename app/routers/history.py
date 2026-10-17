from typing import Optional
from fastapi import APIRouter, Query
from app.services.history_service import history_manager

router = APIRouter()

@router.get("/api/history")
async def get_history(limit: int = Query(default=100, ge=1, le=500)):
    items = history_manager.get_history(limit=limit)
    return {
        "history": items,
        "total": len(items)
    }

@router.delete("/api/history")
async def clear_history():
    history_manager.clear()
    return {"success": True, "message": "History cleared"}
