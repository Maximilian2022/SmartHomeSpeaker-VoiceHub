import os
import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.config import DATA_DIR, settings

SETTINGS_FILE = DATA_DIR / "settings.json"
SETTINGS_BAK_FILE = DATA_DIR / "settings.json.bak"
SETTINGS_TMP_FILE = DATA_DIR / "settings.json.tmp"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "defaultDeviceId": settings.effective_default_ip,
    "favoriteDevices": [],
    "webhookToken": None,
    "adminPassword": None,
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
    "deviceLabels": {},
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
    "rainAlarm": {
        "enabled": False,
        "provider": "auto",
        "yahooAppId": "",
        "latitude": 35.6812,
        "longitude": 139.7671,
        "locationName": "東京都千代田区",
        "checkIntervalMinutes": 5,
        "thresholdMm": 0.5,
        "heavyThresholdMm": 10.0,
        "notifyApproaching": True,
        "notifyHeavy": True,
        "notifyClearing": True,
        "targetScope": "all",
        "targetDevices": ["ALL"],
        "cooldownMinutes": 30,
        "chime": "notice_info"
    },
    "mqtt": {
        "enabled": False,
        "broker": "localhost",
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
    },
    "tts_providers": {
        "urgentFastest": True,
        "azure": {
            "enabled": False,
            "apiKey": "",
            "region": "japaneast",
            "timeoutSeconds": 5.0,
            "defaultVoiceId": "azure:ja-JP-NanamiNeural"
        },
        "gcp": {
            "enabled": False,
            "apiKey": "",
            "timeoutSeconds": 5.0,
            "defaultVoiceId": "gcp:ja-JP-Neural2-B"
        },
        "voicevox": {
            "enabled": False,
            "baseUrl": "http://127.0.0.1:50021",
            "timeoutSeconds": 5.0,
            "defaultVoiceId": "voicevox:2",
            "preload": True
        },
        "sharevox": {
            "enabled": False,
            "baseUrl": "http://127.0.0.1:50025",
            "timeoutSeconds": 5.0,
            "defaultVoiceId": "sharevox:21",
            "preload": True
        },
        "coeiroink": {
            "enabled": False,
            "baseUrl": "http://127.0.0.1:50031",
            "timeoutSeconds": 5.0,
            "defaultVoiceId": "coeiroink:140",
            "preload": True
        },
        "voice_engines": [
            {
                "id": "voicevox_default",
                "name": "VOICEVOX (ローカル)",
                "type": "voicevox",
                "enabled": False,
                "baseUrl": "http://127.0.0.1:50021",
                "timeoutSeconds": 5.0,
                "defaultVoiceId": "voicevox:2",
                "preload": True
            },
            {
                "id": "sharevox_default",
                "name": "SHAREVOX (ローカル)",
                "type": "sharevox",
                "enabled": False,
                "baseUrl": "http://127.0.0.1:50025",
                "timeoutSeconds": 5.0,
                "defaultVoiceId": "sharevox:21",
                "preload": True
            },
            {
                "id": "coeiroink_default",
                "name": "COEIROINK (ローカル)",
                "type": "coeiroink",
                "enabled": False,
                "baseUrl": "http://127.0.0.1:50031",
                "timeoutSeconds": 5.0,
                "defaultVoiceId": "coeiroink:140",
                "preload": True
            }
        ]
    },
    "systemUpdate": {
        "autoUpdate": False,
        "autoUpdateTime": "04:00",
        "watchtowerUrl": settings.watchtower_url,
        "watchtowerToken": settings.watchtower_token,
        "checkIntervalHours": 24
    },
    "pcSpeakers": {
        "outputs": {},
        "primaryOutput": {}
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

    def _normalize_tts_providers(self, data: Dict[str, Any]):
        """TTS プロバイダー設定の初期化・マージ補正および動的音声エンジン群のマイグレーション"""
        if "tts_providers" not in data or not isinstance(data["tts_providers"], dict):
            data["tts_providers"] = dict(DEFAULT_SETTINGS["tts_providers"])
            return

        defaults = DEFAULT_SETTINGS["tts_providers"]
        tp = data["tts_providers"]
        if "urgentFastest" not in tp:
            tp["urgentFastest"] = defaults["urgentFastest"]

        for key in ["azure", "gcp", "voicevox", "sharevox", "coeiroink"]:
            if key not in tp or not isinstance(tp[key], dict):
                tp[key] = dict(defaults[key])
            else:
                for sub_k, sub_v in defaults[key].items():
                    if sub_k not in tp[key]:
                        tp[key][sub_k] = sub_v

        # 既知の無効デフォルトボイスIDの自動補正
        if tp.get("sharevox", {}).get("defaultVoiceId") in ["sharevox:0", "0"]:
            tp["sharevox"]["defaultVoiceId"] = "sharevox:21"
        if tp.get("coeiroink", {}).get("defaultVoiceId") in ["coeiroink:0", "0"]:
            tp["coeiroink"]["defaultVoiceId"] = "coeiroink:140"

        # 動的ローカル音声エンジン群 (voice_engines) のマイグレーション & 同期
        v_engines = tp.get("voice_engines")
        if not v_engines or not isinstance(v_engines, list) or len(v_engines) == 0:
            # 既存の voicevox / sharevox / coeiroink 設定から配列を作成
            tp["voice_engines"] = [
                {
                    "id": "voicevox_default",
                    "name": "VOICEVOX (ローカル)",
                    "type": "voicevox",
                    "enabled": bool(tp.get("voicevox", {}).get("enabled", False)),
                    "baseUrl": tp.get("voicevox", {}).get("baseUrl") or "http://127.0.0.1:50021",
                    "timeoutSeconds": float(tp.get("voicevox", {}).get("timeoutSeconds") or 5.0),
                    "defaultVoiceId": tp.get("voicevox", {}).get("defaultVoiceId") or "voicevox:2",
                    "preload": bool(tp.get("voicevox", {}).get("preload", True))
                },
                {
                    "id": "sharevox_default",
                    "name": "SHAREVOX (ローカル)",
                    "type": "sharevox",
                    "enabled": bool(tp.get("sharevox", {}).get("enabled", False)),
                    "baseUrl": tp.get("sharevox", {}).get("baseUrl") or "http://127.0.0.1:50025",
                    "timeoutSeconds": float(tp.get("sharevox", {}).get("timeoutSeconds") or 5.0),
                    "defaultVoiceId": tp.get("sharevox", {}).get("defaultVoiceId") or "sharevox:21",
                    "preload": bool(tp.get("sharevox", {}).get("preload", True))
                },
                {
                    "id": "coeiroink_default",
                    "name": "COEIROINK (ローカル)",
                    "type": "coeiroink",
                    "enabled": bool(tp.get("coeiroink", {}).get("enabled", False)),
                    "baseUrl": tp.get("coeiroink", {}).get("baseUrl") or "http://127.0.0.1:50031",
                    "timeoutSeconds": float(tp.get("coeiroink", {}).get("timeoutSeconds") or 5.0),
                    "defaultVoiceId": tp.get("coeiroink", {}).get("defaultVoiceId") or "coeiroink:140",
                    "preload": bool(tp.get("coeiroink", {}).get("preload", True))
                }
            ]
        else:
            # voice_engines 配列が存在する場合、各要素のバリデーションと補完
            sanitized_engines = []
            for idx, eng in enumerate(v_engines):
                if not isinstance(eng, dict):
                    continue
                e_type = str(eng.get("type") or "voicevox").lower().strip()
                e_id = str(eng.get("id") or f"engine_{idx}").strip()
                e_name = str(eng.get("name") or (e_type.upper() if e_type in ["voicevox", "sharevox", "coeiroink"] else "カスタム音声エンジン")).strip()
                default_voice = eng.get("defaultVoiceId")
                if not default_voice:
                    if e_type == "sharevox": default_voice = "sharevox:21"
                    elif e_type == "coeiroink": default_voice = "coeiroink:140"
                    else: default_voice = "voicevox:2"

                sanitized_engines.append({
                    "id": e_id,
                    "name": e_name,
                    "type": e_type,
                    "enabled": bool(eng.get("enabled", False)),
                    "baseUrl": str(eng.get("baseUrl") or "http://127.0.0.1:50021").rstrip("/"),
                    "timeoutSeconds": float(eng.get("timeoutSeconds") or 5.0),
                    "defaultVoiceId": default_voice,
                    "preload": bool(eng.get("preload", True))
                })
            tp["voice_engines"] = sanitized_engines

            # 既存コードとの後方互換性のため、代表エンジンを tp["voicevox"] 等に逆同期
            for t in ["voicevox", "sharevox", "coeiroink"]:
                found = next((e for e in sanitized_engines if e["type"] == t), None)
                if found:
                    tp[t] = {
                        "enabled": found["enabled"],
                        "baseUrl": found["baseUrl"],
                        "timeoutSeconds": found["timeoutSeconds"],
                        "defaultVoiceId": found["defaultVoiceId"],
                        "preload": found["preload"]
                    }

    def _load(self) -> Dict[str, Any]:
        self._load_failed = False
        # 1. 通常のファイル読み込み
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    merged = deepcopy(DEFAULT_SETTINGS)
                    for k, v in data.items():
                        if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                            merged[k] = {**merged[k], **v}
                        else:
                            merged[k] = v
                    self._normalize_mqtt(merged)
                    self._normalize_ai(merged)
                    self._normalize_tts_providers(merged)
                    return merged
            except Exception as e:
                print(f"[SettingsManager] settings.json ロード失敗 (破損の可能性): {e}")

        # 2. バックアップファイルからの自動復元試行
        if SETTINGS_BAK_FILE.exists():
            try:
                print("[SettingsManager] バックアップファイル (settings.json.bak) からの復元を試みます...")
                with open(SETTINGS_BAK_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    merged = deepcopy(DEFAULT_SETTINGS)
                    for k, v in data.items():
                        if isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                            merged[k] = {**merged[k], **v}
                        else:
                            merged[k] = v
                    self._normalize_mqtt(merged)
                    self._normalize_ai(merged)
                    self._normalize_tts_providers(merged)
                    print("[SettingsManager] バックアップからの復元に成功しました")
                    return merged
            except Exception as be:
                print(f"[SettingsManager] バックアップからの復元も失敗: {be}")

        # 3. 復元不能な場合
        if SETTINGS_FILE.exists():
            print("[SettingsManager] 警告: 既存の settings.json が破損しており復元できませんでした。上書き保存を防止します。")
            self._load_failed = True
        else:
            # 初回起動時はデフォルト保存
            init_data = deepcopy(DEFAULT_SETTINGS)
            self._save(init_data)

        return deepcopy(DEFAULT_SETTINGS)

    def _save(self, data: Dict[str, Any]):
        if getattr(self, "_load_failed", False):
            print("[SettingsManager] 警告: ロード失敗状態のため既存ファイルの上書き保存を安全にスキップしました")
            return
        try:
            # 1. 一時ファイル (.tmp) へアトミック書き込み
            with open(SETTINGS_TMP_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # 2. 既存の正常ファイルをバックアップ (.bak)
            if SETTINGS_FILE.exists():
                try:
                    shutil.copy2(SETTINGS_FILE, SETTINGS_BAK_FILE)
                except Exception:
                    pass

            # 3. アトミック置換
            os.replace(SETTINGS_TMP_FILE, SETTINGS_FILE)
        except Exception as e:
            print(f"[SettingsManager] Save error: {e}")
            if SETTINGS_TMP_FILE.exists():
                try:
                    SETTINGS_TMP_FILE.unlink()
                except Exception:
                    pass

    def get(self) -> Dict[str, Any]:
        return self.settings

    def update(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        OVERWRITE_COLLECTIONS = {"deviceGroups", "ipAliases", "deviceLabels", "dndScheduleRules", "favoriteDevices"}
        for k, v in new_data.items():
            if k in OVERWRITE_COLLECTIONS:
                self.settings[k] = v
            elif isinstance(v, dict) and k in self.settings and isinstance(self.settings[k], dict):
                self.settings[k] = {**self.settings[k], **v}
            else:
                self.settings[k] = v
        self._normalize_mqtt(self.settings)
        self._normalize_ai(self.settings)
        self._normalize_tts_providers(self.settings)
        self._save(self.settings)
        return self.settings

    def get_default_device_id(self) -> str:
        return self.settings.get("defaultDeviceId") or settings.effective_default_ip

    def set_default_device_id(self, dev_id: str) -> str:
        self.settings["defaultDeviceId"] = dev_id
        self._save(self.settings)
        return dev_id

    def get_favorite_devices(self) -> List[str]:
        raw = self.settings.get("favoriteDevices", [])
        if isinstance(raw, list):
            return [str(x) for x in raw if x]
        return []

    def set_favorite_devices(self, favorites: List[str]) -> List[str]:
        unique_favs: List[str] = []
        for f in favorites:
            s = str(f).strip()
            if s and s not in unique_favs:
                unique_favs.append(s)
        self.settings["favoriteDevices"] = unique_favs
        self._save(self.settings)
        return unique_favs

    def toggle_favorite_device(self, dev_id: str) -> bool:
        target = str(dev_id).strip()
        if not target:
            return False
        favs = self.get_favorite_devices()
        if target in favs:
            favs.remove(target)
            is_fav = False
        else:
            favs.append(target)
            is_fav = True
        self.set_favorite_devices(favs)
        return is_fav

    def get_disabled_devices(self) -> List[str]:
        raw = self.settings.get("disabledDevices", [])
        if isinstance(raw, list):
            return [str(x) for x in raw if x]
        return []

    def set_disabled_devices(self, disabled_list: List[str]) -> List[str]:
        unique_list: List[str] = []
        for d in disabled_list:
            s = str(d).strip()
            if s and s not in unique_list:
                unique_list.append(s)
        self.settings["disabledDevices"] = unique_list
        self._save(self.settings)
        return unique_list

    def toggle_disabled_device(self, dev_id: str) -> bool:
        target = str(dev_id).strip()
        if not target:
            return False
        dis = self.get_disabled_devices()
        if target in dis:
            dis.remove(target)
            is_disabled = False
        else:
            dis.append(target)
            is_disabled = True
        self.set_disabled_devices(dis)
        return is_disabled

    def is_device_disabled(self, dev_id: Optional[str], ip: Optional[str] = None, name: Optional[str] = None) -> bool:
        dis = set(self.get_disabled_devices())
        if not dis:
            return False
        for k in (dev_id, ip, name):
            if k and str(k).strip() in dis:
                return True
        return False

    def get_admin_password(self) -> str:
        """設定ファイル (settings.json) を優先し、未設定 (None) の場合のみ .my.env の値を返す"""
        if "adminPassword" in self.settings:
            gui_val = self.settings.get("adminPassword")
            if gui_val is not None:
                return str(gui_val).strip()
        return settings.effective_admin_password

    def set_admin_password(self, password: str) -> str:
        clean = str(password or "").strip()
        self.settings["adminPassword"] = clean
        self._save(self.settings)
        return clean

    def get_webhook_token(self) -> str:
        """設定ファイル (settings.json) を優先し、未設定 (None) の場合のみ .my.env の値を返す"""
        if "webhookToken" in self.settings:
            val = self.settings.get("webhookToken")
            if val is not None:
                return str(val).strip()
        return settings.webhook_token or ""

    def get_pc_speakers_config(self) -> Dict[str, Any]:
        """PCスピーカーの出力デバイス別設定 (enabled / customName / primaryOutput) を取得"""
        conf = self.settings.get("pcSpeakers")
        if not isinstance(conf, dict):
            conf = {"outputs": {}, "primaryOutput": {}}
            self.settings["pcSpeakers"] = conf
        if not isinstance(conf.get("outputs"), dict):
            conf["outputs"] = {}
        if not isinstance(conf.get("primaryOutput"), dict):
            conf["primaryOutput"] = {}
        return conf

    def update_pc_speaker_output(
        self,
        client_id: str,
        output_key: str,
        enabled: Any = None,
        custom_name: Any = None,
        is_primary: Any = None
    ) -> Dict[str, Any]:
        """特定のPCクライアントの出力デバイスの有効/無効・カスタム名・メイン指定を更新して永続化"""
        conf = self.get_pc_speakers_config()
        comp_key = f"{client_id}@{output_key}"
        out_conf = dict(conf["outputs"].get(comp_key) or {})
        if enabled is not None:
            out_conf["enabled"] = bool(enabled)
        if custom_name is not None:
            out_conf["name"] = str(custom_name).strip()
        conf["outputs"][comp_key] = out_conf

        if is_primary is True:
            conf["primaryOutput"][client_id] = output_key
            # メインに指定された出力は自動的に有効化
            out_conf["enabled"] = True

        self._save(self.settings)
        return conf

    def get_device_labels(self) -> Dict[str, str]:
        """全デバイスのカスタムラベルマッピング (deviceId -> label) を取得"""
        labels = self.settings.get("deviceLabels")
        if not isinstance(labels, dict):
            labels = {}
            self.settings["deviceLabels"] = labels
        return labels

    def get_label_for_device(self, device_id: Optional[str] = None, alt_id: Optional[str] = None) -> str:
        """指定されたデバイスIDまたはIPに設定されているラベルを取得"""
        labels = self.get_device_labels()
        if device_id and device_id in labels:
            return labels[device_id]
        if alt_id and alt_id in labels:
            return labels[alt_id]
        return ""

    def set_device_label(
        self,
        device_id: str,
        label: Optional[str] = None,
        alt_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        特定のデバイスに一意なカスタムラベルを設定または解除。
        全体で一意（大文字小文字無視、重複禁止）を保証。
        成功時は (True, 保存されたラベル文字列)、失敗時は (False, エラーメッセージ) を返却。
        """
        dev_key = str(device_id or "").strip()
        alt_key = str(alt_id or "").strip() if alt_id else ""
        if not dev_key:
            return False, "デバイスIDが指定されていません"

        labels = self.get_device_labels()
        clean_label = str(label or "").strip()

        # ラベル解除 (空文字または未指定)
        if not clean_label:
            removed = False
            if dev_key in labels:
                del labels[dev_key]
                removed = True
            if alt_key and alt_key in labels:
                del labels[alt_key]
                removed = True
            if removed:
                self._save(self.settings)
            return True, ""

        clean_lower = clean_label.lower()

        # 1. 予約語チェック (システムマクロ・一斉発話キーワードとの衝突防止)
        RESERVED_LABELS = {
            "all", "*", "default",
            "gh:all", "google:all",
            "al:all", "alexa:all",
            "hp:all", "homepod:all",
            "pc:all", "client:all", "win:all", "mac:all",
            "cam:all", "onvif:all", "tapo:all",
            "dlna:all"
        }
        if clean_lower in RESERVED_LABELS:
            return False, f"「{clean_label}」はシステム予約語のためラベルとして使用できません"

        # 2. デバイスグループ名との重複チェック
        groups = self.settings.get("deviceGroups", {})
        if isinstance(groups, dict):
            for grp_name in groups.keys():
                if str(grp_name).strip().lower() == clean_lower:
                    return False, f"「{clean_label}」は既存のグループ名と重複しているため使用できません"

        # 3. 他デバイスとの一意性チェック (重複禁止)
        for k, v in labels.items():
            if k != dev_key and k != alt_key:
                if str(v).strip().lower() == clean_lower:
                    return False, f"ラベル「{clean_label}」は既に他のデバイスで使用されています (重複不可)"

        # 保存
        labels[dev_key] = clean_label
        # alt_key がキーとして存在していた場合は古い方を整理
        if alt_key and alt_key in labels and alt_key != dev_key:
            del labels[alt_key]

        self.settings["deviceLabels"] = labels
        self._save(self.settings)
        return True, clean_label

settings_manager = SettingsManager()
