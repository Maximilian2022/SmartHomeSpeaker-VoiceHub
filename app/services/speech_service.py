import asyncio
import os
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from app.services.settings_service import settings_manager
from app.services.tts_service import tts_service
from app.services.devices_service import device_manager
from app.services.cast_service import cast_service
from app.services.homepod_service import homepod_service
from app.services.dlna_service import dlna_service
from app.services.onvif_service import onvif_service
from app.services.alexa_service import alexa_service
from app.services.dnd_service import dnd_service
from app.services.calendar_service import calendar_service
from app.core.deduplication import deduplicator

HISTORY_LOG: List[Dict[str, Any]] = []
MAX_HISTORY = 100

class SpeechService:
    def __init__(self):
        self.server_base_url = "http://127.0.0.1:8080"

    def get_history(self) -> List[Dict[str, Any]]:
        return HISTORY_LOG

    def record_history(self, item: Dict[str, Any]):
        global HISTORY_LOG
        HISTORY_LOG.insert(0, item)
        if len(HISTORY_LOG) > MAX_HISTORY:
            HISTORY_LOG = HISTORY_LOG[:MAX_HISTORY]

    def _get_effective_volume(self, req_volume: Optional[Union[float, int, str]]) -> Optional[float]:
        if req_volume is not None and str(req_volume).strip() != "":
            try:
                v = float(req_volume)
                return v / 100.0 if v > 1.0 else v
            except ValueError:
                pass

        auto_vol_conf = settings_manager.get().get("autoVolume", {})
        if auto_vol_conf.get("enabled", True):
            now_str = datetime.now().strftime("%H:%M")
            for r in auto_vol_conf.get("rules", []):
                st = r.get("startTime", "00:00")
                et = r.get("endTime", "23:59")
                in_range = (st <= now_str <= et) if st <= et else (now_str >= st or now_str <= et)
                if in_range:
                    return float(r.get("volume", 50)) / 100.0
        return None

    async def speak(
        self,
        text: str,
        targets: Optional[Union[str, List[str]]] = None,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        volume_level: Optional[Union[float, int, str]] = None,
        chime: Optional[str] = None,
        client_name: str = "API",
        urgent: bool = False
    ) -> Dict[str, Any]:
        text = text.strip()
        if not text:
            return {"status": "error", "message": "Text cannot be empty"}

        # 1. 重複排除 (Deduplication)
        dedup_conf = settings_manager.get().get("deduplication", {})
        if not urgent and dedup_conf.get("enabled", True):
            cooldown = dedup_conf.get("cooldownSeconds", 30)
            if deduplicator.is_duplicate(text, client_name, cooldown):
                return {"status": "skipped", "message": "Deduplicated", "deduplicated": True}

        # 2. DND 評価 (おやすみ・会議モード)
        current_meeting = calendar_service.get_current_meeting_title()
        dnd_result = dnd_service.evaluate(active_event_title=current_meeting, urgent=urgent)

        if dnd_result.get("active"):
            action = dnd_result.get("action", "skip")
            if action == "skip":
                return {"status": "skipped", "message": f"DND active ({dnd_result.get('reason')})", "dnd": True}
            elif action == "queue":
                dnd_service.add_to_queue({
                    "text": text,
                    "targets": targets,
                    "voice": voice,
                    "client": client_name
                })
                return {"status": "queued", "message": f"Queued for DND ({dnd_result.get('reason')})", "dnd": True}
            elif action == "whisper":
                volume_level = dnd_result.get("whisperVolume", 10)

        # 3. 宛先スピーカーの展開・解決
        target_list: List[str] = []
        if isinstance(targets, str):
            target_list = [t.strip() for t in targets.split(",") if t.strip()]
        elif isinstance(targets, list):
            target_list = [str(t).strip() for t in targets if str(t).strip()]
        if not target_list:
            target_list = ["default"]

        all_devices = await device_manager.get_devices()
        expanded_devices: List[Dict[str, Any]] = []

        # グループ定義
        groups = settings_manager.get().get("deviceGroups", {})

        for tgt in target_list:
            norm_tgt = tgt.upper()
            if norm_tgt in ("ALL", "*"):
                # 全スピーカー
                expanded_devices.extend(all_devices)
            elif norm_tgt in ("GH:ALL", "GOOGLE:ALL"):
                expanded_devices.extend([d for d in all_devices if d.get("type") == "google"])
            elif norm_tgt in ("AL:ALL", "ALEXA:ALL"):
                expanded_devices.extend([d for d in all_devices if d.get("type") == "alexa"])
            elif norm_tgt in ("HP:ALL", "HOMEPOD:ALL"):
                expanded_devices.extend([d for d in all_devices if d.get("type") == "homepod"])
            elif norm_tgt in ("CAM:ALL", "ONVIF:ALL"):
                expanded_devices.extend([d for d in all_devices if d.get("type") == "onvif"])
            elif norm_tgt in ("DLNA:ALL",):
                expanded_devices.extend([d for d in all_devices if d.get("type") == "dlna"])
            elif tgt in groups:
                # カスタムグループ
                for member_name in groups[tgt]:
                    found = device_manager.find_device(member_name)
                    if found:
                        expanded_devices.append(found)
            elif tgt == "default":
                def_ip = device_manager.get_default_device_ip()
                found = device_manager.find_device(def_ip) if def_ip else None
                if found:
                    expanded_devices.append(found)
                elif all_devices:
                    expanded_devices.append(all_devices[0])
            else:
                found = device_manager.find_device(tgt)
                if found:
                    expanded_devices.append(found)

        # 重複排除 (同一IDまたは同一IP)
        unique_targets: List[Dict[str, Any]] = []
        seen_keys = set()
        for d in expanded_devices:
            key = d.get("id") or d.get("ip")
            if key not in seen_keys:
                seen_keys.add(key)
                unique_targets.append(d)

        # Google Cast ネイティブグループ集約
        has_all = any(t.upper() in ("ALL", "*", "GH:ALL", "GOOGLE:ALL") for t in target_list)
        google_devs = [d for d in unique_targets if d.get("type") == "google"]
        if has_all and len(google_devs) > 1:
            # ネイティブグループが存在すれば個別Google端末を除去してグループ1つに集約
            cast_group = next((d for d in google_devs if d.get("isGroup")), None)
            if cast_group:
                unique_targets = [d for d in unique_targets if d.get("type") != "google" or d == cast_group]

        if not unique_targets:
            return {"status": "error", "message": "No valid target devices found"}

        # 4. 音声合成 (TTS)
        opt_voice = voice or "ja-JP-NanamiNeural"
        opt_rate = rate or "+0%"
        opt_pitch = pitch or "+0Hz"
        opt_chime = chime or settings_manager.get().get("chime", "dingdong")

        speech = await tts_service.synthesize(
            text=text,
            voice=opt_voice,
            rate=opt_rate,
            pitch=opt_pitch,
            chime=opt_chime
        )

        effective_vol = self._get_effective_volume(volume_level)
        audio_url = f"{self.server_base_url}/voice/{speech['filename']}"

        # 5. 各プラットフォームへの並列ディスパッチ
        tasks = []
        for dev in unique_targets:
            dtype = dev.get("type", "google")
            if dtype == "google":
                host = dev.get("host") or dev.get("ip", "").split(":")[0]
                port = dev.get("port", 8009)
                tasks.append(cast_service.play_audio(host, port, audio_url, effective_vol))
            elif dtype == "homepod":
                tasks.append(homepod_service.play_audio(dev.get("ip", ""), audio_url))
            elif dtype == "dlna":
                tasks.append(dlna_service.play_audio(dev, audio_url, effective_vol))
            elif dtype == "onvif":
                tasks.append(onvif_service.play_audio(dev, speech["filepath"], speech["duration"], effective_vol))
            elif dtype == "alexa":
                tasks.append(alexa_service.speak(dev.get("name", ""), text))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 6. 履歴記録
        history_entry = {
            "id": f"hist_{int(time.time()*1000)}",
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "targets": [d.get("name") for d in unique_targets],
            "client": client_name,
            "audioUrl": f"/voice/{speech['filename']}",
            "duration": speech["duration"],
            "status": "success" if any(r is True or isinstance(r, dict) for r in results) else "error"
        }
        self.record_history(history_entry)

        return {
            "status": "success",
            "message": "Playback initiated",
            "targets": [d.get("name") for d in unique_targets],
            "audioUrl": history_entry["audioUrl"],
            "duration": speech["duration"]
        }

speech_service = SpeechService()
