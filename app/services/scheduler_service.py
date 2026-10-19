import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from zoneinfo import ZoneInfo
from app.config import DATA_DIR, settings
from app.services.speech_service import speech_service

SCHEDULE_FILE = DATA_DIR / "schedules.json"

WEEKDAY_NAMES_MAP = {
    "0": "日", "1": "月", "2": "火", "3": "水", "4": "木", "5": "金", "6": "土", "7": "日"
}

def build_cron_expression(frequency: str, time_str: str, weekdays: Optional[List[int]] = None) -> str:
    parts = (time_str or "07:00").split(":")
    minute = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    hour = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 7

    if frequency == "daily":
        return f"{minute} {hour} * * *"
    elif frequency == "weekdays":
        return f"{minute} {hour} * * 1-5"
    elif frequency == "weekends":
        return f"{minute} {hour} * * 0,6"
    elif frequency == "custom_days" and weekdays:
        days = ",".join(str(d) for d in sorted(weekdays))
        return f"{minute} {hour} * * {days}"
    return f"{minute} {hour} * * *"

def format_human_readable(sched: Dict[str, Any]) -> str:
    freq = sched.get("frequency")
    t = sched.get("time", "")
    if freq and t:
        if freq == "daily":
            return f"毎日 {t}"
        elif freq == "weekdays":
            return f"平日 (月〜金) {t}"
        elif freq == "weekends":
            return f"土日 {t}"
        elif freq == "custom_days":
            w = sched.get("weekdays", [])
            names = "・".join(WEEKDAY_NAMES_MAP.get(str(d), str(d)) for d in w)
            return f"毎週 {names} {t}"
    return sched.get("cron", "")

def match_cron_field(pattern: str, val: int) -> bool:
    if pattern == "*":
        return True
    for part in pattern.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            sub = part.split("-")
            if len(sub) == 2 and sub[0].isdigit() and sub[1].isdigit():
                if int(sub[0]) <= val <= int(sub[1]):
                    return True
        elif "/" in part:
            sub = part.split("/")
            step = int(sub[1]) if len(sub) == 2 and sub[1].isdigit() else 1
            if val % step == 0:
                return True
        elif part.isdigit() and int(part) == val:
            return True
    return False

def matches_cron(cron_expr: str, dt: datetime) -> bool:
    try:
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False
        m_pat, h_pat, dom_pat, mon_pat, dow_pat = parts
        if not match_cron_field(m_pat, dt.minute):
            return False
        if not match_cron_field(h_pat, dt.hour):
            return False
        if not match_cron_field(dom_pat, dt.day):
            return False
        if not match_cron_field(mon_pat, dt.month):
            return False
        # Python weekday: Mon=0 .. Sun=6, Cron: Sun=0 or 7, Mon=1 .. Sat=6
        cron_dow = 0 if dt.weekday() == 6 else dt.weekday() + 1
        if not (match_cron_field(dow_pat, cron_dow) or (cron_dow == 0 and match_cron_field(dow_pat, 7))):
            return False
        return True
    except Exception:
        return False

