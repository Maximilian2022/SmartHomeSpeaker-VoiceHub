from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services.disaster_service import disaster_service
from app.services.settings_service import settings_manager
from app.core.logger import get_logger

log = get_logger("DisasterRouter")
router = APIRouter()

class TestDisasterRequest(BaseModel):
    type: Optional[str] = "eew"

@router.get("/api/disaster/areas")
async def get_disaster_areas(prefCode: Optional[str] = Query(None)):
    prefectures = disaster_service.get_prefectures()
    cities = []
    if prefCode:
        cities = disaster_service.get_cities_for_prefecture(prefCode)
    return {
        "prefectures": prefectures,
        "cities": cities
    }

@router.get("/api/disaster/settings")
async def get_disaster_settings():
    return settings_manager.get().get("disaster", {})

@router.put("/api/disaster/settings")
async def update_disaster_settings(data: Dict[str, Any]):
    log.info(f"Updating disaster settings: {data}")
    updated = settings_manager.update({"disaster": data})
    return updated.get("disaster", {})

@router.get("/api/disaster/status")
async def get_disaster_status():
    is_ws_active = disaster_service.is_ws_connected
    return {
        "connected": is_ws_active,
        "isWsConnected": is_ws_active,
        "p2pQuake": {
            "connected": is_ws_active,
            "lastEvent": None
        }
    }

@router.get("/api/disaster/weather")
async def get_weather():
    log.info("Fetching today's weather forecast...")
    weather = await disaster_service.get_today_weather()
    if not weather:
        log.warning("Failed to fetch weather forecast from JMA")
        return {"error": "天気予報の取得に失敗しました"}
    return weather

@router.post("/api/disaster/test")
async def test_disaster(req: Optional[TestDisasterRequest] = None):
    test_type = req.type if req else "eew"
    log.info(f"Triggering disaster test for type: {test_type}")
    try:
        res = await disaster_service.trigger_test(test_type)
        return res
    except Exception as e:
        log.error(f"Disaster test error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
