import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from app.config import DATA_DIR
from app.services.settings_service import settings_manager
from app.services.calendar_service import calendar_service
from app.core.logger import get_logger

log = get_logger("DND")
DND_QUEUE_FILE = DATA_DIR / "dnd_queue.json"

def _normalize_target_key(targets: Any) -> Tuple[str, ...]:
    if targets is None:
        return ("__default__",)
    if isinstance(targets, str):
        parts = [t.strip().lower() for t in targets.split(",") if t.strip()]
    elif isinstance(targets, (list, tuple)):
        parts = [str(t).strip().lower() for t in targets if str(t).strip()]
    else:
        parts = [str(targets).strip().lower()]
    return tuple(sorted(parts)) if parts else ("__default__",)


class DndService:

    def __init__(self):
        self.queue: List[Dict[str, Any]] = self._load_queue()
        self.history: List[Dict[str, Any]] = []
        self.was_dnd_active: bool = False
        self._speaker_executor: Optional[Callable] = None
        self._tick_task: Optional[asyncio.Task] = None

    def set_speaker_executor(self, executor: Callable):
        self._speaker_executor = executor

    def start_background_tasks(self):
        if self._tick_task is None or self._tick_task.done():
            self._tick_task = asyncio.create_task(self._tick_loop())

    async def _tick_loop(self):
        log.info("Starting DND background monitor loop...")
        while True:
            try:
                await self.tick()
            except Exception as e:
                log.error(f"Error in DND tick: {e}", exc_info=True)
            await asyncio.sleep(60)

    async def tick(self):
        status = self.get_global_status()
        is_active = status.get("isActive", False)
        if self.was_dnd_active and not is_active:
            log.info("DND mode deactivated. Flushing queued notifications...")
            await self.check_and_flush_queue()
        self.was_dnd_active = is_active

    def record_history(self, text: str, reason: str, action: str, target: str = ""):
        self.history.insert(0, {
            "id": f"dnd_hist_{int(time.time()*1000)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text": text,
            "target": target,
            "reason": reason,
            "action": action
        })
        if len(self.history) > 50:
            self.history = self.history[:50]

    def get_history(self) -> List[Dict[str, Any]]:
        return self.history

    def clear_history(self):
        self.history = []

    def _load_queue(self) -> List[Dict[str, Any]]:
        if DND_QUEUE_FILE.exists():
            try:
                with open(DND_QUEUE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        now_ts = time.time()
                        valid = []
                        for item in data:
                            if not item or not item.get("text"):
                                continue
                            valid.append(item)
                        return valid
            except Exception as e:
                log.warning(f"Failed to load DND queue: {e}")
        return []

    def _save_queue(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(DND_QUEUE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.queue, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"Queue save error: {e}")

    def evaluate(self, active_event_title: Optional[str] = None, urgent: bool = False) -> Dict[str, Any]:
        """
        DND 状態を多層評価
        """
        dnd_conf = settings_manager.get().get("dnd", {})
        if not dnd_conf.get("enabled", True) or urgent:
            return {"active": False, "isActive": False, "reason": "", "action": "none"}

        action = dnd_conf.get("action", "skip")
        whisper_vol = dnd_conf.get("whisperVolume", 10)
        target_scope = dnd_conf.get("targetScope", "all")
        target_devices = dnd_conf.get("targetDevices", [])

        now = datetime.now()
        now_ts = now.timestamp()

        # 1. 手動即時ミュート
        manual_until = dnd_conf.get("manualUntil")
        if manual_until:
            try:
                until_val = float(manual_until)
            except (ValueError, TypeError):
                until_val = 0
            if until_val > now_ts:
                return {
                    "active": True,
                    "isActive": True,
                    "reason": dnd_conf.get("manualReason") or "手動一時ミュート中",
                    "action": action,
                    "whisperVolume": whisper_vol,
                    "targetScope": target_scope,
                    "targetDevices": target_devices,
                    "until": datetime.fromtimestamp(until_val, tz=timezone.utc).isoformat()
                }

        # 2. カレンダー会議連動
        include_all_day = bool(dnd_conf.get("calendarIncludeAllDay", False))
        meeting_titles = [active_event_title] if active_event_title else calendar_service.get_current_meeting_titles(include_all_day=include_all_day)
        if dnd_conf.get("calendarEnabled", True) and meeting_titles:
            mode = dnd_conf.get("calendarMode", "keywords")
            if mode == "all":
                first_title = meeting_titles[0]
                return {
                    "active": True,
                    "isActive": True,
                    "reason": f"カレンダー予定中: {first_title}",
                    "action": action,
                    "whisperVolume": whisper_vol,
                    "targetScope": target_scope,
                    "targetDevices": target_devices
                }
            else:
                keywords_str = dnd_conf.get("calendarKeywords", "")
                keywords = [k.strip().lower() for k in keywords_str.split(",") if k.strip()]
                for m_title in meeting_titles:
                    title_lower = m_title.lower()
                    matched = next((k for k in keywords if k in title_lower), None)
                    if matched:
                        return {
                            "active": True,
                            "isActive": True,
                            "reason": f"会議中 ({matched}): {m_title}",
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
                            "isActive": True,
                            "reason": f"定時スケジュール ({s.get('name', 'DND')})",
                            "action": action,
                            "whisperVolume": whisper_vol,
                            "targetScope": target_scope,
                            "targetDevices": target_devices
                        }

        return {"active": False, "isActive": False, "reason": "", "action": "none"}

    def get_global_status(self) -> Dict[str, Any]:
        """
        GUI が要求する完全なステータス構造
        """
        dnd_conf = settings_manager.get().get("dnd", {})
        meeting_title = calendar_service.get_current_meeting_title()
        eval_res = self.evaluate(active_event_title=meeting_title)
        q_len = len(self.queue)

        active_cal = None
        if meeting_title:
            active_cal = {
                "summary": meeting_title,
                "isAllDay": False
            }

        return {
            "enabled": bool(dnd_conf.get("enabled", True)),
            "isActive": eval_res.get("isActive", False),
            "active": eval_res.get("active", False),
            "reason": eval_res.get("reason") or None,
            "until": eval_res.get("until") or None,
            "action": eval_res.get("action", "skip"),
            "whisperVolume": eval_res.get("whisperVolume", 10),
            "activeCalendarEvent": active_cal,
            "queuedCount": q_len,
            "queueCount": q_len
        }

    def add_to_queue(self, payload: Dict[str, Any]):
        item = {
            "id": f"q_{int(time.time()*1000)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload
        }
        self.queue.append(item)
        self._save_queue()
        log.info(f"Appended message to DND queue ({len(self.queue)} items): '{payload.get('text', '')[:30]}'")

    def get_queue(self) -> List[Dict[str, Any]]:
        return self.queue

    def clear_queue(self) -> List[Dict[str, Any]]:
        cleared = list(self.queue)
        self.queue = []
        self._save_queue()
        return cleared

    async def check_and_flush_queue(self) -> int:
        if not self.queue or not self._speaker_executor:
            return 0

        items = self.clear_queue()
        log.info(f"Flushing {len(items)} queued messages after DND release...")

        from app.services.ai_service import ai_service
        dnd_conf = settings_manager.get().get("dnd", {})
        ai_enabled = dnd_conf.get("aiSummaryEnabled", True)
        threshold = int(dnd_conf.get("aiSummaryThreshold", 2))

        # 宛先ごとにグループ化 (キュー投入順を保持)
        groups: Dict[Tuple[str, ...], List[Dict[str, Any]]] = {}
        for item in items:
            k = _normalize_target_key(item.get("targets"))
            if k not in groups:
                groups[k] = []
            groups[k].append(item)

        for target_key, group_items in groups.items():
            # 発話宛先 (元のリクエストで指定されていた targets を尊重。未指定の場合は None のまま)
            target_speaker = None if target_key == ("__default__",) else group_items[0].get("targets")
            messages = [it.get("text", "") for it in group_items if it.get("text")]

            if ai_enabled and len(messages) >= threshold:
                try:
                    summary_text = await ai_service.summarize_dnd_messages(messages)
                    if summary_text:
                        announce_text = f"おやすみ・会議モードが終了しました。保留されていた {len(group_items)} 件の通知をAIが要約してお知らせします。{summary_text}"
                        await self._speaker_executor(
                            text=announce_text,
                            targets=target_speaker,
                            urgent=True,
                            source="dnd_queue",
                            source_label="DND保留再生"
                        )
                        await asyncio.sleep(0.5)
                        continue
                except Exception as e:
                    log.warning(f"AI summarization failed for target {target_key}, falling back to sequential play: {e}")

            # AI要約無効、閾値未満、または要約失敗時は個別再生
            for it in group_items:
                t = it.get("text", "")
                if t:
                    await self._speaker_executor(
                        text=t,
                        targets=it.get("targets"),
                        urgent=True,
                        source="dnd_queue",
                        source_label="DND保留再生"
                    )
                    await asyncio.sleep(0.5)

        return len(items)

    # エイリアス
    get_status = get_global_status

dnd_service = DndService()
