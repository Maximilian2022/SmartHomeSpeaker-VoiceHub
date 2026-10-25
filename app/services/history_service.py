import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.config import DATA_DIR
from app.core.logger import get_logger
from app.core.log_rotator import get_speak_log_rotator

log = get_logger("History")
HISTORY_FILE = DATA_DIR / "history.json"
MAX_HISTORY_ENTRIES = 100

class HistoryManager:
    def __init__(self):
        self.rotator = get_speak_log_rotator()
        self.history: List[Dict[str, Any]] = []
        self.load_history()

    def load_history(self):
        try:
            # 1. /logs/speak.log (および speak-archive.log) から最新100件を読み込み
            entries = self.rotator.read_latest_entries(MAX_HISTORY_ENTRIES)
            if entries:
                self.history = entries
                log.info(f"Loaded {len(self.history)} history entries from speak.log")
                return

            # 2. speak.log が空で旧 history.json が存在する場合、speak.log へ初回自動移行
            if HISTORY_FILE.exists():
                text = HISTORY_FILE.read_text(encoding="utf-8")
                parsed = json.loads(text)
                if isinstance(parsed, list) and parsed:
                    # 古い順に speak.log へ追記して移行
                    for item in reversed(parsed[:MAX_HISTORY_ENTRIES]):
                        self.rotator.write_entry(item)
                    self.history = parsed[:MAX_HISTORY_ENTRIES]
                    log.info(f"Migrated {len(self.history)} history entries from {HISTORY_FILE} to speak.log")
                    return
        except Exception as e:
            log.warning(f"Failed to load history from speak.log or {HISTORY_FILE}: {e}")
            self.history = []

    def save_history(self):
        # 既存の history.json への同期バックアップ (後方互換性)
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            temp_file = HISTORY_FILE.with_suffix(".tmp")
            temp_file.write_text(json.dumps(self.history, ensure_ascii=False), encoding="utf-8")
            temp_file.replace(HISTORY_FILE)
        except Exception as e:
            log.error(f"Failed to save legacy history backup: {e}")


    def derive_source_label(self, source: str) -> str:
        mapping = {
            "web_ui": "Web UI (即時発言)",
            "quick_test": "Web UI (テスト)",
            "schedule": "定期スケジュール",
            "scheduled_speech": "発声予約 (日時指定)",
            "calendar": "カレンダー連携",
            "tunnel_webhook": "Cloudflare Tunnel (外部)",
            "dnd_queue": "DND保留再生",
            "rain_alarm": "雨アラーム",
            "disaster": "防災速報",
            "mcp": "MCP連携",
            "mqtt": "MQTT連携",
            "system": "システム通知",
            "api": "外部 API / Webhook"
        }
        return mapping.get(source, "外部 API / Webhook")

    def add_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        if not entry or not entry.get("text"):
            return {}

        now_ts = int(time.time() * 1000)
        entry_id = f"hist_{now_ts}"
        timestamp = entry.get("timestamp") or datetime.now(timezone.utc).isoformat()

        targets = entry.get("targets") or ["デフォルト"]
        if isinstance(targets, str):
            targets = [targets]

        source = entry.get("source") or "api"
        source_label = entry.get("sourceLabel") or self.derive_source_label(source)

        record = {
            "id": entry_id,
            "timestamp": timestamp,
            "text": str(entry.get("text", "")),
            "source": source,
            "sourceLabel": source_label,
            "clientName": entry.get("clientName") or entry.get("client") or "",
            "clientIp": entry.get("clientIp") or "",
            "wasQueued": bool(entry.get("wasQueued", False)),
            "targets": targets,
            "voice": entry.get("voice") or "ja-JP-NanamiNeural",
            "rate": entry.get("rate") or "+0%",
            "pitch": entry.get("pitch") or "+0Hz",
            "volume": entry.get("volume") or "",
            "volumeLevel": entry.get("volumeLevel"),
            "audioUrl": entry.get("audioUrl") or "",
            "duration": entry.get("duration", 0),
            "status": entry.get("status") or "success",
            "statusMessage": entry.get("statusMessage") or ("送信完了" if entry.get("status") == "success" else "送信失敗"),
            "urgent": bool(entry.get("urgent", False)),
            "results": entry.get("results") or []
        }

        self.history.insert(0, record)
        if len(self.history) > MAX_HISTORY_ENTRIES:
            self.history = self.history[:MAX_HISTORY_ENTRIES]

        # /logs/speak.log へ追記 (JSON Lines)
        self.rotator.write_entry(record)
        self.save_history()
        log.info(f"Recorded history entry: '{record['text'][:30]}' -> {record['targets']} [{record['status']}]")
        return record

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.history[:limit]

    def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """メモリ上の履歴、speak.log、および history.json を同期更新"""
        if not entry_id or not updates:
            return False
        found = False
        for item in self.history:
            if item.get("id") == entry_id:
                item.update(updates)
                found = True
                break
        if found:
            self.rotator.update_entry(entry_id, updates)
            self.save_history()
            log.info(f"Updated history entry {entry_id}: {updates}")
        return found

    def update_entries(self, updates_map: Dict[str, Dict[str, Any]]) -> int:
        """複数件の一括更新"""
        if not updates_map:
            return 0
        updated_count = 0
        for item in self.history:
            eid = item.get("id")
            if eid in updates_map:
                item.update(updates_map[eid])
                updated_count += 1
        if updated_count > 0:
            self.rotator.update_entries(updates_map)
            self.save_history()
            log.info(f"Updated {updated_count} history entries: {list(updates_map.keys())}")
        return updated_count

    def mark_queued_as_released(self, history_ids: List[str], note: str = "DND保留再生完了"):
        """DND保留中エントリを再生完了（送信成功）に更新"""
        if not history_ids:
            return
        updates = {
            hid: {
                "status": "success",
                "wasQueued": True,
                "statusMessage": note
            }
            for hid in history_ids if hid
        }
        self.update_entries(updates)

    def clear(self):
        self.history = []
        self.save_history()
        try:
            self.rotator.clear()
        except Exception as e:
            log.warning(f"Failed to clear speak.log: {e}")
        log.info("History and speak.log cleared.")

history_manager = HistoryManager()
