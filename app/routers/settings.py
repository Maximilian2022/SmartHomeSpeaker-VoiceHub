from typing import Dict, Any
from fastapi import APIRouter
from app.services.settings_service import settings_manager
from app.services.speech_service import speech_service

router = APIRouter()

@router.get("/api/settings")
async def get_settings():
    return settings_manager.get()

@router.put("/api/settings")
@router.post("/api/settings")
async def update_settings(payload: Dict[str, Any]):
    return settings_manager.update(payload)

@router.post("/api/settings/sync-test")
async def sync_test():
    # 同期テスト音（「ポン、ピン、パン」）を発声
    return await speech_service.speak(
        text="ポン、ピン、パン。同期テストです。",
        targets="ALL",
        urgent=True
    )
