import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.config import DATA_DIR
from app.core.logger import get_logger

log = get_logger("History")
HISTORY_FILE = DATA_DIR / "history.json"
MAX_HISTORY_ENTRIES = 100

class HistoryManager:
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.load_history()

    def load_history(self):
        try:
            if HISTORY_FILE.exists():
                text = HISTORY_FILE.read_text(encoding="utf-8")
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    self.history = parsed[:MAX_HISTORY_ENTRIES]
                    log.info(f"Loaded {len(self.history)} history entries from {HISTORY_FILE}")
        except Exception as e:
            log.warning(f"Failed to load history from {HISTORY_FILE}: {e}")
            self.history = []

    def save_history(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            temp_file = HISTORY_FILE.with_suffix(".tmp")
            temp_file.write_text(json.dumps(self.history, ensure_ascii=False), encoding="utf-8")
            temp_file.replace(HISTORY_FILE)
        except Exception as e:
            log.error(f"Failed to save history to {HISTORY_FILE}: {e}")

    def derive_source_label(self, source: str) -> str:
        mapping = {
            "web_ui": "Web UI (即時発言)",
            "quick_test": "Web UI (テスト)",
            "schedule": "定期スケジュール",
            "calendar": "カレンダー連携",
            "tunnel_webhook": "Cloudflare Tunnel (外部)",
            "dnd_queue": "DND保留再生",
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

        self.save_history()
        log.info(f"Recorded history entry: '{record['text'][:30]}' -> {record['targets']} [{record['status']}]")
        return record

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.history[:limit]

    def clear(self):
        self.history = []
        self.save_history()
        log.info("History cleared.")

history_manager = HistoryManager()
