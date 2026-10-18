import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from app.config import DATA_DIR
from app.core.logger import logger

USAGE_FILE = DATA_DIR / "tts_usage.json"

# 無料枠の上限定数（月間文字数）
FREE_TIER_LIMITS = {
    "gcp_neural": 1_000_000,      # Neural2, Wavenet, Journey (100万文字/月)
    "gcp_standard": 4_000_000,    # Standard (400万文字/月)
    "azure_neural": 500_000,      # Azure Cognitive Speech F0 Neural (50万文字/月)
}

class TtsUsageTracker:
    """GCP / Azure の月次消費文字数を追跡・記録するマネージャー"""

    def __init__(self):
        self.file_path = USAGE_FILE
        self.data = self._load()

    def _get_current_month(self) -> str:
        return datetime.now().strftime("%Y-%m")

    def _load(self) -> Dict[str, Any]:
        current_month = self._get_current_month()
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 月跨ぎチェック
                if data.get("current_month") != current_month:
                    old_month = data.get("current_month", "unknown")
                    logger.info(f"[TtsUsageTracker] 月初リセット実行: {old_month} -> {current_month}")
                    if "history" not in data:
                        data["history"] = {}
                    data["history"][old_month] = {
                        "gcp_neural_characters": data.get("gcp_neural_characters", 0),
                        "gcp_standard_characters": data.get("gcp_standard_characters", 0),
                        "azure_neural_characters": data.get("azure_neural_characters", 0),
                    }
                    data["current_month"] = current_month
                    data["gcp_neural_characters"] = 0
                    data["gcp_standard_characters"] = 0
                    data["azure_neural_characters"] = 0
                    self._save(data)
                return data
            except Exception as e:
                logger.error(f"[TtsUsageTracker] 使用量ファイル読込エラー: {e}")

        # 初期データ構造
        initial_data = {
            "current_month": current_month,
            "gcp_neural_characters": 0,
            "gcp_standard_characters": 0,
            "azure_neural_characters": 0,
            "history": {}
        }
        self._save(initial_data)
        return initial_data

    def _save(self, data: Dict[str, Any]):
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.file_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            temp_path.replace(self.file_path)
        except Exception as e:
            logger.error(f"[TtsUsageTracker] 使用量ファイル保存エラー: {e}")

    def record_usage(self, provider: str, char_count: int, model_type: str = "neural"):
        """文字数の消費を記録"""
        if char_count <= 0:
            return

        current_month = self._get_current_month()
        if self.data.get("current_month") != current_month:
            self.data = self._load()

        key = f"{provider}_{model_type}_characters"
        if key in self.data:
            self.data[key] += char_count
        else:
            self.data[key] = char_count

        self._save(self.data)
        logger.info(f"[TtsUsageTracker] {provider} ({model_type}) 文字数消費記録: +{char_count} (当月累計: {self.data.get(key)})")

    def get_stats(self) -> Dict[str, Any]:
        """WebUI 表示用の使用状況統計を取得"""
        current_month = self._get_current_month()
        if self.data.get("current_month") != current_month:
            self.data = self._load()

        gcp_neural = self.data.get("gcp_neural_characters", 0)
        gcp_standard = self.data.get("gcp_standard_characters", 0)
        azure_neural = self.data.get("azure_neural_characters", 0)

        gcp_neural_limit = FREE_TIER_LIMITS["gcp_neural"]
        gcp_standard_limit = FREE_TIER_LIMITS["gcp_standard"]
        azure_neural_limit = FREE_TIER_LIMITS["azure_neural"]

        return {
            "current_month": current_month,
            "gcp": {
                "neural": {
                    "used": gcp_neural,
                    "limit": gcp_neural_limit,
                    "percentage": round(min(100.0, (gcp_neural / gcp_neural_limit) * 100), 2)
                },
                "standard": {
                    "used": gcp_standard,
                    "limit": gcp_standard_limit,
                    "percentage": round(min(100.0, (gcp_standard / gcp_standard_limit) * 100), 2)
                }
            },
            "azure": {
                "neural": {
                    "used": azure_neural,
                    "limit": azure_neural_limit,
                    "percentage": round(min(100.0, (azure_neural / azure_neural_limit) * 100), 2)
                }
            }
        }

tts_usage_tracker = TtsUsageTracker()
