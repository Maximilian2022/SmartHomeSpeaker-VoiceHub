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
from app.services.client_speaker_service import client_speaker_service
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
                expanded_devices.extend([
                    d for d in all_devices
                    if d.get("type") not in ("client", "pc") or d.get("isPrimary", True)
                ])
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
            elif norm_tgt in ("PC:ALL", "CLIENT:ALL", "WIN:ALL", "MAC:ALL"):
                expanded_devices.extend([
                    d for d in all_devices
                    if d.get("type") in ("client", "pc") and d.get("isPrimary", True)
                ])
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

        # 重複排除 (同一IDまたは同一IP:Port)
        unique_targets: List[Dict[str, Any]] = []
        seen_keys = set()
        for d in expanded_devices:
            key = d.get("id") or f"{d.get('ip')}:{d.get('port', 8009)}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique_targets.append(d)

        # Google Cast ネイティブグループ集約 (失敗時の個別フォールバック用に元リストも保持)
        has_all = any(t.upper() in ("ALL", "*", "GH:ALL", "GOOGLE:ALL") for t in target_list)
        google_devs = [d for d in unique_targets if d.get("type") == "google"]
        if has_all and len(google_devs) > 1:
            cast_group = next((d for d in google_devs if d.get("isGroup")), None)
            if cast_group:
                individual_devs = [d for d in google_devs if not d.get("isGroup")]
                cast_group["_fallback_members"] = individual_devs
                unique_targets = [d for d in unique_targets if d.get("type") != "google" or d == cast_group]

        # 直接キャストグループが指定された場合でも個別スピーカー群を _fallback_members に必ず紐付ける
        for d in unique_targets:
            if d.get("type") == "google" and d.get("isGroup") and not d.get("_fallback_members"):
                d["_fallback_members"] = [dev for dev in all_devices if dev.get("type") == "google" and not dev.get("isGroup")]

        return unique_targets

    async def resolve_fallback_targets(self, all_devices: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        送信失敗時のフォールバック先スピーカー一覧を決定
        優先順位:
          1. ユーザー設定 fallbackSpeaker が明示指定されている場合: それに従う
          2. auto (デフォルト):
             - 階層1: Group（グループ） > 単体スピーカー
             - 階層2: GH (Google Home) > Alexa > HP (HomePod) > DLNA > ONVIF/Tapo
        """
        if all_devices is None:
            all_devices = await device_manager.get_devices()

        fb_pref = settings_manager.get().get("fallbackSpeaker", "auto")
        if fb_pref == "none":
            return []
        elif fb_pref == "default":
            def_ip = device_manager.get_default_device_ip()
            found = device_manager.find_device(def_ip) if def_ip else None
            return [found] if found else []
        elif fb_pref != "auto":
            found = device_manager.find_device(fb_pref)
            if found:
                return [found]

        # auto: Group > 単体, GH > Alexa > HP > DLNA > ONVIF
        # 1. Google Cast Group (ALL / 全部 / 全室 を優先、無ければ先頭グループ)
        cast_groups = [d for d in all_devices if d.get("type") == "google" and d.get("isGroup")]
        if cast_groups:
            all_g = next((g for g in cast_groups if g.get("name", "").upper() == "ALL" or "全部" in g.get("name", "") or "全室" in g.get("name", "")), cast_groups[0])
            g_copy = dict(all_g)
            g_copy["_fallback_members"] = [d for d in all_devices if d.get("type") == "google" and not d.get("isGroup")]
            return [g_copy]

        # 2. Alexa Group
        alexa_groups = [d for d in all_devices if d.get("type") == "alexa" and d.get("isGroup")]
        if alexa_groups:
            return [alexa_groups[0]]

        # 3. HomePod Group
        hp_groups = [d for d in all_devices if d.get("type") == "homepod" and d.get("isGroup")]
        if hp_groups:
            return [hp_groups[0]]

        # 4. Google Cast 単体スピーカー群
        google_indiv = [d for d in all_devices if d.get("type") == "google" and not d.get("isGroup")]
        if google_indiv:
            return google_indiv

        # 5. Alexa 単体スピーカー群
        alexa_indiv = [d for d in all_devices if d.get("type") == "alexa" and not d.get("isGroup")]
        if alexa_indiv:
            return alexa_indiv

        # 6. HomePod 単体スピーカー群
        hp_indiv = [d for d in all_devices if d.get("type") == "homepod" and not d.get("isGroup")]
        if hp_indiv:
            return hp_indiv

        # 7. DLNA スピーカー群
        dlna_indiv = [d for d in all_devices if d.get("type") == "dlna"]
        if dlna_indiv:
            return dlna_indiv

        # 8. ONVIF / Tapo スピーカー群
        onvif_indiv = [d for d in all_devices if d.get("type") in ("onvif", "tapo")]
        if onvif_indiv:
            return onvif_indiv

        return all_devices[:1] if all_devices else []


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
        speed: Optional[str] = None,
        existing_history_id: Optional[str] = None
    ) -> Dict[str, Any]:
        text = text.strip()
        if not text:
            return {"status": "error", "message": "Text cannot be empty"}

        effective_source = source or ("web_ui" if "Mozilla" in client_name or "Web" in client_name else "api")

        # 1. 重複排除 (Deduplication) - Web画面からの直接テスト発言(web_ui / quick_test)は除外
        dedup_conf = settings_manager.get().get("deduplication", {})
        if not urgent and effective_source not in ("web_ui", "quick_test") and dedup_conf.get("enabled", True):
            cooldown = dedup_conf.get("cooldownSeconds", 30)
            if deduplicator.is_duplicate(text, client_name, cooldown):
                skip_msg = f"直前の同一通知から {cooldown} 秒以内のため重複スキップしました"
                self.record_history({
                    "text": text,
                    "source": effective_source,
                    "sourceLabel": source_label,
                    "clientName": client_name,
                    "clientIp": client_ip or "",
                    "targets": [targets] if isinstance(targets, str) else (targets or ["デフォルト"]),
                    "voice": voice or "ja-JP-NanamiNeural",
                    "status": "skipped",
                    "statusMessage": skip_msg,
                    "urgent": urgent,
                    "wasQueued": False,
                    "results": []
                })
                return {
                    "success": True,
                    "status": "skipped",
                    "message": skip_msg,
                    "deduplicated": True,
                    "results": []
                }

        # 2. DND 評価 (おやすみ・会議モード)
        current_meeting = calendar_service.get_current_meeting_title()
        dnd_result = dnd_service.evaluate(active_event_title=current_meeting, urgent=urgent)

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
                hist_record = self.record_history({
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
                dnd_service.add_to_queue({
                    "history_id": hist_record.get("id"),
                    "text": text,
                    "targets": targets,
                    "voice": voice,
                    "client": client_name,
                    "client_ip": client_ip,
                    "source": effective_source,
                    "source_label": source_label
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
            err_msg = "対象スピーカーが見つかりませんでした (No valid target devices found)"
            log.warning(f"[Speech] {err_msg}: targets={targets}")
            self.record_history({
                "text": text,
                "source": effective_source,
                "sourceLabel": source_label,
                "clientName": client_name,
                "clientIp": client_ip or "",
                "targets": [targets] if isinstance(targets, str) else (targets or ["デフォルト"]),
                "voice": voice or "ja-JP-NanamiNeural",
                "status": "error",
                "statusMessage": err_msg,
                "urgent": urgent,
                "wasQueued": False,
                "results": []
            })
            return {"status": "error", "message": err_msg}

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
            try:
                speech = await tts_service.synthesize(
                    text=text,
                    voice=opt_voice,
                    rate=opt_rate,
                    pitch=opt_pitch,
                    chime=opt_chime,
                    urgent=urgent
                )
                audio_url = f"{self.server_base_url}/voice/{speech['filename']}"
            except Exception as e:
                err_msg = "音声合成に失敗しました"
                log.error(f"[Speech] TTS合成エラー: {e}", exc_info=True)
                self.record_history({
                    "text": text,
                    "source": effective_source,
                    "sourceLabel": source_label,
                    "clientName": client_name,
                    "clientIp": client_ip or "",
                    "targets": [d.get("name") or d.get("ip") for d in unique_targets],
                    "voice": opt_voice,
                    "status": "error",
                    "statusMessage": err_msg,
                    "urgent": urgent,
                    "wasQueued": False,
                    "results": [{"target": d.get("name") or d.get("ip"), "status": "error", "error": "音声合成エラー"} for d in unique_targets]
                })
                return {"status": "error", "message": err_msg}

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

        async def _dispatch_google_with_retries(dev: Dict[str, Any]) -> bool:
            """
            Google Cast 送信処理:
            - グループ: 最大2回試行 (失敗時、最新ポート/IPを再解決してリトライ)
            - 個別: 最大3回試行 (失敗時、DHCP等によるIP変動を名前から再解決してリトライ)
            """
            is_group = bool(dev.get("isGroup") or dev.get("port", 8009) != 8009)
            max_attempts = 2 if is_group else 3
            dev_name = dev.get("name") or dev.get("ip")

            current_host = dev.get("host")
            current_port = int(dev.get("port", 8009))
            if not current_host:
                ip_val = str(dev.get("ip", ""))
                if ":" in ip_val:
                    parts = ip_val.split(":")
                    current_host = parts[0]
                    try:
                        current_port = int(parts[1])
                    except ValueError:
                        current_port = 8009
                else:
                    current_host = ip_val

            for attempt in range(1, max_attempts + 1):
                if attempt > 1 and google_delay > 0:
                    await asyncio.sleep(google_delay / 1000.0)

                log.info(f"[Dispatch -> Google Cast] {dev_name} ({current_host}:{current_port}) URL: {audio_url} (試行 {attempt}/{max_attempts}, delay={google_delay}ms)")
                success = await cast_service.play_audio(current_host, current_port, audio_url, effective_vol)
                if success:
                    if attempt > 1:
                        log.info(f"[Speech] ✅ Google Cast '{dev_name}' はリトライ (試行 {attempt}/{max_attempts}) で再生成功しました")
                    return True

                cast_service.purge_cache(current_host, current_port)
                if attempt < max_attempts:
                    target_type_str = "キャストグループ" if is_group else "個別スピーカー"
                    log.warning(f"[Speech] ⚠️ Google Cast {target_type_str} '{dev_name}' ({current_host}:{current_port}) への再生失敗。最新ポート/IPを再解決してリトライします (試行 {attempt + 1}/{max_attempts})...")
                    try:
                        latest_devs = await device_manager.get_devices()
                        matched = None
                        for ld in latest_devs:
                            if ld.get("type") == "google":
                                if is_group and ld.get("isGroup"):
                                    if ld.get("name") == dev.get("name") or ld.get("id") == dev.get("id"):
                                        matched = ld
                                        break
                                elif not is_group and not ld.get("isGroup"):
                                    if ld.get("name") == dev.get("name") or ld.get("rawName") == dev.get("rawName"):
                                        matched = ld
                                        break
                        if matched:
                            new_host = matched.get("host") or str(matched.get("ip", "")).split(":")[0]
                            new_port = int(matched.get("port", 8009))
                            if new_host != current_host or new_port != current_port:
                                log.info(f"[Speech] 🔄 最新接続先を検出しました: {dev_name} ({current_host}:{current_port} -> {new_host}:{new_port})")
                                current_host = new_host
                                current_port = new_port
                    except Exception as ex:
                        log.debug(f"[Speech] 再解決エラー (リトライ継続): {ex}")

            log.warning(f"[Speech] ❌ Google Cast '{dev_name}' への再生が全 {max_attempts} 回の試行で失敗しました")
            return False

        for dev in unique_targets:
            dtype = dev.get("type", "google")
            dev_name = dev.get("name") or dev.get("ip")
            if dtype == "google":
                tasks.append(_run_delayed(google_delay, _dispatch_google_with_retries(dev)))
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
            elif dtype in ("client", "pc"):
                client_id = dev.get("ip", "").replace("client:", "")
                log.info(f"[Dispatch -> Client Speaker] {dev_name} (id={client_id}) URL: {audio_url}")
                tasks.append(client_speaker_service.send_play_event(client_id, audio_url, text=text, volume=effective_vol))

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

        # 1. Google Cast グループ失敗時の個別スピーカー群への自動フォールバック
        for i, dev in enumerate(unique_targets):
            fallback_members = dev.get("_fallback_members")
            res_val = results[i] if i < len(results) else False
            is_ok = (res_val is True or (isinstance(res_val, dict) and res_val.get("status") != "error"))
            if fallback_members and not is_ok:
                log.warning(f"[Speech] ⚠️ Google Cast グループ '{dev.get('name') or dev.get('ip')}' (2回試行) 失敗のため、個別スピーカー {len(fallback_members)} 台へ自動フォールバックします")
                fb_tasks = []
                for fb_dev in fallback_members:
                    fb_tasks.append(_run_delayed(google_delay, _dispatch_google_with_retries(fb_dev)))
                if fb_tasks:
                    fb_results = await asyncio.gather(*fb_tasks, return_exceptions=True)
                    has_any_fb_ok = False
                    for j, fb_dev in enumerate(fallback_members):
                        fb_name = fb_dev.get("name") or fb_dev.get("ip")
                        fb_val = fb_results[j] if j < len(fb_results) else False
                        fb_ok = (fb_val is True or (isinstance(fb_val, dict) and fb_val.get("status") != "error"))
                        if fb_ok:
                            has_any_fb_ok = True
                        fb_err = None
                        if isinstance(fb_val, Exception):
                            fb_err = f"{type(fb_val).__name__}: {fb_val}"
                            log.error(f"[Dispatch Result] ❌ {fb_name} (個別フォールバック) failed: {fb_err}")
                        elif not fb_ok:
                            fb_err = "Fallback playback failed"
                            log.warning(f"[Dispatch Result] ❌ {fb_name} (個別フォールバック) failed")
                        else:
                            log.info(f"[Dispatch Result] ✅ {fb_name} (個別フォールバック) success")
                        detailed_results.append({
                            "target": f"{fb_name} (個別フォールバック)",
                            "status": "success" if fb_ok else "error",
                            "error": fb_err
                        })
                    if has_any_fb_ok:
                        dev_name = dev.get("name") or dev.get("ip")
                        for dr in detailed_results:
                            if dr["target"] == dev_name:
                                dr["status"] = "fallback_recovered"
                                dr["error"] = "グループ送信失敗後、個別スピーカー群へ自動再送成功"

        # 2. 全送信が失敗した場合の全体フォールバック (fallbackSpeaker 設定: auto / default / 個別指定)
        has_any_success = any(r["status"] in ("success", "fallback_recovered") for r in detailed_results)
        if not has_any_success:
            fb_targets = await self.resolve_fallback_targets(all_devices)
            orig_ips = {d.get("ip") for d in unique_targets}
            needed_fb = [d for d in fb_targets if d.get("ip") not in orig_ips]
            if needed_fb:
                log.warning(f"[Speech] ⚠️ 全宛先への送信が失敗したため、設定されたフォールバック先 {[d.get('name') or d.get('ip') for d in needed_fb]} へ自動救済送信します...")
                fb_gen_tasks = []
                for d in needed_fb:
                    dtype = d.get("type", "google")
                    if dtype == "google":
                        fb_gen_tasks.append(_dispatch_google_with_retries(d))
                    elif dtype == "alexa":
                        fb_gen_tasks.append(alexa_service.speak(d.get("name", ""), text, volume_level=effective_vol))
                    elif dtype == "homepod":
                        fb_gen_tasks.append(homepod_service.play_audio(d.get("ip", ""), speech["filepath"], volume_level=effective_vol))
                    elif dtype == "dlna":
                        fb_gen_tasks.append(dlna_service.play_audio(d, audio_url, effective_vol))
                    elif dtype in ("onvif", "tapo"):
                        fb_gen_tasks.append(onvif_service.play_audio(d, speech["filepath"], speech["duration"], effective_vol))

                fb_gen_results = await asyncio.gather(*fb_gen_tasks, return_exceptions=True)
                for k, fbd in enumerate(needed_fb):
                    f_name = fbd.get("name") or fbd.get("ip")
                    f_val = fb_gen_results[k] if k < len(fb_gen_results) else False
                    f_ok = (f_val is True or (isinstance(f_val, dict) and f_val.get("status") != "error"))
                    detailed_results.append({
                        "target": f"{f_name} (全体フォールバック)",
                        "status": "success" if f_ok else "error",
                        "error": None if f_ok else f"General fallback failed ({f_val})"
                    })

        active_results = [r for r in detailed_results if r["status"] != "fallback_recovered"]
        has_success = any(r["status"] == "success" for r in detailed_results)
        all_success = len(active_results) > 0 and all(r["status"] == "success" for r in active_results)

        history_status = "success" if all_success else ("partial" if has_success else "error")
        history_msg = f"{len(active_results)} 台のスピーカーへ送信成功" if all_success else (
            f"一部端末のみ成功 ({sum(1 for r in detailed_results if r['status'] == 'success')}/{len(active_results)} 台)" if has_success else "全デバイスへの送信に失敗しました"
        )

        if speech.get("fallback"):
            history_msg = f"{history_msg} (※外部TTS接続不可のためEdge TTSでフォールバック発話)"

        # 6. 永続化履歴記録
        saved_audio_url = f"/voice/{speech['filename']}" if speech.get("filename") else ""
        if existing_history_id:
            history_manager.update_entry(existing_history_id, {
                "status": history_status,
                "statusMessage": f"DND保留再生完了 ({history_msg})",
                "audioUrl": saved_audio_url,
                "duration": speech.get("duration", 0),
                "actualVoice": speech.get("voice", opt_voice),
                "fallback": bool(speech.get("fallback", False)),
                "results": detailed_results,
                "wasQueued": True
            })
            history_entry = {
                "id": existing_history_id,
                "text": text,
                "audioUrl": saved_audio_url,
                "duration": speech.get("duration", 0),
                "status": history_status
            }
        else:
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
