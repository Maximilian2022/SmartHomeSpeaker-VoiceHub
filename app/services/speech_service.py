import asyncio
import os
import time
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union, Set
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
        self._active_playbacks: Dict[str, Dict[str, Any]] = {}

    def _prune_expired_playbacks(self):
        now = time.monotonic()
        expired = [
            sid for sid, sess in self._active_playbacks.items()
            if now > sess.get("expected_end_at", 0)
            and all(it["task"].done() for it in sess.get("items", []) if it.get("task"))
        ]
        for sid in expired:
            self._active_playbacks.pop(sid, None)

    async def stop_active_playbacks(self, room_tags: Optional[Set[str]] = None) -> int:
        """
        現在再生中・ディスパッチ中のアクティブな対象（VoiceHub が直近再生開始したもの）のみ即座に停止。
        room_tags が指定された場合は、その部屋タグに一致する対象のみを停止する。
        """
        self._prune_expired_playbacks()
        now = time.monotonic()
        stop_coros = []
        stopped_count = 0

        for sess in list(self._active_playbacks.values()):
            is_within_window = now <= sess.get("expected_end_at", 0)
            audio_url = sess.get("audio_url", "")

            for item in sess.get("items", []):
                if item.get("stopped"):
                    continue
                task = item.get("task")
                is_running = bool(task and not task.done())
                if not is_running and not is_within_window:
                    continue

                dev = item.get("dev") or {}
                item_room = item.get("room_tag") or ""
                dtype = dev.get("type", "google")
                is_group = bool(dev.get("isGroup"))

                # 部屋タグ指定がある場合のフィルタリング
                if room_tags is not None:
                    # グループ再生中だった場合は、該当部屋の個別メンバーのみ停止を試みる
                    if is_group and dtype == "google":
                        fb_members = dev.get("_fallback_members") or []
                        matched_members = [
                            m for m in fb_members
                            if (m.get("roomTag") or settings_manager.get_room_tag_for_device(m.get("id"), m.get("ip"), m.get("clientId"))) in room_tags
                        ]
                        if not matched_members:
                            continue
                        item["stopped"] = True
                        for m in matched_members:
                            m_host = m.get("host") or str(m.get("ip", "")).split(":")[0]
                            m_port = int(m.get("port", 8009))
                            if m_host:
                                stop_coros.append(cast_service.stop_playback(m_host, m_port, expected_media_url=audio_url))
                                stopped_count += 1
                        continue
                    elif item_room not in room_tags:
                        continue

                item["stopped"] = True
                sess["stopped"] = True
                if task and not task.done():
                    task.cancel()

                stopped_count += 1
                if dtype == "google":
                    host = item.get("host") or dev.get("host") or str(dev.get("ip", "")).split(":")[0]
                    port = int(item.get("port") or dev.get("port", 8009))
                    if host:
                        stop_coros.append(cast_service.stop_playback(host, port, expected_media_url=audio_url))
                elif dtype == "homepod":
                    stop_coros.append(homepod_service.stop_playback(dev.get("ip", "")))
                elif dtype == "dlna":
                    stop_coros.append(dlna_service.stop_playback(dev))
                elif dtype in ("onvif", "tapo"):
                    stop_coros.append(onvif_service.stop_playback(dev))
                elif dtype == "alexa":
                    stop_coros.append(alexa_service.stop_playback(dev.get("name", "")))
                elif dtype in ("client", "pc"):
                    raw_cid = dev.get("clientId") or str(dev.get("ip", "")).replace("client:", "").split("@", 1)[0]
                    if raw_cid:
                        reason = "dnd_mute" if room_tags is None else "vc_room_mute"
                        stop_coros.append(
                            client_speaker_service.broadcast_control_event("stop", {"reason": reason}, target_client_id=raw_cid)
                        )

        if stop_coros:
            await asyncio.gather(*stop_coros, return_exceptions=True)

        if stopped_count > 0:
            log.info(f"⏹️ Sent immediate stop to {stopped_count} active playback target(s) (room_filter={sorted(room_tags) if room_tags else 'ALL'})")
        return stopped_count

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
                tgt_lower = tgt.lower()
                # 1. ID / ラベル / 名前 の完全一致（グループ名やラベル指定を優先）
                found = next(
                    (
                        d for d in all_devices
                        if str(d.get("id", "")).lower() == tgt_lower
                        or (d.get("label") and str(d["label"]).lower() == tgt_lower)
                        or str(d.get("name", "")).lower() == tgt_lower
                    ),
                    None
                )
                # 2. IP / host の一致（同一IPを持つCastグループに吸われないよう個別端末を優先）
                if not found:
                    found = next(
                        (
                            d for d in all_devices
                            if not d.get("isGroup")
                            and (
                                str(d.get("ip", "")).lower() == tgt_lower
                                or str(d.get("host", "")).lower() == tgt_lower
                                or f"{str(d.get('host', d.get('ip', ''))).lower()}:{d.get('port', 8009)}" == tgt_lower
                            )
                        ),
                        None
                    )
                if not found:
                    found = next(
                        (
                            d for d in all_devices
                            if str(d.get("ip", "")).lower() == tgt_lower
                            or str(d.get("host", "")).lower() == tgt_lower
                        ),
                        None
                    )
                if not found:
                    found = device_manager.find_device(tgt)
                if found:
                    expanded_devices.append(found)

        # 物理エンドポイントに基づく厳格な重複排除
        # (同一IPへの二重送信による途中上書き・再生キャンセルを防止)
        unique_targets: List[Dict[str, Any]] = []
        seen_keys = set()
        for d in expanded_devices:
            dtype = d.get("type", "google")
            is_grp = bool(d.get("isGroup"))
            if dtype == "google":
                if is_grp:
                    key = f"google_group:{d.get('name') or d.get('id')}"
                else:
                    host = d.get("host") or str(d.get("ip", "")).split(":")[0]
                    key = f"google_host:{host}"
            elif dtype in ("client", "pc"):
                key = f"client:{d.get('id') or d.get('ip')}"
            elif dtype == "alexa":
                key = f"alexa:{d.get('name') or d.get('id')}"
            else:
                raw_ip = str(d.get("ip", "")).split(":")[0]
                key = f"{dtype}:{raw_ip}"

            if key not in seen_keys:
                seen_keys.add(key)
                unique_targets.append(d)

        def _get_unique_google_members(devs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """Google Cast 個別端末一覧から同一IP（物理端末）の重複を完全排除"""
            seen_hosts = set()
            res = []
            for d in devs:
                if d.get("type") == "google" and not d.get("isGroup"):
                    h = d.get("host") or str(d.get("ip", "")).split(":")[0]
                    if h and h not in seen_hosts:
                        seen_hosts.add(h)
                        res.append(d)
            return res

        # Google Cast ネイティブグループ集約 (失敗時の個別フォールバック用に元リストも保持)
        has_all = any(t.upper() in ("ALL", "*", "GH:ALL", "GOOGLE:ALL") for t in target_list)
        google_devs = [d for d in unique_targets if d.get("type") == "google"]
        if has_all and len(google_devs) > 1:
            cast_group = next((d for d in google_devs if d.get("isGroup")), None)
            if cast_group:
                individual_devs = _get_unique_google_members(google_devs)
                cast_group["_fallback_members"] = individual_devs
                unique_targets = [d for d in unique_targets if d.get("type") != "google" or d == cast_group]

        # 直接キャストグループが指定された場合でも個別スピーカー群を _fallback_members に必ず紐付ける (IP重複排除)
        for d in unique_targets:
            if d.get("type") == "google" and d.get("isGroup") and not d.get("_fallback_members"):
                d["_fallback_members"] = _get_unique_google_members(all_devices)

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

        # 無効化 (disabled) されたスピーカーを除外
        active_targets = [d for d in unique_targets if not settings_manager.is_device_disabled(d.get("id"), d.get("ip"), d.get("name"))]
        if not active_targets:
            err_msg = "対象スピーカーが見つからないか、無効化されています (No active target devices found)"
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

        # 各ターゲットに最新の部屋タグを補完
        def _attach_room_tag(dev_dict: Dict[str, Any]) -> Dict[str, Any]:
            d_copy = dict(dev_dict)
            if not d_copy.get("roomTag"):
                d_copy["roomTag"] = settings_manager.get_room_tag_for_device(
                    d_copy.get("id"), d_copy.get("ip"), d_copy.get("clientId")
                )
            return d_copy

        unique_targets = [_attach_room_tag(d) for d in active_targets]

        # 3.5 部屋タグ連動・PC VC 参加中自動ミュート評価 (urgent=True は貫通)
        muted_rooms = client_speaker_service.get_vc_muted_rooms()
        dnd_conf = settings_manager.get().get("dnd", {})
        vc_action = dnd_conf.get("action", "skip")
        vc_whisper_vol = dnd_conf.get("whisperVolume", 10)
        vc_muted_summary: List[str] = []

        if not urgent and muted_rooms:
            # グループターゲット内に VC ミュート対象部屋のデバイスが含まれる場合は個別端末へ展開
            expanded_for_vc: List[Dict[str, Any]] = []
            for d in unique_targets:
                if d.get("isGroup"):
                    dtype = d.get("type", "google")
                    if dtype == "google":
                        members = d.get("_fallback_members") or [
                            ad for ad in all_devices if ad.get("type") == "google" and not ad.get("isGroup")
                        ]
                    elif dtype == "alexa":
                        members = [ad for ad in all_devices if ad.get("type") == "alexa" and not ad.get("isGroup")]
                    elif dtype == "homepod":
                        members = [ad for ad in all_devices if ad.get("type") == "homepod" and not ad.get("isGroup")]
                    else:
                        members = []

                    enabled_members = [
                        _attach_room_tag(m) for m in members
                        if not settings_manager.is_device_disabled(m.get("id"), m.get("ip"), m.get("name"))
                    ]
                    if enabled_members and any(m.get("roomTag") in muted_rooms for m in enabled_members):
                        log.info(f"[Speech] Expanding group '{d.get('name')}' into {len(enabled_members)} member(s) for room VC auto-mute")
                        expanded_for_vc.extend(enabled_members)
                        continue
                expanded_for_vc.append(d)

            # 展開後の簡易重複排除
            seen_vc_keys = set()
            deduped_for_vc: List[Dict[str, Any]] = []
            for d in expanded_for_vc:
                k = f"{d.get('type')}:{d.get('host') or d.get('ip') or d.get('id')}"
                if k not in seen_vc_keys:
                    seen_vc_keys.add(k)
                    deduped_for_vc.append(d)

            speak_targets: List[Dict[str, Any]] = []
            suppressed_rooms: Dict[str, List[Dict[str, Any]]] = {}
            for d in deduped_for_vc:
                r_tag = d.get("roomTag") or ""
                if r_tag and r_tag in muted_rooms:
                    if vc_action == "whisper":
                        w_ratio = max(0.01, min(1.0, float(vc_whisper_vol) / 100.0))
                        d["_override_volume"] = w_ratio
                        speak_targets.append(d)
                        if r_tag not in vc_muted_summary:
                            vc_muted_summary.append(r_tag)
                    else:
                        suppressed_rooms.setdefault(r_tag, []).append(d)
                else:
                    speak_targets.append(d)

            # skip / queue された部屋の履歴＆保留キュー記録
            for r_tag, room_devs in suppressed_rooms.items():
                vc_muted_summary.append(r_tag)
                dev_labels = [rd.get("name") or rd.get("ip") for rd in room_devs]
                dev_targets = [rd.get("ip") or rd.get("id") or rd.get("name") for rd in room_devs if (rd.get("ip") or rd.get("id") or rd.get("name"))]
                reason_str = f"PC VC中 (部屋: {r_tag})"
                dnd_service.record_history(
                    text=text,
                    reason=reason_str,
                    action=vc_action,
                    target=", ".join(dev_labels)
                )
                if vc_action == "queue":
                    hist_rec = self.record_history({
                        "text": text,
                        "source": effective_source,
                        "sourceLabel": source_label,
                        "clientName": client_name,
                        "clientIp": client_ip or "",
                        "targets": dev_labels,
                        "voice": voice or tts_service.get_default_voice_id(),
                        "status": "queued",
                        "statusMessage": f"{reason_str} のため保留キューに追加しました",
                        "urgent": urgent,
                        "wasQueued": True,
                        "results": []
                    })
                    dnd_service.add_to_queue({
                        "history_id": hist_rec.get("id"),
                        "text": text,
                        "targets": dev_targets,
                        "room_tag": r_tag,
                        "voice": voice,
                        "client": client_name,
                        "client_ip": client_ip,
                        "source": effective_source,
                        "source_label": source_label
                    })
                elif not speak_targets:
                    # 他部屋の送信先がない場合は skip 履歴をここで記録
                    pass

            if not speak_targets:
                rooms_disp = ", ".join(sorted(suppressed_rooms.keys()))
                if vc_action == "queue":
                    return {
                        "success": True,
                        "status": "queued",
                        "vcRoomMuted": True,
                        "mutedRooms": sorted(suppressed_rooms.keys()),
                        "queued": True,
                        "message": f"Queued for VC active room(s): {rooms_disp}",
                        "results": []
                    }
                else:
                    self.record_history({
                        "text": text,
                        "source": effective_source,
                        "sourceLabel": source_label,
                        "clientName": client_name,
                        "clientIp": client_ip or "",
                        "targets": [d.get("name") or d.get("ip") for d in deduped_for_vc],
                        "voice": voice or "ja-JP-NanamiNeural",
                        "status": "suppressed",
                        "statusMessage": f"PC VC参加中の部屋 ({rooms_disp}) のため自動ミュートしました",
                        "urgent": urgent,
                        "wasQueued": False,
                        "results": []
                    })
                    return {
                        "success": True,
                        "status": "skipped",
                        "vcRoomMuted": True,
                        "mutedRooms": sorted(suppressed_rooms.keys()),
                        "message": f"Suppressed by VC active room(s): {rooms_disp}",
                        "results": []
                    }

            if suppressed_rooms and vc_action == "skip":
                # 別部屋でも発話する場合、スキップされた部屋の分も分かりやすくログ出力
                log.info(f"[Speech] Skipped room(s) {sorted(suppressed_rooms.keys())} due to active VC; continuing for {len(speak_targets)} other target(s)")

            unique_targets = speak_targets

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

        target_names = [f"{d.get('name')} ({d.get('type')}:{d.get('ip')})" for d in unique_targets]
        log.info(f"Dispatching speech '{text[:40]}' to {len(unique_targets)} device(s): {', '.join(target_names)}")

        async def _dispatch_google_with_retries(dev: Dict[str, Any], target_vol: Optional[float]) -> bool:
            """
            Google Cast 送信処理:
            - グループ: 最大3回試行 (失敗時、最新ポート/IPを再解決してリトライ)
            - 個別: 最大3回試行 (失敗時、DHCP等によるIP変動を名前から再解決してリトライ)
            """
            is_group = bool(dev.get("isGroup") or dev.get("port", 8009) != 8009)
            max_attempts = 3
            dev_name = dev.get("name") or dev.get("ip")
            tried_endpoints = set()

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
                tried_endpoints.add((current_host, current_port))
                if attempt > 1 and google_delay > 0:
                    await asyncio.sleep(google_delay / 1000.0)

                log.info(f"[Dispatch -> Google Cast] {dev_name} ({current_host}:{current_port}) URL: {audio_url} (試行 {attempt}/{max_attempts}, delay={google_delay}ms)")
                success = await cast_service.play_audio(current_host, current_port, audio_url, target_vol)
                if success:
                    if attempt > 1:
                        log.info(f"[Speech] ✅ Google Cast '{dev_name}' はリトライ (試行 {attempt}/{max_attempts}) で再生成功しました")
                        if is_group:
                            device_manager.promote_group_endpoint(dev.get("name") or dev_name, current_host, current_port)
                    return True

                cast_service.purge_cache(current_host, current_port)
                if attempt < max_attempts:
                    target_type_str = "キャストグループ" if is_group else "個別スピーカー"
                    log.warning(f"[Speech] ⚠️ Google Cast {target_type_str} '{dev_name}' ({current_host}:{current_port}) への再生失敗。別ポート/IPを探索してリトライします (試行 {attempt + 1}/{max_attempts})...")
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
                                    if ld.get("name") == dev.get("name") or (dev.get("rawName") and ld.get("rawName") == dev.get("rawName")):
                                        matched = ld
                                        break

                        alt_found = False
                        if is_group:
                            candidates = (matched.get("candidateEndpoints") if matched else None) or dev.get("candidateEndpoints") or []
                            for ep in candidates:
                                ep_h = ep.get("host")
                                ep_p = int(ep.get("port", 8009))
                                if (ep_h, ep_p) not in tried_endpoints:
                                    log.info(f"[Speech] 🔄 キャストグループ '{dev_name}' の未試行候補エンドポイントへ切り替えます: ({current_host}:{current_port} -> {ep_h}:{ep_p})")
                                    current_host = ep_h
                                    current_port = ep_p
                                    alt_found = True
                                    break

                        if not alt_found and matched:
                            new_host = matched.get("host") or str(matched.get("ip", "")).split(":")[0]
                            new_port = int(matched.get("port", 8009))
                            if (new_host, new_port) not in tried_endpoints:
                                log.info(f"[Speech] 🔄 最新接続先を検出しました: {dev_name} ({current_host}:{current_port} -> {new_host}:{new_port})")
                                current_host = new_host
                                current_port = new_port
                    except Exception as ex:
                        log.debug(f"[Speech] 再解決エラー (リトライ継続): {ex}")

            log.warning(f"[Speech] ❌ Google Cast '{dev_name}' への再生が全 {max_attempts} 回の試行で失敗しました")
            return False

        # アクティブ再生セッション登録（DND / VC 開始時の即時停止対象トラッキング）
        self._prune_expired_playbacks()
        session_id = uuid.uuid4().hex[:12]
        raw_dur = float(speech.get("duration") or 0.0)
        est_dur = raw_dur if raw_dur > 0.0 else max(5.0, len(text) * 0.18 + 3.0)
        session_info: Dict[str, Any] = {
            "session_id": session_id,
            "started_at": time.monotonic(),
            "expected_end_at": time.monotonic() + est_dur + 4.0,
            "audio_url": audio_url,
            "items": [],
            "stopped": False,
        }
        self._active_playbacks[session_id] = session_info

        def _resolve_target_vol(d_item: Dict[str, Any]) -> Optional[float]:
            ov = d_item.get("_override_volume")
            if ov is not None:
                return min(effective_vol, float(ov)) if effective_vol is not None else float(ov)
            return effective_vol

        tasks = []
        for dev in unique_targets:
            dtype = dev.get("type", "google")
            dev_name = dev.get("name") or dev.get("ip")
            target_vol = _resolve_target_vol(dev)
            coro = None
            item_host = None
            item_port = 8009

            if dtype == "google":
                item_host = dev.get("host") or str(dev.get("ip", "")).split(":")[0]
                item_port = int(dev.get("port", 8009))
                coro = _run_delayed(google_delay, _dispatch_google_with_retries(dev, target_vol))
            elif dtype == "homepod":
                log.info(f"[Dispatch -> HomePod] {dev_name} ({dev.get('ip')}) File: {speech['filepath']} (delay={homepod_delay}ms)")
                coro = _run_delayed(homepod_delay, homepod_service.play_audio(dev.get("ip", ""), speech["filepath"], volume_level=target_vol))
            elif dtype == "dlna":
                log.info(f"[Dispatch -> DLNA] {dev_name} ({dev.get('ip')}) URL: {audio_url}")
                coro = dlna_service.play_audio(dev, audio_url, target_vol)
            elif dtype in ("onvif", "tapo"):
                log.info(f"[Dispatch -> {dtype.upper()}] {dev_name} ({dev.get('ip')}) file: {speech['filepath']}")
                coro = onvif_service.play_audio(dev, speech["filepath"], speech["duration"], target_vol)
            elif dtype == "alexa":
                log.info(f"[Dispatch -> Alexa] {dev_name} text: '{text[:30]}' (delay={alexa_delay}ms)")
                coro = _run_delayed(alexa_delay, alexa_service.speak(dev.get("name", ""), text, volume_level=target_vol))
            elif dtype in ("client", "pc"):
                client_id = dev.get("ip", "").replace("client:", "")
                log.info(f"[Dispatch -> Client Speaker] {dev_name} (id={client_id}) URL: {audio_url}")
                coro = client_speaker_service.send_play_event(client_id, audio_url, text=text, volume=target_vol)

            if coro is not None:
                t_obj = asyncio.create_task(coro)
                tasks.append(t_obj)
                session_info["items"].append({
                    "dev": dev,
                    "room_tag": dev.get("roomTag") or "",
                    "host": item_host,
                    "port": item_port,
                    "task": t_obj,
                    "stopped": False,
                })

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # DND / VC 開始により途中で即時停止された場合は、フォールバック・リトライを行わず中断完了とする
        if session_info.get("stopped"):
            stopped_results = [
                {"target": d.get("name") or d.get("ip"), "status": "stopped", "error": "DNDまたはVC開始により中断"}
                for d in unique_targets
            ]
            stop_msg = "おやすみ・会議モード (DND) または通話開始により再生を即時中断しました"
            saved_audio_url = f"/voice/{speech['filename']}" if speech.get("filename") else ""
            self.record_history({
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
                "duration": speech.get("duration", 0),
                "status": "suppressed",
                "statusMessage": stop_msg,
                "urgent": urgent,
                "results": stopped_results,
            })
            return {
                "success": True,
                "status": "stopped",
                "message": stop_msg,
                "targets": [d.get("name") for d in unique_targets],
                "audioUrl": saved_audio_url,
                "duration": speech.get("duration", 0),
                "results": stopped_results,
            }

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
            if fallback_members and not is_ok and not session_info.get("stopped"):
                # 実行時にも IP 重複を完全排除（同一スピーカーへの二重送信による途中上書きキャンセルを防止）
                seen_fb_hosts = set()
                deduped_members = []
                for fbm in fallback_members:
                    f_host = fbm.get("host") or str(fbm.get("ip", "")).split(":")[0]
                    if f_host and f_host not in seen_fb_hosts:
                        seen_fb_hosts.add(f_host)
                        deduped_members.append(fbm)
                    elif f_host in seen_fb_hosts:
                        log.warning(f"[Speech] ⚠️ 同一IP ({f_host}) への重複送信をスキップ: {fbm.get('name')}")

                log.warning(f"[Speech] ⚠️ Google Cast グループ '{dev.get('name') or dev.get('ip')}' (全試行) 失敗のため、重複排除済み個別スピーカー {len(deduped_members)} 台へ自動フォールバックします")
                fb_tasks = []
                for fb_dev in deduped_members:
                    fb_tasks.append(_run_delayed(google_delay, _dispatch_google_with_retries(fb_dev, _resolve_target_vol(fb_dev))))
                if fb_tasks:
                    fb_results = await asyncio.gather(*fb_tasks, return_exceptions=True)
                    has_any_fb_ok = False
                    for j, fb_dev in enumerate(deduped_members):
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
        if not has_any_success and not session_info.get("stopped"):
            fb_targets = await self.resolve_fallback_targets(all_devices)
            orig_ips = {d.get("ip") for d in unique_targets}
            needed_fb = []
            for d in fb_targets:
                if d.get("ip") in orig_ips:
                    continue
                d_with_tag = _attach_room_tag(d)
                if not urgent and muted_rooms and vc_action != "whisper" and d_with_tag.get("roomTag") in muted_rooms:
                    continue
                needed_fb.append(d_with_tag)
            if needed_fb:
                log.warning(f"[Speech] ⚠️ 全宛先への送信が失敗したため、設定されたフォールバック先 {[d.get('name') or d.get('ip') for d in needed_fb]} へ自動救済送信します...")
                fb_gen_tasks = []
                for d in needed_fb:
                    dtype = d.get("type", "google")
                    fb_vol = effective_vol
                    if not urgent and muted_rooms and vc_action == "whisper" and d.get("roomTag") in muted_rooms:
                        w_ratio = max(0.01, min(1.0, float(vc_whisper_vol) / 100.0))
                        fb_vol = min(effective_vol, w_ratio) if effective_vol is not None else w_ratio
                    if dtype == "google":
                        fb_gen_tasks.append(_dispatch_google_with_retries(d, fb_vol))
                    elif dtype == "alexa":
                        fb_gen_tasks.append(alexa_service.speak(d.get("name", ""), text, volume_level=fb_vol))
                    elif dtype == "homepod":
                        fb_gen_tasks.append(homepod_service.play_audio(d.get("ip", ""), speech["filepath"], volume_level=fb_vol))
                    elif dtype == "dlna":
                        fb_gen_tasks.append(dlna_service.play_audio(d, audio_url, fb_vol))
                    elif dtype in ("onvif", "tapo"):
                        fb_gen_tasks.append(onvif_service.play_audio(d, speech["filepath"], speech["duration"], fb_vol))

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
