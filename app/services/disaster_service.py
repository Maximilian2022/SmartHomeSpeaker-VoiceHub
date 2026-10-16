import asyncio
import json
from typing import Dict, Any, Optional, Callable
import aiohttp
import httpx
from app.services.settings_service import settings_manager

P2P_QUAKE_WS = "wss://api.p2pquake.net/v2/ws"
JMA_WEATHER_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json" # 東京（設定可能）

class DisasterService:
    def __init__(self):
        self._ws_task: Optional[asyncio.Task] = None
        self._on_alert_callback: Optional[Callable] = None
        self._last_alert_id: str = ""

    def set_alert_callback(self, cb: Callable):
        self._on_alert_callback = cb

    async def start(self):
        if self._ws_task is None or self._ws_task.done():
            self._ws_task = asyncio.create_task(self._run_ws_loop())

    async def _run_ws_loop(self):
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(P2P_QUAKE_WS) as ws:
                        print("[DisasterService] Connected to P2PQuake WebSocket")
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                await self._handle_p2p_message(data)
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except Exception as e:
                print(f"[DisasterService] WebSocket connection error: {e}")
            await asyncio.sleep(10) # 再接続インターバル

    async def _handle_p2p_message(self, data: Dict[str, Any]):
        code = data.get("code")
        # 551: 地震情報, 556: 緊急地震速報
        if code in (551, 556):
            msg_id = data.get("_id") or data.get("id") or str(data.get("time"))
            if msg_id == self._last_alert_id:
                return
            self._last_alert_id = msg_id

            text = ""
            if code == 556:
                text = "緊急地震速報です。強い揺れに警戒してください。"
            elif code == 551:
                earthquake = data.get("earthquake", {})
                hypocenter = earthquake.get("hypocenter", {}).get("name", "各地")
                max_scale = earthquake.get("maxScale", 0)
                scale_str = self._scale_to_text(max_scale)
                if max_scale >= 30: # 震度3以上
                    text = f"地震情報です。{hypocenter}で最大{scale_str}の地震が発生しました。"

            if text and self._on_alert_callback:
                await self._on_alert_callback(text, urgent=True)

    def _scale_to_text(self, scale: int) -> str:
        mapping = {
            10: "震度1", 20: "震度2", 30: "震度3", 40: "震度4",
            45: "震度5弱", 50: "震度5強", 55: "震度6弱", 60: "震度6強", 70: "震度7"
        }
        return mapping.get(scale, f"震度{scale}")

    async def get_today_weather(self, area_code: str = "130000") -> str:
        """気象庁 API から本日の天気を取得"""
        try:
            url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    series = data[0]["timeSeries"][0]["areas"][0]
                    weathers = series.get("weathers", [""])
                    return weathers[0].replace("　", "、")
        except Exception as e:
            print(f"[DisasterService] Weather fetch error: {e}")
        return ""

disaster_service = DisasterService()