class SchedulerService:
    def __init__(self):
        self.schedules: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []
        self._bg_task: Optional[asyncio.Task] = None
        self.tz = ZoneInfo(settings.tz or "Asia/Tokyo")
        self.load()

    def load(self):
        try:
            if SCHEDULE_FILE.exists():
                data = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.schedules = data
                elif isinstance(data, dict):
                    self.schedules = data.get("schedules", [])
                    self.history = data.get("history", [])
                for s in self.schedules:
                    if not s.get("readableFrequency"):
                        s["readableFrequency"] = format_human_readable(s)
            else:
                self.schedules = []
        except Exception as e:
            print(f"[SchedulerService] Load failed: {e}")
            self.schedules = []

    def save(self):
        try:
            SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schedules": self.schedules,
                "history": self.history[-100:]  # 直近100件
            }
            tmp_path = SCHEDULE_FILE.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(SCHEDULE_FILE)
        except Exception as e:
            print(f"[SchedulerService] Save failed: {e}")

    def get_schedules(self) -> List[Dict[str, Any]]:
        return self.schedules

    def get_history(self) -> List[Dict[str, Any]]:
        return self.history

    def add_schedule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        cron = data.get("cron") or build_cron_expression(
            data.get("frequency", "daily"),
            data.get("time", "07:00"),
            data.get("weekdays")
        )
        new_sched = {
            "id": data.get("id") or str(uuid.uuid4()),
            "name": data.get("name", "無題のスケジュール"),
            "text": data.get("text", ""),
            "cron": cron,
            "frequency": data.get("frequency", "daily"),
            "time": data.get("time", "07:00"),
            "weekdays": data.get("weekdays", []),
            "readableFrequency": format_human_readable(data),
            "deviceIps": data.get("deviceIps") or ([data.get("deviceIp")] if data.get("deviceIp") else ["default"]),
            "voice": data.get("voice", settings.default_voice),
            "rate": data.get("rate", "+0%"),
            "pitch": data.get("pitch", "+0Hz"),
            "volumeLevel": data.get("volumeLevel", 1.0),
            "enabled": data.get("enabled", True),
            "createdAt": datetime.now(self.tz).isoformat()
        }
        self.schedules.append(new_sched)
        self.save()
        return new_sched

    def update_schedule(self, sched_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for i, s in enumerate(self.schedules):
            if s.get("id") == sched_id:
                cron = data.get("cron") or build_cron_expression(
                    data.get("frequency", s.get("frequency", "daily")),
                    data.get("time", s.get("time", "07:00")),
                    data.get("weekdays", s.get("weekdays", []))
                )
                updated = {**s, **data, "cron": cron}
                updated["readableFrequency"] = format_human_readable(updated)
                self.schedules[i] = updated
                self.save()
                return updated
        return None

    def delete_schedule(self, sched_id: str) -> bool:
        initial_len = len(self.schedules)
        self.schedules = [s for s in self.schedules if s.get("id") != sched_id]
        if len(self.schedules) < initial_len:
            self.save()
            return True
        return False

    def toggle_schedule(self, sched_id: str) -> Optional[Dict[str, Any]]:
        for s in self.schedules:
            if s.get("id") == sched_id:
                s["enabled"] = not s.get("enabled", True)
                self.save()
                return s
        return None

    async def run_schedule_now(self, sched_id: str) -> Dict[str, Any]:
        target = next((s for s in self.schedules if s.get("id") == sched_id), None)
        if not target:
            raise ValueError("Schedule not found")
        return await self._execute_schedule(target, manual=True)

    async def _execute_schedule(self, sched: Dict[str, Any], manual: bool = False) -> Dict[str, Any]:
        text = sched.get("text", "")
        targets = sched.get("deviceIps") or ["default"]
        vol = sched.get("volumeLevel")
        voice = sched.get("voice", settings.default_voice)
        rate = sched.get("rate", "+0%")
        pitch = sched.get("pitch", "+0Hz")

        vol_val = None
        if vol is not None and str(vol).strip() != "":
            try:
                vol_val = float(vol)
            except ValueError:
                pass

        try:
            res = await speech_service.speak(
                text=text,
                targets=targets,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume_level=vol_val,
                urgent=False
            )
            hist = {
                "scheduleId": sched.get("id"),
                "name": sched.get("name"),
                "text": text,
                "status": "success",
                "manual": manual,
                "timestamp": datetime.now(self.tz).isoformat()
            }
            self.history.append(hist)
            sched["lastRun"] = datetime.now(self.tz).isoformat()
            self.save()
            return res
        except Exception as e:
            hist = {
                "scheduleId": sched.get("id"),
                "name": sched.get("name"),
                "text": text,
                "status": "error",
                "error": str(e),
                "manual": manual,
                "timestamp": datetime.now(self.tz).isoformat()
            }
            self.history.append(hist)
            self.save()
            raise

    async def start(self):
        """毎分チェックするバックグラウンドタスクを開始"""
        if self._bg_task and not self._bg_task.done():
            return
        self._bg_task = asyncio.create_task(self._cron_loop())

    async def _cron_loop(self):
        last_minute = -1
        while True:
            try:
                now = datetime.now(self.tz)
                if now.minute != last_minute and now.second < 10:
                    last_minute = now.minute
                    for sched in self.schedules:
                        if sched.get("enabled", True):
                            cron_expr = sched.get("cron", "")
                            if matches_cron(cron_expr, now):
                                print(f"[SchedulerService] Triggering: {sched.get('name')}")
                                asyncio.create_task(self._execute_schedule(sched))
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[SchedulerService] Loop error: {e}")
                await asyncio.sleep(10)

scheduler_service = SchedulerService()
