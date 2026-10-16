from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.disaster_service import disaster_service
from app.services.settings_service import settings_manager
from app.services.speech_service import speech_service

router = APIRouter()

PREFECTURE_MASTER = [
    {"code": "016000", "name": "北海道 (石狩・空知・後志)", "prefix": "01"},
    {"code": "020000", "name": "青森県", "prefix": "02"},
    {"code": "030000", "name": "岩手県", "prefix": "03"},
    {"code": "040000", "name": "宮城県", "prefix": "04"},
    {"code": "050000", "name": "秋田県", "prefix": "05"},
    {"code": "060000", "name": "山形県", "prefix": "06"},
    {"code": "070000", "name": "福島県", "prefix": "07"},
    {"code": "080000", "name": "茨城県", "prefix": "08"},
    {"code": "090000", "name": "栃木県", "prefix": "09"},
    {"code": "100000", "name": "群馬県", "prefix": "10"},
    {"code": "110000", "name": "埼玉県", "prefix": "11"},
    {"code": "120000", "name": "千葉県", "prefix": "12"},
    {"code": "130000", "name": "東京都", "prefix": "13"},
    {"code": "140000", "name": "神奈川県", "prefix": "14"},
    {"code": "150000", "name": "新潟県", "prefix": "15"},
    {"code": "160000", "name": "富山県", "prefix": "16"},
    {"code": "170000", "name": "石川県", "prefix": "17"},
    {"code": "180000", "name": "福井県", "prefix": "18"},
    {"code": "190000", "name": "山梨県", "prefix": "19"},
    {"code": "200000", "name": "長野県", "prefix": "20"},
    {"code": "210000", "name": "岐阜県", "prefix": "21"},
    {"code": "220000", "name": "静岡県", "prefix": "22"},
    {"code": "230000", "name": "愛知県", "prefix": "23"},
    {"code": "240000", "name": "三重県", "prefix": "24"},
    {"code": "250000", "name": "滋賀県", "prefix": "25"},
    {"code": "260000", "name": "京都府", "prefix": "26"},
    {"code": "270000", "name": "大阪府", "prefix": "27"},
    {"code": "280000", "name": "兵庫県", "prefix": "28"},
    {"code": "290000", "name": "奈良県", "prefix": "29"},
    {"code": "300000", "name": "和歌山県", "prefix": "30"},
    {"code": "310000", "name": "鳥取県", "prefix": "31"},
    {"code": "320000", "name": "島根県", "prefix": "32"},
    {"code": "330000", "name": "岡山県", "prefix": "33"},
    {"code": "340000", "name": "広島県", "prefix": "34"},
    {"code": "350000", "name": "山口県", "prefix": "35"},
    {"code": "360000", "name": "徳島県", "prefix": "36"},
    {"code": "370000", "name": "香川県", "prefix": "37"},
    {"code": "380000", "name": "愛媛県", "prefix": "38"},
    {"code": "390000", "name": "高知県", "prefix": "39"},
    {"code": "400000", "name": "福岡県", "prefix": "40"},
    {"code": "410000", "name": "佐賀県", "prefix": "41"},
    {"code": "420000", "name": "長崎県", "prefix": "42"},
    {"code": "430000", "name": "熊本県", "prefix": "43"},
    {"code": "440000", "name": "大分県", "prefix": "44"},
    {"code": "450000", "name": "宮崎県", "prefix": "45"},
    {"code": "460100", "name": "鹿児島県", "prefix": "46"},
    {"code": "471000", "name": "沖縄県 (本島)", "prefix": "47"}
]

@router.get("/api/disaster/areas")
async def get_disaster_areas(prefCode: Optional[str] = None):
    cities = []
    return {"prefectures": PREFECTURE_MASTER, "cities": cities}

@router.get("/api/disaster/settings")
async def get_disaster_settings():
    return settings_manager.get().get("disaster", {})

@router.put("/api/disaster/settings")
async def update_disaster_settings(data: Dict[str, Any]):
    updated = settings_manager.update({"disaster": data})
    return updated.get("disaster", {})

@router.get("/api/disaster/status")
async def get_disaster_status():
    is_ws_active = disaster_service._ws_task is not None and not disaster_service._ws_task.done()
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
    weather = await disaster_service.get_today_weather()
    return weather or {"error": "天気予報の取得に失敗しました"}

@router.post("/api/disaster/test")
async def test_disaster(req: Optional[Dict[str, Any]] = None):
    # 防災テスト警報
    return await speech_service.speak(
        text="これは防災緊急速報のテスト通知です。訓練です。",
        targets="ALL",
        urgent=True
    )
