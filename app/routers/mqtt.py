from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.mqtt_service import mqtt_service
from app.services.settings_service import settings_manager
from app.core.logger import get_logger

log = get_logger("MqttRouter")
router = APIRouter()

class MqttTestRequest(BaseModel):
    text: str = "こちらはMQTT経由のテスト発話です"
    target: Optional[str] = None
    brokerId: Optional[str] = None

@router.get("/api/mqtt/status")
async def get_mqtt_status():
    """MQTT サービスの接続状況・統計情報を取得"""
    return mqtt_service.get_status()

@router.post("/api/mqtt/restart")
async def restart_mqtt():
    """設定変更に伴う MQTT クライアントの再起動・再接続"""
    await mqtt_service.restart()
    return {"success": True, "status": mqtt_service.get_status()}

@router.post("/api/mqtt/test")
async def test_mqtt(req: MqttTestRequest):
    """MQTT ブローカーを経由したテスト送信・発話検証"""
    try:
        res = await mqtt_service.test_publish(req.text, req.target, broker_id=req.brokerId)
        return res
    except Exception as e:
        log.error(f"Failed to test MQTT: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to publish MQTT test message")

class HaDiscoveryRequest(BaseModel):
    clear: bool = False
    brokerId: Optional[str] = None

@router.post("/api/mqtt/ha-discovery")
async def trigger_ha_discovery(req: HaDiscoveryRequest = HaDiscoveryRequest()):
    """Home Assistant MQTT Auto-Discovery トピックの強制パブリッシュ / 削除"""
    try:
        res = await mqtt_service.publish_ha_discovery(clear=req.clear, broker_id=req.brokerId)
        return res
    except Exception as e:
        log.error(f"Failed to publish HA discovery: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to configure Home Assistant discovery")

