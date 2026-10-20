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
from app.config import settings
from app.services.calendar_service import calendar_service
from app.core.logger import get_logger
from app.services.history_service import history_manager
from app.core.deduplication import deduplicator

log = get_logger("Speech")

class SpeechService:
    def __init__(self):
        pass

    @property
    def server_base_url(self) -> str:
        ip = settings.effective_wireless_ip
        return f"http://{ip}:{settings.server_port}"

    def get_history(self) -> List[Dict[str, Any]]:
        return history_manager.get_history()

    def record_history(self, item: Dict[str, Any]):
        return history_manager.add_entry(item)

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

    async def resolve_targets(
        self,
        target_list: List[str],
        all_devices: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        if all_devices is None:
            all_devices = await device_manager.get_devices()

        expanded_devices: List[Dict[str, Any]] = []
        groups = settings_manager.get().get("deviceGroups", {})

        for tgt in target_list:
            norm_tgt = tgt.upper()
            if norm_tgt in ("ALL", "*"):
                expanded_devices.extend(all_devices)
            elif norm_tgt in ("GH:ALL", "GOOGLE:ALL"):
                expanded_devices.extend([d for d in all_devices if d.get("type") == "google"])
            elif norm_tgt in ("AL:ALL", "ALEXA:ALL"):
                expanded_devices.extend([d for d in all_devices if d.get("type") == "alexa"])
            elif norm_tgt in ("HP:ALL", "HOMEPOD:ALL"):
                expanded_devices.extend([d for d in all_devices if d.get("type") == "homepod"])
            elif norm_tgt in ("CAM:ALL", "ONVIF:ALL", "TAPO:ALL"):
                expanded_devices.extend([d for d in all_devices if d.get("type") in ("onvif", "tapo")])
            elif norm_tgt in ("DLNA:ALL",):
                expanded_devices.extend([d for d in all_devices if d.get("type") == "dlna"])
            elif tgt in groups:
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
            cast_group = next((d for d in google_devs if d.get("isGroup")), None)
            if cast_group:
                unique_targets = [d for d in unique_targets if d.get("type") != "google" or d == cast_group]

        return unique_targets

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
        client_ip: Optional[str] = None,
        source: Optional[str] = None,
        source_label: Optional[str] = None,
        urgent: bool = False,
        was_queued: bool = False,
        speed: Optional[str] = None
    ) -> Dict[str, Any]:
        text = text.strip()
        if not text:
            return {"status": "error", "message": "Text cannot be empty"}

        # 1. 重複排除 (Deduplication)
        dedup_conf = settings_manager.get().get("deduplication", {})
        if not urgent and dedup_conf.get("enabled", True):
            cooldown = dedup_conf.get("cooldownSeconds", 30)
            if deduplicator.is_duplicate(text, client_name, cooldown):
                return {
                    "success": True,
                    "status": "skipped",
                    "message": f"直前の同一通知から {cooldown} 秒以内のためスキップしました",
                    "deduplicated": True,
                    "results": []
                }

        # 2. DND 評価 (おやすみ・会議モード)
        current_meeting = calendar_service.get_current_meeting_title()
        dnd_result = dnd_service.evaluate(active_event_title=current_meeting, urgent=urgent)

        effective_source = source or ("web_ui" if "Mozilla" in client_name or "Web" in client_name else "api")

        if dnd_result.get("active"):
            action = dnd_result.get("action", "skip")
            target_str = ",".join(targets) if isinstance(targets, list) else str(targets or "デフォルト")
            dnd_service.record_history(
                text=text,
                reason=dnd_result.get("reason", "DND"),
                action=action,
                target=target_str
            )

            if action == "skip":
                self.record_history({
                    "text": text,
                    "source": effective_source,
                    "sourceLabel": source_label,
                    "clientName": client_name,
                    "clientIp": client_ip or "",
                    "targets": [targets] if isinstance(targets, str) else (targets or ["デフォルト"]),
                    "voice": voice or "ja-JP-NanamiNeural",
                    "status": "suppressed",
                    "statusMessage": f"おやすみ・会議モード (DND) 発動中のため発話を抑制しました ({dnd_result.get('reason')})",
                    "urgent": urgent,
                    "wasQueued": False,
                    "results": []
                })
                return {
                    "success": True,
                    "status": "skipped",
                    "dndSuppressed": True,
                    "message": f"DND active ({dnd_result.get('reason')})",
                    "dnd": True,
                    "results": []
                }
            elif action == "queue":
                dnd_service.add_to_queue({
                    "text": text,
                    "targets": targets,
                    "voice": voice,
                    "client": client_name,
                    "client_ip": client_ip,
                    "source": effective_source,
                    "source_label": source_label
                })
                self.record_history({
                    "text": text,
                    "source": effective_source,
                    "sourceLabel": source_label,
                    "clientName": client_name,
                    "clientIp": client_ip or "",
                    "targets": [targets] if isinstance(targets, str) else (targets or ["デフォルト"]),
                    "voice": voice or tts_service.get_default_voice_id(),
                    "status": "queued",
                    "statusMessage": f"DND発動中のため保留キューに追加しました ({dnd_result.get('reason')})",
                    "urgent": urgent,
                    "wasQueued": True,
                    "results": []
                })
                return {
                    "success": True,
                    "status": "queued",
                    "dndSuppressed": True,
                    "queued": True,
                    "message": f"Queued for DND ({dnd_result.get('reason')})",
                    "dnd": True,
                    "results": []
                }
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
        unique_targets = await self.resolve_targets(target_list, all_devices)

        # Alexa ネイティブグループ集約 (Amazon Rate Limit 防止 & 全室同期発声)
        has_alexa_all = any(t.upper() in ("ALL", "*", "AL:ALL", "ALEXA:ALL") for t in target_list)
        alexa_devs = [d for d in unique_targets if d.get("type") == "alexa"]
        if (has_alexa_all or len(alexa_devs) >= 4) and len(alexa_devs) > 1:
            # 「全部」「全部の部屋」「全室」「everywhere」等のグループがあれば1つに集約
            alexa_group = next((d for d in alexa_devs if d.get("isGroup")), None)
            if alexa_group:
                log.info(f"[Speech] Alexa native group detected: '{alexa_group.get('name')}' -> Consolidating {len(alexa_devs)} individual Alexa targets into group")
                unique_targets = [d for d in unique_targets if d.get("type") != "alexa" or d == alexa_group]

        if not unique_targets:
            return {"status": "error", "message": "No valid target devices found"}

        # 4. 音声合成 (TTS)
        opt_voice = voice or tts_service.get_default_voice_id()
        opt_rate = rate or speed or "+0%"
        opt_pitch = pitch or "+0Hz"
        opt_chime = chime or settings_manager.get().get("chime", "dingdong")

        # 宛先がすべて Alexa の場合、MP3 音声は一切使用されないため合成処理・チャイム結合をスキップして高速化
        only_alexa = all(d.get("type") == "alexa" for d in unique_targets)
        if only_alexa:
            log.info(f"Target is exclusively Alexa device(s) ({len(unique_targets)} dev). Skipping TTS audio synthesis & chime concatenation.")
            speech = {"filename": "", "filepath": "", "duration": 0.0, "cached": False, "voice": "alexa", "fallback": False}
            audio_url = ""
        else:
            speech = await tts_service.synthesize(
                text=text,
                voice=opt_voice,
                rate=opt_rate,
                pitch=opt_pitch,
                chime=opt_chime,
                urgent=urgent
            )
            audio_url = f"{self.server_base_url}/voice/{speech['filename']}"

        effective_vol = self._get_effective_volume(volume_level)

        # 5. 各プラットフォームへの並列ディスパッチ (syncOffsets 静的ディレイ反映)
        sync_offsets = settings_manager.get().get("syncOffsets", {})
        google_delay = max(0, int(sync_offsets.get("googleDelayMs", 0)))
        homepod_delay = max(0, int(sync_offsets.get("homepodDelayMs", 0)))
        alexa_delay = max(0, int(sync_offsets.get("alexaDelayMs", 0)))

        async def _run_delayed(delay_ms: int, coro):
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000.0)
            return await coro

        tasks = []
        target_names = [f"{d.get('name')} ({d.get('type')}:{d.get('ip')})" for d in unique_targets]
        log.info(f"Dispatching speech '{text[:40]}' to {len(unique_targets)} device(s): {', '.join(target_names)}")

        for dev in unique_targets:
            dtype = dev.get("type", "google")
            dev_name = dev.get("name") or dev.get("ip")
            if dtype == "google":
                ip_val = str(dev.get("ip", ""))
                if ":" in ip_val:
                    parts = ip_val.split(":")
                    host = parts[0]
                    try:
                        port = int(parts[1])
                    except ValueError:
                        port = 8009
                else:
                    host = dev.get("host") or ip_val
                    port = int(dev.get("port", 8009))
                log.info(f"[Dispatch -> Google Cast] {dev_name} ({host}:{port}) URL: {audio_url} (delay={google_delay}ms)")
                coro = cast_service.play_audio(host, port, audio_url, effective_vol)
                tasks.append(_run_delayed(google_delay, coro))
            elif dtype == "homepod":
                log.info(f"[Dispatch -> HomePod] {dev_name} ({dev.get('ip')}) File: {speech['filepath']} (delay={homepod_delay}ms)")
                coro = homepod_service.play_audio(dev.get("ip", ""), speech["filepath"], volume_level=effective_vol)
                tasks.append(_run_delayed(homepod_delay, coro))
            elif dtype == "dlna":
                log.info(f"[Dispatch -> DLNA] {dev_name} ({dev.get('ip')}) URL: {audio_url}")
                tasks.append(dlna_service.play_audio(dev, audio_url, effective_vol))
            elif dtype in ("onvif", "tapo"):
                log.info(f"[Dispatch -> {dtype.upper()}] {dev_name} ({dev.get('ip')}) file: {speech['filepath']}")
                tasks.append(onvif_service.play_audio(dev, speech["filepath"], speech["duration"], effective_vol))
            elif dtype == "alexa":
                log.info(f"[Dispatch -> Alexa] {dev_name} text: '{text[:30]}' (delay={alexa_delay}ms)")
                coro = alexa_service.speak(dev.get("name", ""), text, volume_level=effective_vol)
                tasks.append(_run_delayed(alexa_delay, coro))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        detailed_results = []
        for i, dev in enumerate(unique_targets):
            dev_name = dev.get("name") or dev.get("ip")
            res_val = results[i] if i < len(results) else False
            is_ok = (res_val is True or (isinstance(res_val, dict) and res_val.get("status") != "error"))
            err_msg = None
            if isinstance(res_val, Exception):
                err_msg = f"{type(res_val).__name__}: {res_val}"
                log.error(f"[Dispatch Result] ❌ {dev_name} failed with exception: {err_msg}")
            elif not is_ok:
                err_msg = "Playback failed"
                log.warning(f"[Dispatch Result] ❌ {dev_name} failed (result={res_val})")
            else:
                log.info(f"[Dispatch Result] ✅ {dev_name} success")

            detailed_results.append({
                "target": dev_name,
                "status": "success" if is_ok else "error",
                "error": err_msg
            })

        has_success = any(r["status"] == "success" for r in detailed_results)
        all_success = len(detailed_results) > 0 and all(r["status"] == "success" for r in detailed_results)

        history_status = "success" if all_success else ("partial" if has_success else "error")
        history_msg = f"{len(detailed_results)} 台のスピーカーへ送信成功" if all_success else (
            f"一部端末のみ成功 ({sum(1 for r in detailed_results if r['status'] == 'success')}/{len(detailed_results)} 台)" if has_success else "全デバイスへの送信に失敗しました"
        )

        if speech.get("fallback"):
            history_msg = f"{history_msg} (※外部TTS接続不可のためEdge TTSでフォールバック発話)"

        # 6. 永続化履歴記録
        saved_audio_url = f"/voice/{speech['filename']}" if speech.get("filename") else ""
        history_entry = {
            "text": text,
            "source": effective_source,
            "sourceLabel": source_label,
            "clientName": client_name,
            "clientIp": client_ip or "",
            "wasQueued": was_queued,
            "targets": [d.get("name") or d.get("ip") for d in unique_targets],
            "voice": opt_voice,
            "actualVoice": speech.get("voice", opt_voice),
            "fallback": bool(speech.get("fallback", False)),
            "rate": opt_rate,
            "pitch": opt_pitch,
            "audioUrl": saved_audio_url,
            "duration": speech["duration"],
            "status": history_status,
            "statusMessage": history_msg,
            "urgent": urgent,
            "results": detailed_results
        }
        self.record_history(history_entry)

        return {
            "success": has_success,
            "status": history_status,
            "message": history_msg,
            "targets": [d.get("name") for d in unique_targets],
            "audioUrl": history_entry["audioUrl"],
            "duration": speech["duration"],
            "results": detailed_results
        }

    # say / speak の相互運用性保証エイリアス
    say = speak

speech_service = SpeechService()
