import os
import json
import uuid
import asyncio
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from zoneinfo import ZoneInfo

from app.config import DATA_DIR, settings
from app.services.speech_service import speech_service
from app.core.logger import get_logger

log = get_logger("ScheduledSpeech")

SCHEDULED_SPEECHES_FILE = DATA_DIR / "scheduled_speeches.json"


def parse_schedule_time(time_val: Any, tz: ZoneInfo) -> Optional[datetime]:
    """
    様々な形式の発声指定日時をパースして timezone-aware な datetime を返す。
    - None または 空文字: None
    - datetime オブジェクト: tz を考慮して返却
    - 相対指定: '+5m', '+10min', '+30s', '+1h', '+2d' など
    - 時刻のみ: '07:30', '15:45:30' など (今日のその時刻)
    - ISO 8601: '2026-10-19T08:30:00+09:00', '2026-10-19 08:30:00', '2026-10-19T08:30:00'
    - UNIX タイムスタンプ: 1792345678 (秒) または 1792345678000 (ミリ秒)
    """
    if time_val is None:
        return None

    now = datetime.now(tz)

    if isinstance(time_val, datetime):
        if time_val.tzinfo is None:
            return time_val.replace(tzinfo=tz)
        return time_val.astimezone(tz)

    # 数値（UNIXタイムスタンプ）の処理
    if isinstance(time_val, (int, float)):
        try:
            ts = float(time_val)
            if ts > 1e11:  # ミリ秒
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=tz)
        except Exception:
            return None

    str_val = str(time_val).strip()
    if not str_val:
        return None

    # 数値文字列（UNIXタイムスタンプ）
    if str_val.isdigit() or (str_val.replace(".", "", 1).isdigit() and "." in str_val):
        try:
            ts = float(str_val)
            if ts > 1e11:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=tz)
        except Exception:
            pass

    # 相対時間指定のチェック (+5m, +10min, +1h, 30s など)
    rel_match = re.match(r"^\+?(\d+)\s*(s|sec|seconds?|m|min|minutes?|h|hours?|d|days?)$", str_val, re.IGNORECASE)
    if rel_match:
        amount = int(rel_match.group(1))
        unit = rel_match.group(2).lower()
        if unit.startswith("s"):
            return now + timedelta(seconds=amount)
        elif unit.startswith("m"):
            return now + timedelta(minutes=amount)
        elif unit.startswith("h"):
            return now + timedelta(hours=amount)
        elif unit.startswith("d"):
            return now + timedelta(days=amount)

    # 時刻のみの指定 (HH:MM または HH:MM:SS)
    time_only_match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", str_val)
    if time_only_match:
        hour = int(time_only_match.group(1))
        minute = int(time_only_match.group(2))
        second = int(time_only_match.group(3) or 0)
        target = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
        return target

    # ISO 8601 および 一般的な日時文字列のパース
    # 例: 2026-10-19T08:30:00, 2026-10-19 08:30:00
    clean_str = str_val.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        else:
            dt = dt.astimezone(tz)
        return dt
    except Exception:
        pass

    # 各種フォーマットフォールバック
    date_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%m/%d %H:%M",
    ]
    for fmt in date_formats:
        try:
            parsed = datetime.strptime(str_val, fmt)
            if fmt == "%m/%d %H:%M":
                parsed = parsed.replace(year=now.year)
            return parsed.replace(tzinfo=tz)
        except Exception:
            continue

    log.warning(f"Could not parse speech time string: '{str_val}'")
    return None


