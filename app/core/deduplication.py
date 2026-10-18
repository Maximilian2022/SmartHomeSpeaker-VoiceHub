import time
import hashlib
from typing import Dict

class Deduplicator:
    def __init__(self):
        # key: client_key + ":::" + text, value: timestamp
        self._history: Dict[str, float] = {}

    def is_duplicate(self, text: str, sender: str = "unknown", cooldown_seconds: int = 30) -> bool:
        if cooldown_seconds <= 0:
            return False

        now = time.time()
        key = f"{sender}:::{text.strip()}"
        last_time = self._history.get(key)

        if last_time and (now - last_time < cooldown_seconds):
            return True

        self._history[key] = now
        # キャッシュが1000件を超えた場合のみ、1時間以上前の古いエントリをパージ
        if len(self._history) > 1000:
            expire_threshold = now - 3600
            self._history = {k: v for k, v in self._history.items() if v >= expire_threshold}

        return False

    def clear(self):
        """キャッシュを手動クリア"""
        self._history.clear()

deduplicator = Deduplicator()
