import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import httpx
from app.services.settings_service import settings_manager
from app.services.speech_service import speech_service
from app.services.dnd_service import dnd_service
from app.core.logger import get_logger

log = get_logger("RainAlarm")

YAHOO_WEATHER_API_URL = "https://map.yahooapis.jp/weather/V1/place"
OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"
JMA_TARGET_TIMES_URL = "https://www.jma.go.jp/bosai/jmatile/data/nowc/targetTimes_N1.json"


class RainAlarmService:
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_check_time: float = 0
        self._last_approaching_notify_time: float = 0
        self._last_heavy_notify_time: float = 0
        self._last_clearing_notify_time: float = 0
        self._is_raining_state: bool = False
        self._last_status: Dict[str, Any] = {
            "status": "idle",
            "lastChecked": None,
            "providerUsed": None,
            "currentRainfall": 0.0,
            "timeline": [],
            "lastAlert": None
        }
        self._jma_cache: Dict[str, Any] = {"times": [], "fetched_at": 0}
        self._forecast_cache: Dict[str, Dict[str, Any]] = {}
        self._rain_active: bool = False
        self._rain_expires_at: float = 0.0
        self._rain_alert_info: Optional[Dict[str, Any]] = None
        self._rain_auto_off_task: Optional[asyncio.Task] = None

    def get_trigger_status(self) -> Dict[str, Any]:
        """スマートホーム連携用トリガー状態（雨雲接近/降雨中）を返却"""
        now = time.time()
        active = self._rain_active and (self._rain_expires_at == 0 or now < self._rain_expires_at)
        return {
            "active": active,
            "expiresAt": self._rain_expires_at if active else 0,
            "alert": self._rain_alert_info if active else None
        }

    async def set_trigger_active(self, active: bool, duration_sec: int = 1800, alert_info: Optional[Dict[str, Any]] = None):
        """雨雲接近トリガー状態を設定し、MQTT へ状態を同期"""
        from app.services.mqtt_service import mqtt_service
        self._rain_active = active
        if self._rain_auto_off_task and not self._rain_auto_off_task.done():
            self._rain_auto_off_task.cancel()

        if not active:
            self._rain_expires_at = 0.0
            self._rain_alert_info = None
            asyncio.create_task(mqtt_service.publish_disaster_state("rain", False))
            log.info("[RainAlarm] 雨雲接近トリガー状態を OFF に設定しました")
            return

        self._rain_expires_at = time.time() + duration_sec if duration_sec > 0 else 0.0
        self._rain_alert_info = alert_info or {"type": "rain", "time": time.time()}
        asyncio.create_task(mqtt_service.publish_disaster_state("rain", True, self._rain_alert_info))
        log.info(f"[RainAlarm] 雨雲接近トリガー状態を ON に設定しました (有効期限: {duration_sec}秒)")

        if duration_sec > 0:
            async def auto_off():
                try:
                    await asyncio.sleep(duration_sec)
                    self._rain_active = False
                    self._rain_expires_at = 0.0
                    self._rain_alert_info = None
                    asyncio.create_task(mqtt_service.publish_disaster_state("rain", False))
                    log.info("[RainAlarm] 雨雲接近トリガー状態を自動リセット (OFF) にしました")
                except asyncio.CancelledError:
                    pass
            self._rain_auto_off_task = asyncio.create_task(auto_off())

    async def trigger_test_state(self, duration_sec: int = 10) -> Dict[str, Any]:
        """スマートホーム連動テスト用: 一時的に雨雲接近トリガーを ON にする"""
        test_info = {"type": "test", "message": "雨雲接近テスト", "timestamp": datetime.now().isoformat()}
        await self.set_trigger_active(True, duration_sec=duration_sec, alert_info=test_info)
        return {"success": True, "target": "rain", "active": True, "duration": duration_sec}

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        log.info("[RainAlarm] 監視サービスを開始しました")

    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        log.info("[RainAlarm] 監視サービスを停止しました")

    async def _monitor_loop(self):
        """定期監視ループ"""
        while self._running:
            try:
                conf = settings_manager.get().get("rainAlarm", {})
                if conf.get("enabled", False):
                    await self.check_and_notify()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"[RainAlarm] 監視ループエラー: {e}", exc_info=True)

            conf = settings_manager.get().get("rainAlarm", {})
            interval_min = max(1, int(conf.get("checkIntervalMinutes", 5)))
            await asyncio.sleep(interval_min * 60)

    async def get_jma_radar_times(self) -> List[Dict[str, str]]:
        """気象庁の降水ナウキャスト最新時刻リストを取得（キャッシュ付き: 60秒）"""
        now = time.time()
        if self._jma_cache["times"] and (now - self._jma_cache["fetched_at"] < 60):
            return self._jma_cache["times"]

        headers = {"User-Agent": "VoiceHub/1.0 (SmartHome Speaker)"}
        try:
            async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
                res = await client.get(JMA_TARGET_TIMES_URL)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0:
                        self._jma_cache = {"times": data, "fetched_at": now}
                        return data
        except Exception as e:
            log.warning(f"[RainAlarm] 気象庁ナウキャスト時刻取得失敗: {e}")
            if self._jma_cache["times"]:
                return self._jma_cache["times"]
        return []

    async def fetch_forecast(
        self,
        lat: float,
        lon: float,
        provider: str = "auto",
        yahoo_app_id: str = ""
    ) -> Tuple[float, List[Dict[str, Any]], str]:
        """指定した地点の降雨予測データを取得。
        返却値: (現在実況雨量 mm/h, タイムラインリスト, 使用したプロバイダー名)
        """
        chosen_provider = provider
        if chosen_provider == "auto":
            chosen_provider = "yahoo" if yahoo_app_id.strip() else "openmeteo"

        cache_key = f"{round(lat, 3)}_{round(lon, 3)}_{chosen_provider}"
        now_ts = time.time()
        cached = self._forecast_cache.get(cache_key)
        if cached and (now_ts - cached["cached_at"] < 60.0):
            return cached["curr"], cached["timeline"], cached["provider_used"]

        if chosen_provider == "yahoo":
            try:
                curr, timeline = await self._fetch_yahoo(lat, lon, yahoo_app_id)
                provider_used = "Yahoo! 気象情報API"
            except Exception as e:
                log.warning(f"[RainAlarm] Yahoo! API失敗、Open-Meteoにフォールバックします: {e}")
                if provider == "auto":
                    curr, timeline = await self._fetch_openmeteo(lat, lon)
                    provider_used = "Open-Meteo (フォールバック)"
                else:
                    raise e
        else:
            # Open-Meteo
            curr, timeline = await self._fetch_openmeteo(lat, lon)
            provider_used = "Open-Meteo"

        self._forecast_cache[cache_key] = {
            "curr": curr,
            "timeline": timeline,
            "provider_used": provider_used,
            "cached_at": now_ts
        }
        return curr, timeline, provider_used

    async def _fetch_yahoo(
        self,
        lat: float,
        lon: float,
        app_id: str
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Yahoo! YOLP 気象情報API から 10分刻み・60分後までの降水強度を取得"""
        if not app_id.strip():
            raise ValueError("Yahoo! Client ID (App ID) が設定されていません")

        params = {
            "coordinates": f"{lon:.6f},{lat:.6f}",
            "appid": app_id.strip(),
            "output": "json"
        }
        headers = {"User-Agent": "VoiceHub/1.0 (SmartHome Speaker)"}
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            resp = await client.get(YAHOO_WEATHER_API_URL, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Yahoo API returned HTTP {resp.status_code}: {resp.text[:120]}")

            data = resp.json()
            features = data.get("Feature", [])
            if not features:
                raise ValueError("Yahoo API returned empty feature data")

            weather_list = features[0].get("Property", {}).get("WeatherList", {}).get("Weather", [])
            if not weather_list:
                raise ValueError("Yahoo API returned empty weather list")

            timeline = []
            current_rainfall = 0.0

            # observation（直近実況）と forecast（未来予測）
            base_time = None
            for idx, w in enumerate(weather_list):
                w_type = w.get("Type", "")
                date_str = str(w.get("Date", ""))  # YYYYMMDDHHMI
                rainfall = float(w.get("Rainfall", 0.0))

                dt = None
                time_disp = ""
                if len(date_str) == 12:
                    try:
                        dt = datetime.strptime(date_str, "%Y%m%d%H%M")
                        time_disp = dt.strftime("%H:%M")
                    except Exception:
                        time_disp = date_str[-4:-2] + ":" + date_str[-2:]

                if w_type == "observation":
                    current_rainfall = rainfall
                    if dt:
                        base_time = dt
                    timeline.append({
                        "time": time_disp,
                        "date": date_str,
                        "minutesAhead": 0,
                        "rainfall": rainfall,
                        "isObservation": True
                    })
                elif w_type == "forecast":
                    minutes_ahead = (idx) * 10
                    if base_time and dt:
                        diff = int((dt - base_time).total_seconds() / 60)
                        if diff > 0:
                            minutes_ahead = diff
                    timeline.append({
                        "time": time_disp,
                        "date": date_str,
                        "minutesAhead": minutes_ahead,
                        "rainfall": rainfall,
                        "isObservation": False
                    })

            return current_rainfall, timeline

    async def _fetch_openmeteo(
        self,
        lat: float,
        lon: float
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Open-Meteo API から 15分刻み降水予測を取得 (APIキー不要)"""
        params = {
            "latitude": f"{lat:.6f}",
            "longitude": f"{lon:.6f}",
            "minutely_15": "precipitation",
            "forecast_days": 1,
            "timezone": "Asia/Tokyo"
        }
        headers = {"User-Agent": "VoiceHub/1.0 (SmartHome Speaker)"}
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            resp = await client.get(OPEN_METEO_API_URL, params=params)
            if resp.status_code != 200:
                raise RuntimeError(f"Open-Meteo returned HTTP {resp.status_code}: {resp.text[:120]}")

            data = resp.json()
            minutely = data.get("minutely_15", {})
            times = minutely.get("time", [])
            precips = minutely.get("precipitation", [])

            now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
            timeline = []
            current_rainfall = 0.0

            # 現在時刻に最も近いインデックスを探す
            current_idx = 0
            for i, t_str in enumerate(times):
                if t_str <= now_str:
                    current_idx = i
                else:
                    break

            # 直近と今後1時間分（最大4〜5コマ: 15分刻み）を抽出
            slice_end = min(len(times), current_idx + 6)
            for offset, idx in enumerate(range(current_idx, slice_end)):
                t_str = times[idx]
                time_disp = t_str.split("T")[-1] if "T" in t_str else t_str
                # 15分間の降水量 (mm) -> 1時間換算 (mm/h = mm * 4)
                raw_p = float(precips[idx]) if idx < len(precips) else 0.0
                hourly_equiv = round(raw_p * 4.0, 1)

                is_obs = (offset == 0)
                if is_obs:
                    current_rainfall = hourly_equiv

                timeline.append({
                    "time": time_disp,
                    "date": t_str,
                    "minutesAhead": offset * 15,
                    "rainfall": hourly_equiv,
                    "isObservation": is_obs
                })

            return current_rainfall, timeline

    async def check_and_notify(self) -> Dict[str, Any]:
        """降雨状況をチェックし、条件に合致すればアナウンスを発声"""
        conf = settings_manager.get().get("rainAlarm", {})
        if not conf.get("enabled", False):
            return {"status": "disabled", "message": "雨アラームは無効化されています"}

        lat = float(conf.get("latitude", 35.6812))
        lon = float(conf.get("longitude", 139.7671))
        provider = conf.get("provider", "auto")
        yahoo_app_id = conf.get("yahooAppId", "")
        threshold = float(conf.get("thresholdMm", 0.5))
        heavy_threshold = float(conf.get("heavyThresholdMm", 10.0))
        cooldown_sec = int(conf.get("cooldownMinutes", 30)) * 60

        notify_approaching = conf.get("notifyApproaching", True)
        notify_heavy = conf.get("notifyHeavy", True)
        notify_clearing = conf.get("notifyClearing", True)

        now = time.time()
        self._last_check_time = now

        try:
            curr_rain, timeline, used_provider = await self.fetch_forecast(
                lat, lon, provider, yahoo_app_id
            )
        except Exception as e:
            log.error(f"[RainAlarm] 天気データ取得失敗: {e}", exc_info=True)
            self._last_status.update({
                "status": "error",
                "lastChecked": datetime.now().isoformat(),
                "error": "Failed to fetch weather forecast"
            })
            return {"status": "error", "error": "Failed to fetch weather forecast"}

        self._last_status.update({
            "status": "active",
            "lastChecked": datetime.now().isoformat(),
            "providerUsed": used_provider,
            "currentRainfall": curr_rain,
            "timeline": timeline,
            "error": None
        })

        # アナウンス判定
        alert_triggered = False
        alert_type = None
        alert_message = ""

        # 1. 激しい雨・豪雨警戒判定 (notifyHeavy)
        if notify_heavy and (now - self._last_heavy_notify_time > cooldown_sec):
            # 今後60分以内で heavy_threshold 以上の地点があるか探す
            heavy_point = next((p for p in timeline if p["rainfall"] >= heavy_threshold), None)
            if heavy_point:
                min_ahead = heavy_point["minutesAhead"]
                rain_val = heavy_point["rainfall"]
                if min_ahead == 0:
                    alert_message = f"【大雨警戒】現在、毎時約{rain_val:.1f}ミリの非常に激しい雨が降っています。雨雲の急激な発達や浸水にご注意ください。"
                else:
                    alert_message = f"【大雨警戒】約{min_ahead}分後に毎時約{rain_val:.1f}ミリの強い雨が降る見込みです。激しい雨にご注意ください。"
                alert_type = "heavy"
                alert_triggered = True
                self._last_heavy_notify_time = now

        # 2. 雨雲接近・降り始め判定 (notifyApproaching)
        if not alert_triggered and notify_approaching and (now - self._last_approaching_notify_time > cooldown_sec):
            # 現在実況が雨なし (curr_rain < threshold) で、未来に threshold 以上の雨雲があるか
            if curr_rain < threshold:
                first_rain_point = next(
                    (p for p in timeline if not p["isObservation"] and p["rainfall"] >= threshold),
                    None
                )
                if first_rain_point:
                    min_ahead = first_rain_point["minutesAhead"]
                    rain_val = first_rain_point["rainfall"]
                    alert_message = (
                        f"【雨雲接近】まもなく約{min_ahead}分後に雨が降り始める見込みです。"
                        f"予想される雨の強さは毎時約{rain_val:.1f}ミリです。洗濯物の取り込みや雨具の準備をしてください。"
                    )
                    alert_type = "approaching"
                    alert_triggered = True
                    self._last_approaching_notify_time = now

        # 3. 雨上がり判定 (notifyClearing)
        if not alert_triggered and notify_clearing and (now - self._last_clearing_notify_time > cooldown_sec):
            # 前回雨が降っていた状態から、現在雨なし (< threshold) かつ直近予測も雨なしへ移行
            if self._is_raining_state and curr_rain < threshold:
                # 直近30分以内も雨がないか確認
                future_rains = [p["rainfall"] for p in timeline if not p["isObservation"] and p["minutesAhead"] <= 30]
                if all(r < threshold for r in future_rains):
                    alert_message = "【雨上がり】雨が止んだ見込みです。傘などのお忘れ物にご注意ください。"
                    alert_type = "clearing"
                    alert_triggered = True
                    self._last_clearing_notify_time = now

        # 状態更新
        self._is_raining_state = (curr_rain >= threshold)

        # 音声アナウンス送出 & スマートホームトリガー連動
        if alert_triggered and alert_message:
            log.info(f"[RainAlarm] ★ アラート検知 ({alert_type}): {alert_message}")
            self._last_status["lastAlert"] = {
                "type": alert_type,
                "message": alert_message,
                "timestamp": datetime.now().isoformat()
            }
            if alert_type in ("heavy", "approaching"):
                await self.set_trigger_active(True, duration_sec=1800, alert_info={"type": alert_type, "message": alert_message})
            elif alert_type == "clearing":
                await self.set_trigger_active(False)

            await self._speak_alert(alert_message, alert_type)

        return {
            "status": "ok",
            "providerUsed": used_provider,
            "currentRainfall": curr_rain,
            "alertTriggered": alert_triggered,
            "alertType": alert_type,
            "alertMessage": alert_message,
            "timeline": timeline
        }

    async def _speak_alert(self, text: str, alert_type: str):
        """設定先スピーカーへアナウンスを発話（DND評価・保留・履歴記録は speech_service に委譲）"""
        conf = settings_manager.get().get("rainAlarm", {})
        disaster_conf = settings_manager.get().get("disaster", {})

        # 防災設定のスピーカー指定と連動（rainAlarmで個別設定されていない場合はdisaster設定にフォールバック）
        scope = conf.get("targetScope") or disaster_conf.get("targetScope", "all")
        target_devices = conf.get("targetDevices") or disaster_conf.get("targetDevices", ["ALL"])
        chime = conf.get("chime", "notice_info")

        # ターゲット決定（SpeechService準拠: 'default' / list of devices / ['ALL']）
        if scope == "default":
            targets = ["default"]
        elif scope == "specific" and target_devices:
            targets = target_devices
        else:
            targets = ["ALL"]

        log.info(f"[RainAlarm] スピーカーへ雨アラームを発話します (scope={scope}, targets={targets}, chime={chime})")
        try:
            await speech_service.speak(
                text=text,
                targets=targets,
                chime=chime,
                urgent=False,
                source="rain_alarm",
                source_label="雨アラーム",
                client_name="雨アラームサービス"
            )
        except Exception as e:
            log.error(f"[RainAlarm] 音声発話失敗: {e}")

    async def test_alert(self, alert_type: str = "approaching") -> Dict[str, Any]:
        """テストアナウンスを即時発話"""
        conf = settings_manager.get().get("rainAlarm", {})
        loc_name = conf.get("locationName", "登録地点")

        if alert_type == "heavy":
            msg = f"【大雨警戒テスト】{loc_name}付近で約15分後に毎時約15ミリの強い雨が降る見込みです。激しい雨にご注意ください。"
        elif alert_type == "clearing":
            msg = f"【雨上がりテスト】{loc_name}付近で雨が止んだ見込みです。傘のお忘れ物にご注意ください。"
        else:
            msg = f"【雨雲接近テスト】{loc_name}付近でまもなく約20分後に雨が降り始める見込みです。予想される雨の強さは毎時約2.5ミリです。洗濯物の取り込み等にご注意ください。"

        log.info(f"[RainAlarm] テスト発声実行 ({alert_type}): {msg}")
        if alert_type in ("heavy", "approaching"):
            await self.set_trigger_active(True, duration_sec=15, alert_info={"type": alert_type, "message": msg, "test": True})
        elif alert_type == "clearing":
            await self.set_trigger_active(False)

        await self._speak_alert(msg, alert_type)
        return {"status": "ok", "message": msg, "alertType": alert_type}

    def get_status(self) -> Dict[str, Any]:
        """現在の雨アラーム状態を返す"""
        conf = settings_manager.get().get("rainAlarm", {})
        return {
            "config": {
                "enabled": conf.get("enabled", False),
                "provider": conf.get("provider", "auto"),
                "hasYahooAppId": bool((conf.get("yahooAppId") or "").strip()),
                "latitude": conf.get("latitude", 35.6812),
                "longitude": conf.get("longitude", 139.7671),
                "locationName": conf.get("locationName", "東京都千代田区"),
                "checkIntervalMinutes": conf.get("checkIntervalMinutes", 5),
                "thresholdMm": conf.get("thresholdMm", 0.5),
                "heavyThresholdMm": conf.get("heavyThresholdMm", 10.0),
                "notifyApproaching": conf.get("notifyApproaching", True),
                "notifyHeavy": conf.get("notifyHeavy", True),
                "notifyClearing": conf.get("notifyClearing", True),
                "targetScope": conf.get("targetScope", "all"),
                "targetDevices": conf.get("targetDevices", ["ALL"]),
                "cooldownMinutes": conf.get("cooldownMinutes", 30),
                "chime": conf.get("chime", "notice_info")
            },
            "state": self._last_status
        }


rain_alarm_service = RainAlarmService()
