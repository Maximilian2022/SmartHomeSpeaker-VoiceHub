import json
from pathlib import Path
from typing import Any, Dict
from app.config import DATA_DIR, settings

SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "defaultDeviceId": settings.effective_default_ip,
    "webhookToken": settings.webhook_token,
    "calendar": {
        "enabled": False,
        "calendars": [],
        "icalUrl": "",
        "remindEnabled": True,
        "remindMinutesBefore": 10,
        "dailySummaryEnabled": True,
        "dailySummaryTime": "07:30",
        "targetDevices": ["default"],
        "voice": "ja-JP-NanamiNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "volumeLevel": ""
    },
    "dnd": {
        "enabled": True,
        "scheduleEnabled": False,
        "schedules": [
            {
                "id": "dnd_work",
                "name": "平日業務時間",
                "days": ["1", "2", "3", "4", "5"],
                "startTime": "09:00",
                "endTime": "18:00",
                "enabled": True
            },
            {
                "id": "dnd_night",
                "name": "深夜帯",
                "days": ["0", "1", "2", "3", "4", "5", "6"],
                "startTime": "23:00",
                "endTime": "07:00",
                "enabled": False
            }
        ],
        "calendarEnabled": True,
        "calendarMode": "keywords",
        "calendarKeywords": "MTG, 会議, Zoom, Teams, Meet, 打ち合わせ, 商談, 集中",
        "calendarIncludeAllDay": False,
        "manualUntil": None,
        "manualReason": "",
        "targetScope": "all",
        "targetDevices": [],
        "action": "skip",
        "whisperVolume": 10,
        "topMuteDuration": "indefinite",
        "aiSummaryEnabled": True,
        "aiSummaryThreshold": 2,
        "aiSummaryCustomPrompt": ""
    },
    "ai": {
        "enabled": True,
        "provider": "gemini",
        "geminiApiKey": settings.effective_gemini_key,
        "openaiApiKey": settings.openai_api_key,
        "geminiModel": "gemini-2.5-flash",
        "openaiModel": "gpt-4o-mini",
        "summarizeDndQueue": True,
        "summaryThreshold": 2,
        "summarizeDailyCalendar": True,
        "dailyCalendarPrompt": "",
        "customPrompt": ""
    },
    "chime": "dingdong",
    "deduplication": {
        "enabled": True,
        "cooldownSeconds": 30
    },
    "deviceGroups": {
        "1F": ["リビング", "キッチン", "和室", "トイレ1F"],
        "2F": ["寝室", "書斎", "部屋", "トイレ2F"],
        "LDK": ["リビング", "キッチン"]
    },
    "autoVolume": {
        "enabled": True,
        "rules": [
            {"id": "day", "name": "日中 (07:00〜21:00)", "startTime": "07:00", "endTime": "21:00", "volume": 50},
            {"id": "evening", "name": "夜間 (21:00〜23:00)", "startTime": "21:00", "endTime": "23:00", "volume": 25},
            {"id": "night", "name": "深夜 (23:00〜07:00)", "startTime": "23:00", "endTime": "07:00", "volume": 10}
        ]
    },
    "ipAliases": {},
    "onvif": {
        "enabled": True,
        "defaultUsername": "admin",
        "defaultPassword": "",
        "registeredDevices": []
    },
    "syncOffsets": {
        "alexaDelayMs": 0,
        "homepodDelayMs": 0,
        "googleDelayMs": 0,
        "dynamicAutoAdjust": True
    }
}

class SettingsManager:
    def __init__(self):
        self.settings = self._load()

    def _load(self) -> Dict[str, Any]:
        if not SETTINGS_FILE.exists():
            self._save(DEFAULT_SETTINGS)
            return dict(DEFAULT_SETTINGS)
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = dict(DEFAULT_SETTINGS)
                for k, v in data.items():
                    if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                        merged[k] = {**merged[k], **v}
                    else:
                        merged[k] = v
                return merged
        except Exception as e:
            print(f"[SettingsManager] Load error: {e}")
            return dict(DEFAULT_SETTINGS)

    def _save(self, data: Dict[str, Any]):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[SettingsManager] Save error: {e}")

    def get(self) -> Dict[str, Any]:
        return self.settings

    def update(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in new_data.items():
            if isinstance(v, dict) and k in self.settings and isinstance(self.settings[k], dict):
                self.settings[k] = {**self.settings[k], **v}
            else:
                self.settings[k] = v
        self._save(self.settings)
        return self.settings

    def get_default_device_id(self) -> str:
        return self.settings.get("defaultDeviceId") or settings.effective_default_ip

    def set_default_device_id(self, dev_id: str) -> str:
        self.settings["defaultDeviceId"] = dev_id
        self._save(self.settings)
        return dev_id

settings_manager = SettingsManager()
