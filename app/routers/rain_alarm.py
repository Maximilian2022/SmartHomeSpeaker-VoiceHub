from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from app.services.rain_alarm_service import rain_alarm_service
from app.services.settings_service import settings_manager

router = APIRouter(prefix="/api/rain-alarm", tags=["RainAlarm"])


class TestAlertRequest(BaseModel):
    alertType: str = Field(default="approaching", description="テスト種別 (approaching, heavy, clearing)")


@router.get("/status")
async def get_rain_alarm_status():
    """雨アラームの現在の設定および監視・降雨状況を取得"""
    return rain_alarm_service.get_status()


@router.post("/check-now")
async def trigger_check_now():
    """雨雲状況の手動即時チェックと判定を実行"""
    res = await rain_alarm_service.check_and_notify()
    return res


@router.post("/test")
async def trigger_test_alert(req: TestAlertRequest):
    """雨アラームのテスト音声を即時発声"""
    res = await rain_alarm_service.test_alert(req.alertType)
    return res


@router.get("/forecast")
async def get_live_forecast(
    lat: float = Query(..., description="緯度"),
    lon: float = Query(..., description="経度")
):
    """指定した緯度経度のリアルタイム降雨予測を取得（WebUI地図プレビュー用）"""
    conf = settings_manager.get().get("rainAlarm", {})
    provider = conf.get("provider", "auto")
    yahoo_app_id = conf.get("yahooAppId", "")

    try:
        curr, timeline, provider_used = await rain_alarm_service.fetch_forecast(
            lat=lat,
            lon=lon,
            provider=provider,
            yahoo_app_id=yahoo_app_id
        )
        return {
            "currentRainfall": curr,
            "timeline": timeline,
            "providerUsed": provider_used
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"降雨予測データの取得に失敗しました: {str(e)}")


@router.get("/radar-time")
async def get_jma_radar_times():
    """気象庁雨雲レーダー（高解像度降水ナウキャスト）の最新時刻一覧を取得（WebUI地図重ね合わせ用）"""
    times = await rain_alarm_service.get_jma_radar_times()
    return {"times": times}


@router.get("/ip-location")
async def get_approx_ip_location():
    """HTTP環境等でGPSが使用できない場合のIPアドレスベースの大まかな位置情報（フォールバック用）"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get("http://ip-api.com/json/?lang=ja")
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success":
                    return {
                        "status": "success",
                        "latitude": data.get("lat", 35.6812),
                        "longitude": data.get("lon", 139.7671),
                        "locationName": f"{data.get('regionName', '')}{data.get('city', '')}"
                    }
    except Exception as e:
        pass
    return {
        "status": "fallback",
        "latitude": 35.6812,
        "longitude": 139.7671,
        "locationName": "東京都千代田区"
    }
