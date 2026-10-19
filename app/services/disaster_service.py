import asyncio
import json
import time
from typing import Dict, Any, Optional, Callable, List
import aiohttp
import httpx
from app.services.settings_service import settings_manager
from app.core.logger import get_logger

log = get_logger("Disaster")

P2P_QUAKE_WS = "wss://api.p2pquake.net/v2/ws"
AREA_JSON_URL = "https://www.jma.go.jp/bosai/common/const/area.json"

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

SCALE_MAP = {
    10: "震度1", 20: "震度2", 30: "震度3", 40: "震度4",
    45: "震度5弱", 50: "震度5強", 55: "震度6弱", 60: "震度6強", 70: "震度7"
}

JMA_WARNING_CODES: Dict[str, Dict[str, str]] = {
    # 特別警報 (special)
    "32": {"name": "暴風雪特別警報", "level": "special"},
    "33": {"name": "大雨特別警報", "level": "special"},
    "35": {"name": "暴風特別警報", "level": "special"},
    "36": {"name": "大雪特別警報", "level": "special"},
    "37": {"name": "波浪特別警報", "level": "special"},
    "38": {"name": "高潮特別警報", "level": "special"},
    # 警報 (warning)
    "02": {"name": "暴風雪警報", "level": "warning"},
    "03": {"name": "大雨警報", "level": "warning"},
    "04": {"name": "洪水警報", "level": "warning"},
    "05": {"name": "暴風警報", "level": "warning"},
    "06": {"name": "大雪警報", "level": "warning"},
    "07": {"name": "波浪警報", "level": "warning"},
    "08": {"name": "高潮警報", "level": "warning"},
    # 注意報 (advisory)
    "10": {"name": "大雨注意報", "level": "advisory"},
    "12": {"name": "大雪注意報", "level": "advisory"},
    "13": {"name": "風雪注意報", "level": "advisory"},
    "14": {"name": "雷注意報", "level": "advisory"},
    "15": {"name": "強風注意報", "level": "advisory"},
    "16": {"name": "波浪注意報", "level": "advisory"},
    "17": {"name": "融雪注意報", "level": "advisory"},
    "18": {"name": "洪水注意報", "level": "advisory"},
    "19": {"name": "高潮注意報", "level": "advisory"},
    "20": {"name": "濃霧注意報", "level": "advisory"},
    "21": {"name": "乾燥注意報", "level": "advisory"},
    "22": {"name": "なだれ注意報", "level": "advisory"},
    "23": {"name": "低温注意報", "level": "advisory"},
    "24": {"name": "霜注意報", "level": "advisory"},
    "25": {"name": "着氷注意報", "level": "advisory"},
    "26": {"name": "着雪注意報", "level": "advisory"}
}