class ScheduledSpeechService:
    """
    一回限りの日時指定発声（予約発声）サービス
    - 過去の日時なら即時発声
    - 未来の日時なら指定時刻まで安全に待機・発声
    - scheduled_speeches.json に永続化し、コンテナ再起動時も確実に復旧・発声
    """

    def __init__(self):
        self.tasks: List[Dict[str, Any]] = []
        self._bg_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.tz = ZoneInfo(settings.tz or "Asia/Tokyo")
        self.load()

    def load(self):
        """永続化ファイルから予約タスクをロード"""
        try:
            if SCHEDULED_SPEECHES_FILE.exists():
                data = json.loads(SCHEDULED_SPEECHES_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.tasks = data
                elif isinstance(data, dict):
                    self.tasks = data.get("tasks", [])
                log.info(f"Loaded {len(self.tasks)} scheduled speech tasks from disk")
            else:
                self.tasks = []
        except Exception as e:
            log.error(f"Failed to load scheduled speeches: {e}", exc_info=True)
            self.tasks = []

    def save(self):
        """予約タスクをアトミックに永続化保存"""
        try:
            SCHEDULED_SPEECHES_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "tasks": self.tasks[-200:],  # 直近200件
                "updated_at": datetime.now(self.tz).isoformat()
            }
            tmp_path = SCHEDULED_SPEECHES_FILE.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(SCHEDULED_SPEECHES_FILE)
        except Exception as e:
            log.error(f"Failed to save scheduled speeches: {e}", exc_info=True)

    async def schedule_or_speak(
        self,
        text: str,
        time_spec: Any,
        targets: Optional[Union[str, List[str]]] = None,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        volume_level: Optional[Union[float, int, str]] = None,
        chime: Optional[str] = None,
        client_name: Optional[str] = None,
        client_ip: Optional[str] = None,
        source: Optional[str] = None,
        source_label: Optional[str] = None,
        urgent: bool = False,
    ) -> Dict[str, Any]:
        """
        日時指定オプションを判定し、
        - 過去または現在（または指定なし）なら即時発声
        - 未来なら予約タスクとしてキューイング
        """
        now = datetime.now(self.tz)
        target_dt = parse_schedule_time(time_spec, self.tz)

        # 日時指定がない、またはパース不能なら通常通り即時発声
        if not target_dt:
            log.info(f"[Speech] No valid scheduled time specified ({time_spec}) -> Executing immediately")
            return await speech_service.speak(
                text=text,
                targets=targets,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume_level=volume_level,
                chime=chime,
                client_name=client_name,
                client_ip=client_ip,
                source=source,
                source_label=source_label,
                urgent=urgent
            )

        # 過去または現在（誤差1秒以内含む）なら即時発声
        diff_sec = (target_dt - now).total_seconds()
        if diff_sec <= 1.0:
            log.info(f"[Speech] Specified time ({target_dt.isoformat()}) is in the past ({diff_sec:.1f}s ago) -> Executing immediately")
            res = await speech_service.speak(
                text=text,
                targets=targets,
                voice=voice,
                rate=rate,
                pitch=pitch,
                volume_level=volume_level,
                chime=chime,
                client_name=client_name,
                client_ip=client_ip,
                source=source,
                source_label=source_label,
                urgent=urgent
            )
            res["scheduled"] = False
            res["specified_time"] = target_dt.isoformat()
            return res

        # 未来の日時 -> 予約タスクとして保存
        task_id = f"speech_{uuid.uuid4().hex[:10]}"
        vol_val = None
        if volume_level is not None and str(volume_level).strip() != "":
            try:
                vol_val = float(volume_level)
            except ValueError:
                pass

        task = {
            "id": task_id,
            "text": text,
            "targets": targets if isinstance(targets, list) else ([targets] if targets else ["default"]),
            "voice": voice,
            "rate": rate,
            "pitch": pitch,
            "volume_level": vol_val,
            "chime": chime,
            "urgent": urgent,
            "client_name": client_name or "Webhook",
            "client_ip": client_ip or "127.0.0.1",
            "source": source or "webhook",
            "source_label": source_label or "発声予約 (日時指定)",
            "scheduled_at": target_dt.isoformat(),
            "created_at": now.isoformat(),
            "delay_seconds": round(diff_sec, 1),
            "status": "pending"
        }

        async with self._lock:
            self.tasks.append(task)
            self.save()

        log.info(
            f"[Speech.Scheduled] New speech task scheduled: id={task_id}, text='{text[:30]}...', "
            f"scheduled_at={target_dt.strftime('%Y-%m-%d %H:%M:%S')} (in {diff_sec:.1f}s)"
        )

        return {
            "success": True,
            "status": "scheduled",
            "message": f"発声予約を受け付けました ({target_dt.strftime('%Y-%m-%d %H:%M:%S')} 予定)",
            "task_id": task_id,
            "scheduled_at": target_dt.isoformat(),
            "delay_seconds": round(diff_sec, 1),
            "text": text,
            "targets": task["targets"]
        }

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """現在待機中の予約タスク一覧を取得"""
        now = datetime.now(self.tz)
        pending = []
        for t in self.tasks:
            if t.get("status") == "pending":
                item = {**t}
                try:
                    s_dt = datetime.fromisoformat(t["scheduled_at"])
                    item["remaining_seconds"] = max(0, round((s_dt - now).total_seconds(), 1))
                except Exception:
                    item["remaining_seconds"] = 0
                pending.append(item)
        # 実行予定が近い順にソート
        pending.sort(key=lambda x: x.get("scheduled_at", ""))
        return pending

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """すべてのタスク一覧（待機中および完了履歴）"""
        return sorted(self.tasks, key=lambda x: x.get("scheduled_at", ""), reverse=True)

    async def cancel_task(self, task_id: str) -> bool:
        """予約タスクをキャンセル"""
        async with self._lock:
            for t in self.tasks:
                if t.get("id") == task_id and t.get("status") == "pending":
                    t["status"] = "cancelled"
                    t["cancelled_at"] = datetime.now(self.tz).isoformat()
                    self.save()
                    log.info(f"[Speech.Scheduled] Cancelled task: {task_id}")
                    return True
        return False

    async def _execute_due_task(self, task: Dict[str, Any]):
        """期日が到来した予約タスクを発声実行"""
        task_id = task.get("id")
        log.info(f"[Speech.Scheduled] Triggering scheduled speech: id={task_id}, text='{task.get('text', '')[:30]}'")
        task["status"] = "running"
        task["started_at"] = datetime.now(self.tz).isoformat()
        
        try:
            res = await speech_service.speak(
                text=task.get("text", ""),
                targets=task.get("targets"),
                voice=task.get("voice"),
                rate=task.get("rate"),
                pitch=task.get("pitch"),
                volume_level=task.get("volume_level"),
                chime=task.get("chime"),
                client_name=task.get("client_name"),
                client_ip=task.get("client_ip"),
                source=task.get("source") or "scheduled_speech",
                source_label=task.get("source_label") or "発声予約 (日時指定)",
                urgent=task.get("urgent", False)
            )
            task["status"] = "completed"
            task["completed_at"] = datetime.now(self.tz).isoformat()
            task["result"] = res
            log.info(f"[Speech.Scheduled] Successfully executed task: {task_id}")
        except Exception as e:
            task["status"] = "failed"
            task["failed_at"] = datetime.now(self.tz).isoformat()
            task["error"] = str(e)
            log.error(f"[Speech.Scheduled] Execution failed for {task_id}: {e}", exc_info=True)
        finally:
            self.save()

    async def start(self):
        """定期監視ループを開始（毎秒〜2秒チェック）"""
        if self._bg_task and not self._bg_task.done():
            return
        self._bg_task = asyncio.create_task(self._worker_loop())
        log.info("Scheduled speech worker loop started")

    async def _worker_loop(self):
        """予約発声の期日判定・実行ワーカー"""
        while True:
            try:
                now = datetime.now(self.tz)
                due_tasks: List[Dict[str, Any]] = []

                async with self._lock:
                    for t in self.tasks:
                        if t.get("status") == "pending":
                            s_at = t.get("scheduled_at")
                            if not s_at:
                                continue
                            try:
                                dt = datetime.fromisoformat(s_at)
                                if dt <= now:
                                    # 発声期日到来
                                    t["status"] = "running"
                                    due_tasks.append(t)
                            except Exception as e:
                                log.warning(f"Invalid scheduled_at '{s_at}' in task {t.get('id')}: {e}")

                    if due_tasks:
                        self.save()

                # ロックを解放してから各タスクを並行または順次実行
                for t in due_tasks:
                    asyncio.create_task(self._execute_due_task(t))

                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"[ScheduledSpeech] Worker loop error: {e}", exc_info=True)
                await asyncio.sleep(3)


scheduled_speech_service = ScheduledSpeechService()
