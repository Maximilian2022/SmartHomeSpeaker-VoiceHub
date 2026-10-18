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
    },
    "disaster": {
        "enabled": True,
        "targetScope": "all",
        "targetDevices": ["ALL"],
        "area": {
            "prefCode": "130000",
            "prefName": "東京都",
            "cityCode": "1310100",
            "cityName": "千代田区"
        },
        "earthquake": {
            "enabled": True,
            "eewEnabled": True,
            "eewUrgent": True,
            "eewVolume": 80,
            "reportEnabled": True,
            "minScale": 30,
            "reportUrgent": False,
            "targetScope": "local"
        },
        "weatherWarning": {
            "enabled": True,
            "level": "warning",
            "notifyClear": True,
            "urgent": False,
            "checkIntervalMinutes": 5
        },
        "dailyWeather": {
            "enabled": True,
            "includeAdvice": True
        }
    },
    "mqtt": {
        "enabled": False,
        "broker": "192.168.11.1",
        "port": 1883,
        "username": "",
        "password": "",
        "clientId": "voice-hub",
        "keepalive": 60,
        "baseTopic": "voicehub",
        "defaultTarget": "",
        "publishEvents": True,
        "tls": False,
        "haDiscoveryEnabled": True,
        "haDiscoveryPrefix": "homeassistant",
        "brokers": []
    }
}

class SettingsManager:
    def __init__(self):
        self.settings = self._load()

    def _normalize_mqtt(self, data: Dict[str, Any]):
        """単一ブローカー設定とマルチブローカー (brokers 配列) の相互自動同期・マイグレーション"""
        if "mqtt" not in data or not isinstance(data["mqtt"], dict):
            return

        m = data["mqtt"]
        brokers = m.get("brokers")
        if not brokers or not isinstance(brokers, list) or len(brokers) == 0:
            # 既存の単一ブローカー設定を brokers[0] に変換
            single_broker = (m.get("broker") or "").strip()
            if single_broker:
                m["brokers"] = [{
                    "id": "default",
                    "name": "メインブローカー",
                    "enabled": bool(m.get("enabled", True)),
                    "broker": single_broker,
                    "port": int(m.get("port") or 1883),
                    "username": m.get("username") or "",
                    "password": m.get("password") or "",
                    "clientId": m.get("clientId") or "voice-hub",
                    "keepalive": int(m.get("keepalive") or 60),
                    "baseTopic": m.get("baseTopic") or "voicehub",
                    "defaultTarget": m.get("defaultTarget") or "",
                    "publishEvents": bool(m.get("publishEvents", True)),
                    "tls": bool(m.get("tls", False)),
                    "haDiscoveryEnabled": bool(m.get("haDiscoveryEnabled", True)),
                    "haDiscoveryPrefix": m.get("haDiscoveryPrefix") or "homeassistant"
                }]
            else:
                m["brokers"] = []
        else:
            # brokers 配列が存在する場合、直下フィールドを brokers[0] と同期して下位互換を維持
            first = brokers[0]
            m["broker"] = first.get("broker", "")
            m["port"] = first.get("port", 1883)
            m["username"] = first.get("username", "")
            m["password"] = first.get("password", "")
            m["clientId"] = first.get("clientId", "voice-hub")
            m["baseTopic"] = first.get("baseTopic", "voicehub")
            m["defaultTarget"] = first.get("defaultTarget", "")
            m["publishEvents"] = first.get("publishEvents", True)
            m["tls"] = first.get("tls", False)
            m["haDiscoveryEnabled"] = first.get("haDiscoveryEnabled", True)
            m["haDiscoveryPrefix"] = first.get("haDiscoveryPrefix", "homeassistant")
            master_enabled = bool(m.get("enabled", True))
            has_active_broker = any(bool(b.get("enabled", False)) for b in brokers)
            m["enabled"] = master_enabled and has_active_broker

    def _normalize_ai(self, data: Dict[str, Any]):
        """AI 設定内の廃止済みモデル名（Gemini 1.5 / 2.0等）の自動修復"""
        if "ai" not in data or not isinstance(data["ai"], dict):
            return
        ai_conf = data["ai"]
        model = str(ai_conf.get("geminiModel") or "").strip()
        deprecated_patterns = ["1.5", "1.0", "2.0"]
        if not model or any(p in model for p in deprecated_patterns):
            ai_conf["geminiModel"] = "gemini-2.5-flash"


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
                self._normalize_mqtt(merged)
                self._normalize_ai(merged)
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
        self._normalize_mqtt(self.settings)
        self._normalize_ai(self.settings)
        self._save(self.settings)
        return self.settings

    def get_default_device_id(self) -> str:
        return self.settings.get("defaultDeviceId") or settings.effective_default_ip

    def set_default_device_id(self, dev_id: str) -> str:
        self.settings["defaultDeviceId"] = dev_id
        self._save(self.settings)
        return dev_id

settings_manager = SettingsManager()
