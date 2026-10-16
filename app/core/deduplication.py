import time
import hashlib
from typing import Dict, Tuple

class Deduplicator:
    def __init__(self):
        # key: hash(sender + ":" + text), value: timestamp
        self._history: Dict[str, float] = {}

    def is_duplicate(self, text: str, sender: str = "unknown", cooldown_seconds: int = 30) -> bool:
        if cooldown_seconds <= 0:
            return False
            
        now = time.time()
        # 古い履歴のクリーンアップ (1時間以上前)
        self._history = {k: v for k, v in self._history.items() if now - v < 3600}
        
        key = hashlib.md5(f"{sender}:{text.strip()}".encode()).hexdigest()
        last_time = self._history.get(key)
        
        if last_time and (now - last_time < cooldown_seconds):
            return True
            
        self._history[key] = now
        return False

deduplicator = Deduplicator()