class DisasterService:
    def __init__(self):
        self._ws_task: Optional[asyncio.Task] = None
        self._poll_task: Optional[asyncio.Task] = None
        self._speech_executor: Optional[Callable] = None
        self._last_alert_id: str = ""
        self._last_processed_earthquake_id: Optional[str] = None
        self._active_eew_events: Dict[str, Dict[str, Any]] = {}
        self._last_known_warnings: set = set()
        self._is_first_warning_check: bool = True
        self.area_data_cache: Optional[Dict[str, Any]] = None
        self.is_ws_connected: bool = False

    def set_speech_executor(self, cb: Callable):
        self._speech_executor = cb

    async def speak(self, text: str, urgent: bool = False, volume: Optional[int] = None):
        if not self._speech_executor:
            log.warning(f"Speech executor not registered. Text: {text}")
            return
        try:
            settings = settings_manager.get().get("disaster", {})
            target_scope = settings.get("targetScope", "all")
            if target_scope == "default":
                targets = ["default"]
            elif target_scope == "specific":
                targets = settings.get("targetDevices", []) or ["ALL"]
            else:
                targets = ["ALL"]

            await self._speech_executor(
                text=text,
                targets=targets,
                urgent=urgent,
                volume_level=volume
            )
        except Exception as e:
            log.error(f"Speech dispatch error in disaster: {e}", exc_info=True)

    async def start(self):
        log.info("Starting DisasterService background workers...")
        await self.load_area_master()
        if self._ws_task is None or self._ws_task.done():
            self._ws_task = asyncio.create_task(self._run_ws_loop())
        if self._poll_task is None or self._poll_task.done():
            self._poll_task = asyncio.create_task(self._run_warning_poll_loop())

    async def load_area_master(self):
        """気象庁エリアマスター (area.json) の取得・キャッシュ"""
        try:
            async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": "SmartHomeSpeaker-VoiceHub/2.0"}) as client:
                resp = await client.get(AREA_JSON_URL)
                if resp.status_code == 200:
                    self.area_data_cache = resp.json()
                    log.info("JMA area master data loaded successfully.")
                else:
                    log.warning(f"Failed to fetch area.json: HTTP {resp.status_code}")
        except Exception as e:
            log.warning(f"Area master fetch error (continuing with offline fallback): {e}")

    def get_prefectures(self) -> List[Dict[str, str]]:
        return PREFECTURE_MASTER

    def get_cities_for_prefecture(self, pref_code: str) -> List[Dict[str, str]]:
        if not self.area_data_cache or "class20s" not in self.area_data_cache:
            return []
        pref = next((p for p in PREFECTURE_MASTER if p["code"] == pref_code), None)
        prefix = pref["prefix"] if pref else pref_code[:2]

        cities = []
        for code, info in self.area_data_cache["class20s"].items():
            if code.startswith(prefix):
                cities.append({
                    "code": code,
                    "name": info.get("name", ""),
                    "kana": info.get("kana", "")
                })
        cities.sort(key=lambda c: c["code"])
        return cities

    async def get_today_weather(self, area_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """気象庁 API から本日の詳細天気予報を取得して構造化オブジェクトを返す"""
        settings = settings_manager.get().get("disaster", {})
        area_conf = settings.get("area", {})
        pref_code = area_code or area_conf.get("prefCode") or "130000"
        city_name = area_conf.get("cityName") or area_conf.get("prefName") or "東京地方"

        try:
            url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{pref_code}.json"
            async with httpx.AsyncClient(timeout=6.0, headers={"User-Agent": "SmartHomeSpeaker-VoiceHub/2.0"}) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    log.warning(f"Weather API HTTP error: {resp.status_code} for {url}")
                    return None
                data = resp.json()
                if not isinstance(data, list) or len(data) == 0:
                    log.warning("Weather API returned empty or invalid JSON array")
                    return None

                time_series = data[0].get("timeSeries", [])
                weather_area = time_series[0].get("areas", [{}])[0] if len(time_series) > 0 else {}
                pop_area = time_series[1].get("areas", [{}])[0] if len(time_series) > 1 else {}

                # 1. 天気
                weathers = weather_area.get("weathers", [])
                today_weather = weathers[0].replace("\u3000", "、").replace("  ", " ").strip() if weathers else "晴れ"

                # 2. 降水確率 (当日の最大確率)
                pops = pop_area.get("pops", [])
                max_pop = 0
                if pops:
                    valid_pops = []
                    for p in pops:
                        try:
                            valid_pops.append(int(p))
                        except ValueError:
                            pass
                    if valid_pops:
                        max_pop = max(valid_pops)

                # 3. 気温 (最高・最低気温)
                temp_max = None
                temp_min = None
                temp_area = None
                if len(time_series) > 2 and "areas" in time_series[2]:
                    temp_area = time_series[2]["areas"][0]
                elif len(data) > 1 and "timeSeries" in data[1]:
                    ts1 = data[1].get("timeSeries", [])
                    if len(ts1) > 1 and "areas" in ts1[1]:
                        temp_area = ts1[1]["areas"][0]

                if temp_area and "temps" in temp_area:
                    temps = []
                    for t in temp_area["temps"]:
                        try:
                            temps.append(int(t))
                        except ValueError:
                            pass
                    if len(temps) >= 2:
                        temp_min = min(temps)
                        temp_max = max(temps)
                    elif len(temps) == 1:
                        temp_max = temps[0]

                # 4. アドバイス生成
                daily_conf = settings.get("dailyWeather", {})
                include_advice = daily_conf.get("includeAdvice", True)
                advice = ""
                if include_advice:
                    if max_pop >= 50:
                        advice = "傘を必ずお持ちください。"
                    elif max_pop >= 30:
                        advice = "折りたたみ傘があると安心です。"
                    elif temp_max is not None and temp_max >= 30:
                        advice = "熱中症対策を万全にしてください。"
                    elif temp_min is not None and temp_min <= 5:
                        advice = "防寒対策をしっかりしてお出かけください。"

                temp_str = f"、最高気温は{temp_max}度" if temp_max is not None else ""
                advice_str = f" {advice}" if advice else ""
                summary_text = f"今日の{city_name}の天気は{today_weather}{temp_str}、降水確率は{max_pop}%です。{advice_str}".strip()

                return {
                    "areaName": city_name,
                    "weather": today_weather,
                    "pop": f"{max_pop}%",
                    "maxPopValue": max_pop,
                    "tempMax": f"{temp_max}度" if temp_max is not None else None,
                    "tempMin": f"{temp_min}度" if temp_min is not None else None,
                    "advice": advice,
                    "summaryText": summary_text
                }
        except Exception as e:
            log.error(f"Weather fetch error: {e}", exc_info=True)
            return None

    # ================= P2P 地震情報 WebSocket =================
    async def _run_ws_loop(self):
        while True:
            try:
                log.info(f"Connecting to P2PQuake WebSocket ({P2P_QUAKE_WS})...")
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(P2P_QUAKE_WS, heartbeat=20.0) as ws:
                        self.is_ws_connected = True
                        log.info("P2PQuake WebSocket connected.")
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    data = json.loads(msg.data)
                                    await self._handle_p2p_message(data)
                                except Exception as err:
                                    log.error(f"P2PQuake msg parse error: {err}")
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                log.warning(f"P2PQuake WebSocket closed: {msg.type}")
                                break
            except Exception as e:
                log.warning(f"P2PQuake WebSocket connection error: {e}")
            finally:
                self.is_ws_connected = False
            await asyncio.sleep(15)

    async def _handle_p2p_message(self, data: Dict[str, Any]):
        code = data.get("code")
        settings = settings_manager.get().get("disaster", {})
        if not settings.get("enabled", True) or not settings.get("earthquake", {}).get("enabled", True):
            return

        # 556: 緊急地震速報 (EEW)
        if code == 556 and settings.get("earthquake", {}).get("eewEnabled", True):
            await self._handle_eew(data, settings)
        # 551: 地震情報 (震度速報)
        elif code == 551 and settings.get("earthquake", {}).get("reportEnabled", True):
            await self._handle_quake_report(data, settings)

    async def _handle_eew(self, data: Dict[str, Any], settings: Dict[str, Any]):
        eq_config = settings.get("earthquake", {})
        user_area = settings.get("area", {})
        event_id = data.get("issue", {}).get("eventId") or data.get("id") or str(time.time())
        is_cancelled = bool(data.get("cancelled") or data.get("earthquake", {}).get("cancelled"))

        now_ms = time.time() * 1000
        existing = self._active_eew_events.get(event_id)

        if is_cancelled:
            if existing and existing.get("status") == "notified":
                log.info(f"Issuing EEW cancellation: {event_id}")
                self._active_eew_events[event_id] = {"notifiedAt": now_ms, "status": "cancelled"}
                cancel_text = "先ほどの緊急地震速報は取り消されました。誤報、または観測値の修正によるものです。"
                await self.speak(
                    text=cancel_text,
                    urgent=eq_config.get("eewUrgent", True),
                    volume=eq_config.get("eewVolume", 80)
                )
            return

        if existing and existing.get("status") == "notified":
            return # 重複発報防止

        # 地域マッチング
        target_pref = user_area.get("prefName", "")
        eew_areas = data.get("areas", [])
        should_notify = (eq_config.get("targetScope") == "all" or len(eew_areas) == 0)

        if not should_notify and target_pref:
            for a in eew_areas:
                aname = a.get("name") or a.get("pref") or ""
                if target_pref in aname or aname in target_pref:
                    should_notify = True
                    break

        if should_notify:
            self._active_eew_events[event_id] = {"notifiedAt": now_ms, "status": "notified"}
            text = "緊急地震速報です。強い揺れに警戒してください。身を守る行動を取ってください。"
            log.warning(f"EEW Alert triggered! eventId={event_id}")
            await self.speak(
                text=text,
                urgent=eq_config.get("eewUrgent", True),
                volume=eq_config.get("eewVolume", 80)
            )

    async def _handle_quake_report(self, data: Dict[str, Any], settings: Dict[str, Any]):
        eq = data.get("earthquake")
        if not eq:
            return
        event_key = f"{eq.get('time')}_{eq.get('hypocenter', {}).get('name')}_{eq.get('maxScale')}"
        if self._last_processed_earthquake_id == event_key:
            return
        self._last_processed_earthquake_id = event_key

        eq_config = settings.get("earthquake", {})
        min_scale = int(eq_config.get("minScale", 30))
        max_scale = int(eq.get("maxScale", 0))

        if max_scale < min_scale:
            return

        hypocenter = eq.get("hypocenter", {}).get("name", "各地")
        user_area = settings.get("area", {})
        target_scope = eq_config.get("targetScope", "all")
        target_pref = user_area.get("prefName", "")

        display_scale = max_scale
        if target_scope == "local" and target_pref:
            points = data.get("points", [])
            matched_point = False
            local_max = 0
            if points:
                for p in points:
                    p_pref = p.get("pref", "")
                    p_addr = p.get("addr", "")
                    if target_pref in p_pref or p_pref in target_pref or target_pref in p_addr:
                        p_scale = int(p.get("scale", 0))
                        if p_scale > local_max:
                            local_max = p_scale
                if local_max >= min_scale:
                    matched_point = True
                    display_scale = local_max

            if not matched_point:
                if (target_pref in hypocenter or hypocenter in target_pref) and max_scale >= min_scale:
                    matched_point = True
                    display_scale = max_scale

            if not matched_point:
                log.info(f"Quake report ignored: targetScope=local ({target_pref}) did not match points or hypocenter ({hypocenter}).")
                return

        scale_text = SCALE_MAP.get(display_scale, f"震度{display_scale // 10}")
        text = f"地震情報です。{hypocenter}で最大{scale_text}の地震が発生しました。"
        log.warning(f"Quake report alert: {text}")
        await self.speak(text=text, urgent=bool(eq_config.get("reportUrgent", False)))

    # ================= 気象警報ポーリング =================
    async def _run_warning_poll_loop(self):
        await asyncio.sleep(10)
        while True:
            try:
                await self.check_weather_warnings()
            except Exception as e:
                log.warning(f"Weather warning poll error: {e}")
            settings = settings_manager.get().get("disaster", {})
            interval_m = int(settings.get("weatherWarning", {}).get("checkIntervalMinutes", 5))
            await asyncio.sleep(max(1, interval_m) * 60)

    async def check_weather_warnings(self):
        settings = settings_manager.get().get("disaster", {})
        if not settings.get("enabled", True) or not settings.get("weatherWarning", {}).get("enabled", True):
            return

        area = settings.get("area", {})
        pref_code = area.get("prefCode", "130000")
        city_code = area.get("cityCode", "")
        city_name = area.get("cityName") or area.get("prefName") or "地域"

        url = f"https://www.jma.go.jp/bosai/warning/data/warning/{pref_code}.json"
        async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": "SmartHomeSpeaker-VoiceHub/2.0"}) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return
            data = resp.json()
            area_types = data.get("areaTypes", [])
            areas = area_types[1].get("areas", []) if len(area_types) > 1 else (area_types[0].get("areas", []) if area_types else [])

            target_area = None
            if city_code:
                target_area = next((a for a in areas if a.get("code") == city_code), None)
            if not target_area and areas:
                target_area = areas[0]

            if not target_area or "warnings" not in target_area:
                return

            # 設定レベルに応じたフィルタリング
            configured_level = settings.get("weatherWarning", {}).get("level", "warning")
            if configured_level == "special":
                allowed_levels = {"special"}
            elif configured_level == "advisory":
                allowed_levels = {"special", "warning", "advisory"}
            else: # デフォルト: "warning" (警報以上)
                allowed_levels = {"special", "warning"}

            current_warnings = set()
            for w in target_area["warnings"]:
                st = w.get("status", "")
                if st in ("発表", "継続"):
                    code = str(w.get("code", "")).zfill(2)
                    warn_info = JMA_WARNING_CODES.get(code)
                    if warn_info and warn_info.get("level") in allowed_levels:
                        current_warnings.add(warn_info["name"])

            # 初回ポーリング時は既存警報の音声通知を抑制し、ベースラインとして記録するのみ
            if self._is_first_warning_check:
                self._last_known_warnings = current_warnings
                self._is_first_warning_check = False
                log.info(f"Initial weather warnings baseline recorded: {current_warnings}")
                return

            # 差分判定
            new_warnings = current_warnings - self._last_known_warnings
            cleared_warnings = self._last_known_warnings - current_warnings
            self._last_known_warnings = current_warnings

            if new_warnings:
                names_str = "、".join(sorted(new_warnings))
                text = f"気象警報です。{city_name}に{names_str}が発表されました。"
                log.warning(f"New weather warning announced: {text}")
                await self.speak(text=text, urgent=bool(settings.get("weatherWarning", {}).get("urgent", False)))
            elif cleared_warnings and settings.get("weatherWarning", {}).get("notifyClear", True):
                names_str = "、".join(sorted(cleared_warnings))
                text = f"気象警報の解除です。{city_name}の{names_str}は解除されました。"
                log.info(f"Weather warning cleared: {text}")
                await self.speak(text=text, urgent=False)

    # ================= テスト発話機能 =================
    async def trigger_test(self, test_type: str) -> Dict[str, Any]:
        settings = settings_manager.get().get("disaster", {})
        city_name = settings.get("area", {}).get("cityName") or settings.get("area", {}).get("prefName") or "各地"

        if test_type == "eew":
            text = "緊急地震速報のテストです。強い揺れに警戒してください。これは訓練放送です。"
            await self.speak(text, urgent=True, volume=settings.get("earthquake", {}).get("eewVolume", 80))
            return {"success": True, "text": text}
        elif test_type == "eew_cancel":
            text = "緊急地震速報の取消テストです。先ほどの緊急地震速報は取り消されました。誤報、または観測値の修正によるものです。これは訓練放送です。"
            await self.speak(text, urgent=True, volume=settings.get("earthquake", {}).get("eewVolume", 80))
            return {"success": True, "text": text}
        elif test_type == "quake":
            min_scale = settings.get("earthquake", {}).get("minScale", 30)
            scale_text = SCALE_MAP.get(int(min_scale), "震度3")
            text = f"地震情報のテストです。{city_name}で{scale_text}の揺れを観測しました。震源地はテスト湾、マグニチュードは5.0です。この地震による津波の心配はありません。"
            await self.speak(text, urgent=bool(settings.get("earthquake", {}).get("reportUrgent", False)))
            return {"success": True, "text": text}
        elif test_type == "warning":
            text = f"気象警報のテストです。{city_name}に大雨警報、および洪水警報が発表されました。これはテスト放送です。"
            await self.speak(text, urgent=bool(settings.get("weatherWarning", {}).get("urgent", False)))
            return {"success": True, "text": text}
        elif test_type == "weather":
            weather = await self.get_today_weather()
            summary_text = weather.get("summaryText") if weather else "本日の天気予報の取得に失敗しました。"
            await self.speak(summary_text, urgent=False)
            return {"success": True, "text": summary_text}
        else:
            text = "これは防災緊急速報のテスト通知です。訓練です。"
            await self.speak(text, urgent=True)
            return {"success": True, "text": text}

disaster_service = DisasterService()
