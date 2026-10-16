from fastapi import APIRouter
from app.services.disaster_service import disaster_service
from app.services.speech_service import speech_service

router = APIRouter()

@router.get("/api/disaster/status")
async def get_disaster_status():
    return {"connected": disaster_service._ws_task is not None and not disaster_service._ws_task.done()}

@router.get("/api/disaster/weather")
async def get_weather():
    weather = await disaster_service.get_today_weather()
    return {"weather": weather}

@router.post("/api/disaster/test")
async def test_disaster():
    # 防災テスト警報
    return await speech_service.speak(
        text="これは防災緊急速報のテスト通知です。訓練です。",
        targets="ALL",
        urgent=True
    )
