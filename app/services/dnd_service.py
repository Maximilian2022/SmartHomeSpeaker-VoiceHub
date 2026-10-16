import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from app.config import DATA_DIR
from app.services.settings_service import settings_manager

DND_QUEUE_FILE = DATA_DIR / "dnd_queue.json"

class DndService:
    def __init__(self):
        self.queue: List[Dict[str, Any]] = self._load_queue()

    def _load_queue(self) -> List[Dict[str, Any]]:
        if DND_QUEUE_FILE.exists():
            try:
                with open(DND_QUEUE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_queue(self):
        try:
            with open(DND_QUEUE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.queue, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DndService] Queue save error: {e}")

    def evaluate(self, active_event_title: Optional[str] = None, urgent: bool = False) -> Dict[str, Any]:
        """
        DND 状態を多層評価
        return: { active: bool, reason: str, action: str, whisperVolume: int, targetScope: str, targetDevices: list }
        """
        dnd_conf = settings_manager.get().get("dnd", {})
        if not dnd_conf.get("enabled", True) or urgent:
            return {"active": False, "reason": "", "action": "none"}

        action = dnd_conf.get("action", "skip")
        whisper_vol = dnd_conf.get("whisperVolume", 10)
        target_scope = dnd_conf.get("targetScope", "all")
        target_devices = dnd_conf.get("targetDevices", [])

        now = datetime.now()
        now_ts = now.timestamp()

        # 1. 手動即時ミュート
        manual_until = dnd_conf.get("manualUntil")
        if manual_until and manual_until > now_ts:
            return {
                "active": True,
                "reason": dnd_conf.get("manualReason") or "手動一時ミュート中",
                "action": action,
                "whisperVolume": whisper_vol,
                "targetScope": target_scope,
                "targetDevices": target_devices
            }

        # 2. カレンダー会議連動
        if dnd_conf.get("calendarEnabled", True) and active_event_title:
            mode = dnd_conf.get("calendarMode", "keywords")
            if mode == "all":
                return {
                    "active": True,
                    "reason": f"カレンダー予定中: {active_event_title}",
                    "action": action,
                    "whisperVolume": whisper_vol,
                    "targetScope": target_scope,
                    "targetDevices": target_devices
                }
            else:
                keywords_str = dnd_conf.get("calendarKeywords", "")
                keywords = [k.strip().lower() for k in keywords_str.split(",") if k.strip()]
                title_lower = active_event_title.lower()
                matched = next((k for k in keywords if k in title_lower), None)
                if matched:
                    return {
                        "active": True,
                        "reason": f"会議中 ({matched}): {active_event_title}",
                        "action": action,
                        "whisperVolume": whisper_vol,
                        "targetScope": target_scope,
                        "targetDevices": target_devices
                    }

        # 3. 曜日・時間帯定時スケジュール
        if dnd_conf.get("scheduleEnabled", False):
            current_day = str((now.weekday() + 1) % 7) # 0=Sun..6=Sat
            current_time = now.strftime("%H:%M")

            for s in dnd_conf.get("schedules", []):
                if not s.get("enabled", True):
                    continue
                if current_day in s.get("days", []):
                    st = s.get("startTime", "00:00")
                    et = s.get("endTime", "23:59")
                    if st <= et:
                        in_range = (st <= current_time <= et)
                    else: # 日またぎ
                        in_range = (current_time >= st or current_time <= et)

                    if in_range:
                        return {
                            "active": True,
                            "reason": f"定時スケジュール ({s.get('name', 'DND')})",
                            "action": action,
                            "whisperVolume": whisper_vol,
                            "targetScope": target_scope,
                            "targetDevices": target_devices
                        }

        return {"active": False, "reason": "", "action": "none"}

    def add_to_queue(self, payload: Dict[str, Any]):
        item = {
            "id": f"q_{int(time.time()*1000)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload
        }
        self.queue.append(item)
        self._save_queue()

    def get_queue(self) -> List[Dict[str, Any]]:
        return self.queue

    def clear_queue(self) -> List[Dict[str, Any]]:
        cleared = list(self.queue)
        self.queue = []
        self._save_queue()
        return cleared

dnd_service = DndService()
