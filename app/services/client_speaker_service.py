import asyncio
import re
import time
from typing import Dict, Any, List, Optional
from app.core.logger import get_logger
from app.services.settings_service import settings_manager

log = get_logger("ClientSpeaker")


def _sanitize_key(val: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", str(val or "")).strip("_") or "default"


class ClientSpeakerInfo:
    def __init__(
        self,
        client_id: str,
        name: str,
        ip: str,
        platform: str = "pc",
        queue: Optional[asyncio.Queue] = None,
        outputs: Optional[List[Dict[str, Any]]] = None,
        script_hash: str = ""
    ):
        self.id = client_id
        self.name = name
        self.ip = ip
        self.platform = platform  # macos, windows, linux, pc
        self.queue = queue or asyncio.Queue(maxsize=50)
        self.outputs: List[Dict[str, Any]] = outputs if isinstance(outputs, list) else []
        self.script_hash: str = str(script_hash or "")
        self.connected_at = time.time()
        self.last_seen = time.time()

    def touch(self):
        self.last_seen = time.time()

    def _get_model_name(self) -> str:
        p_lower = (self.platform or "").lower()
        if "mac" in p_lower or "darwin" in p_lower:
            return "Mac Speaker"
        elif "win" in p_lower:
            return "Windows Speaker"
        elif "linux" in p_lower:
            return "Linux Speaker"
        return "PC Speaker"

    def to_device_dict(self) -> Dict[str, Any]:
        """DeviceManager と互換性のある単一代表スピーカー情報辞書を生成（後方互換およびメイン出力取得用）"""
        if self.outputs:
            devs = self.to_device_dicts(include_disabled=True)
            primary = next((d for d in devs if d.get("isPrimary")), None)
            if primary:
                return primary
            if devs:
                return devs[0]

        clean_id = self.id.replace(" ", "_").replace(":", "_").replace(".", "_")
        dev_id = f"client_{clean_id}"
        prefix_ip = f"client:{self.id}"
        model_name = self._get_model_name()

        return {
            "id": dev_id,
            "name": self.name or f"PC ({self.ip})",
            "ip": prefix_ip,
            "rawIp": self.ip,
            "model": model_name,
            "type": "client",
            "platform": self.platform,
            "clientId": self.id,
            "clientName": self.name or f"PC ({self.ip})",
            "outputKey": "",
            "outputName": "",
            "enabled": True,
            "isPrimary": True,
            "isOsDefault": True,
            "isOnline": True,
            "isDefault": False,
            "isFavorite": False
        }

    def to_device_dicts(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """
        PC に接続されている各オーディオ出力デバイスを個別のスピーカー辞書リストとして生成。
        outputs が未報告（旧クライアントまたは単体テスト時）の場合は単一デバイス辞書を返す。
        """
        if not self.outputs:
            return [self.to_device_dict()]

        pc_conf = settings_manager.get_pc_speakers_config()
        outputs_conf = pc_conf.get("outputs", {})
        primary_map = pc_conf.get("primaryOutput", {})
        configured_primary_key = primary_map.get(self.id)

        clean_id = self.id.replace(" ", "_").replace(":", "_").replace(".", "_")
        model_name = self._get_model_name()
        base_pc_name = self.name or f"PC ({self.ip})"

        raw_items: List[Dict[str, Any]] = []
        for idx, out in enumerate(self.outputs):
            if not isinstance(out, dict):
                continue
            out_key = str(out.get("key") or f"out_{idx}").strip()
            out_name = str(out.get("name") or out_key).strip()
            is_os_default = bool(out.get("isDefault", False))

            comp_key = f"{self.id}@{out_key}"
            saved = outputs_conf.get(comp_key, {}) if isinstance(outputs_conf, dict) else {}
            enabled = bool(saved.get("enabled", True))
            custom_name = str(saved.get("name") or "").strip()

            display_name = custom_name if custom_name else f"{base_pc_name} ({out_name})"
            dev_id = f"client_{clean_id}_{_sanitize_key(out_key)}"
            prefix_ip = f"client:{self.id}@{out_key}"

            raw_items.append({
                "id": dev_id,
                "name": display_name,
                "ip": prefix_ip,
                "rawIp": self.ip,
                "model": f"{model_name} [{out_name}]",
                "type": "client",
                "platform": self.platform,
                "clientId": self.id,
                "clientName": base_pc_name,
                "outputKey": out_key,
                "outputName": out_name,
                "customName": custom_name,
                "enabled": enabled,
                "isPrimary": False,
                "isOsDefault": is_os_default,
                "isOnline": True,
                "isDefault": False,
                "isFavorite": False
            })

        if not raw_items:
            return [self.to_device_dict()]

        # メイン出力 (isPrimary: ALL / PC:ALL 一斉発話時に鳴らす代表1台) の決定
        primary_item = None
        if configured_primary_key:
            primary_item = next(
                (item for item in raw_items if item["outputKey"] == configured_primary_key and item["enabled"]),
                None
            )
        if not primary_item:
            primary_item = next(
                (item for item in raw_items if item["isOsDefault"] and item["enabled"]),
                None
            )
        if not primary_item:
            primary_item = next((item for item in raw_items if item["enabled"]), None)
        if not primary_item:
            primary_item = next((item for item in raw_items if item["isOsDefault"]), raw_items[0])

        if primary_item:
            primary_item["isPrimary"] = True

        if include_disabled:
            return raw_items
        return [item for item in raw_items if item["enabled"]]


class ClientSpeakerService:
    """
    Windows / Mac / Linux 等の外部 PC クライアントを
    SSE (Server-Sent Events) 経由でスピーカーとして管理・音声配信するサービス
    """
    def __init__(self):
        self._clients: Dict[str, ClientSpeakerInfo] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        client_id: str,
        name: str,
        ip: str,
        platform: str = "pc",
        outputs: Optional[List[Dict[str, Any]]] = None,
        script_hash: str = ""
    ) -> asyncio.Queue:
        """クライアントの接続を登録し、イベント受信用キューを返却"""
        async with self._lock:
            if client_id in self._clients:
                old = self._clients[client_id]
                log.info(f"Re-registering client speaker: id={client_id}, name='{name}' (was '{old.name}')")
                if not outputs and old.outputs:
                    outputs = old.outputs

            queue: asyncio.Queue = asyncio.Queue(maxsize=50)
            info = ClientSpeakerInfo(
                client_id=client_id,
                name=name or f"PC ({ip})",
                ip=ip,
                platform=platform,
                queue=queue,
                outputs=outputs,
                script_hash=script_hash
            )
            self._clients[client_id] = info
            count = len(self._clients)

        out_cnt = len(info.outputs)
        log.info(
            f"💻 Client speaker connected: '{name}' (id={client_id}, ip={ip}, platform={platform}, outputs={out_cnt}). "
            f"Active client PCs: {count}"
        )
        return queue

    async def update_outputs(
        self,
        client_id: str,
        outputs: List[Dict[str, Any]],
        script_hash: Optional[str] = None
    ) -> bool:
        """接続中のクライアントから報告されたオーディオ出力デバイス一覧を更新"""
        async with self._lock:
            client = self._clients.get(client_id)
            if not client:
                return False
            client.outputs = outputs if isinstance(outputs, list) else []
            if script_hash:
                client.script_hash = str(script_hash)
            client.touch()
        log.info(f"🔊 Updated audio outputs for client '{client.name}' (id={client_id}): {len(client.outputs)} output(s)")
        return True

    async def unregister(self, client_id: str):
        """クライアントの切断を処理"""
        async with self._lock:
            removed = self._clients.pop(client_id, None)
            count = len(self._clients)

        if removed:
            log.info(f"💻 Client speaker disconnected: '{removed.name}' (id={client_id}). Active client PCs: {count}")

    def get_active_devices(self, include_disabled: bool = False) -> List[Dict[str, Any]]:
        """現在接続中の全クライアントスピーカーの出力デバイスリストを取得"""
        clients = list(self._clients.values())
        result: List[Dict[str, Any]] = []
        for c in clients:
            result.extend(c.to_device_dicts(include_disabled=include_disabled))
        return result

    def get_connected_clients_summary(self, server_script_hash: str = "") -> List[Dict[str, Any]]:
        """接続中のPCクライアント単位のサマリーと全出力デバイス一覧を返却"""
        clients = list(self._clients.values())
        summaries: List[Dict[str, Any]] = []
        for c in clients:
            all_outs = c.to_device_dicts(include_disabled=True)
            summaries.append({
                "clientId": c.id,
                "name": c.name,
                "ip": c.ip,
                "platform": c.platform,
                "scriptHash": c.script_hash,
                "isUpToDate": bool(c.script_hash and server_script_hash and c.script_hash == server_script_hash),
                "connectedAt": c.connected_at,
                "lastSeen": c.last_seen,
                "outputs": all_outs
            })
        return summaries

    def find_client(self, query: str) -> Optional[ClientSpeakerInfo]:
        """クエリ（id, name, 'client:<id>', または 'client:<id>@<output_key>'）からクライアントPCを検索"""
        if not query:
            return None
        norm = query.strip()
        for prefix in ("client:", "pc:"):
            if norm.lower().startswith(prefix):
                norm = norm[len(prefix):]
                break

        base_norm = norm.split("@", 1)[0].strip()

        # 1. ID 完全一致
        if base_norm in self._clients:
            return self._clients[base_norm]

        # 2. 名前の完全一致または小文字一致、あるいは出力デバイス名/ID一致
        norm_lower = norm.lower()
        base_lower = base_norm.lower()
        for c in self._clients.values():
            if c.name == base_norm or c.name.lower() == base_lower or c.id.lower() == base_lower:
                return c
            for d in c.to_device_dicts(include_disabled=True):
                if (
                    d.get("id", "").lower() == norm_lower
                    or d.get("ip", "").lower() == f"client:{norm_lower}"
                    or d.get("name", "").lower() == norm_lower
                    or d.get("outputName", "").lower() == norm_lower
                ):
                    return c
        return None

    def find_device_dict(self, query: str) -> Optional[Dict[str, Any]]:
        """
        クエリから特定の出力デバイス辞書（またはPC名指定時はメイン出力のデバイス辞書）を検索して返却
        """
        if not query:
            return None
        norm = query.strip()
        clean_norm = norm
        for prefix in ("client:", "pc:"):
            if clean_norm.lower().startswith(prefix):
                clean_norm = clean_norm[len(prefix):]
                break

        norm_lower = norm.lower()
        clean_lower = clean_norm.lower()

        # 1. 具体的な出力指定 (client:<id>@<output_key> や dev_id や 個別表示名)
        for c in self._clients.values():
            all_devs = c.to_device_dicts(include_disabled=True)
            for d in all_devs:
                d_ip_clean = str(d.get("ip", "")).replace("client:", "")
                if (
                    ("@" in clean_norm and d_ip_clean.lower() == clean_lower)
                    or d.get("id", "").lower() == norm_lower
                    or d.get("name", "").lower() == norm_lower
                    or (d.get("customName") and d["customName"].lower() == norm_lower)
                ):
                    return d

        # 2. PC自体のIDまたは名前で指定された場合 -> そのPCのメイン出力 (isPrimary) を返却
        client = self.find_client(norm)
        if client:
            return client.to_device_dict()

        # 3. 出力デバイス単体名 (例: "Logicool G560") での部分・完全一致
        for c in self._clients.values():
            for d in c.to_device_dicts(include_disabled=False):
                out_name = d.get("outputName", "")
                if out_name and (out_name.lower() == clean_lower or clean_lower in out_name.lower()):
                    return d

        return None

    async def send_play_event(
        self,
        client_id: str,
        audio_url: str,
        text: str = "",
        volume: Optional[float] = None,
        output_key: Optional[str] = None,
        output_name: Optional[str] = None
    ) -> bool:
        """指定されたクライアントスピーカー（および特定出力デバイス）へ音声再生イベントを送信"""
        raw_target = str(client_id or "").strip()
        for prefix in ("client:", "pc:"):
            if raw_target.lower().startswith(prefix):
                raw_target = raw_target[len(prefix):]
                break

        if "@" in raw_target and not output_key:
            base_id, out_k = raw_target.split("@", 1)
            raw_target = base_id.strip()
            output_key = out_k.strip()

        client = self.find_client(raw_target)
        if not client:
            log.warning(f"Client speaker not found: query='{client_id}'")
            return False

        # 出力先デバイス情報の解決（指定がない場合はそのPCのメイン出力 isPrimary を使用）
        resolved_out_key = output_key or ""
        resolved_out_name = output_name or ""
        if client.outputs:
            all_devs = client.to_device_dicts(include_disabled=True)
            matched_dev = None
            if resolved_out_key:
                matched_dev = next((d for d in all_devs if d.get("outputKey") == resolved_out_key), None)
            if not matched_dev:
                matched_dev = next((d for d in all_devs if d.get("isPrimary")), None) or (all_devs[0] if all_devs else None)
            if matched_dev:
                resolved_out_key = matched_dev.get("outputKey", "")
                resolved_out_name = matched_dev.get("outputName", "")

        data_dict: Dict[str, Any] = {
            "audio_url": audio_url,
            "text": text,
            "volume": volume
        }
        if resolved_out_key:
            data_dict["output_key"] = resolved_out_key
        if resolved_out_name:
            data_dict["output_name"] = resolved_out_name

        payload = {
            "event": "play",
            "data": data_dict
        }

        try:
            if client.queue.full():
                try:
                    client.queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            client.queue.put_nowait(payload)
            client.touch()
            out_desc = f" -> output='{resolved_out_name or resolved_out_key}'" if (resolved_out_name or resolved_out_key) else ""
            log.info(f"Sent audio play event to client speaker '{client.name}' (id={client.id}{out_desc})")
            return True
        except Exception as e:
            log.error(f"Failed to send play event to client speaker '{client.name}': {e}")
            return False

    async def broadcast_play_event(
        self,
        audio_url: str,
        text: str = "",
        volume: Optional[float] = None
    ) -> int:
        """全クライアントスピーカー（各PCのメイン出力）へ一斉に音声再生イベントを送信"""
        clients = list(self._clients.values())
        if not clients:
            return 0

        success_count = 0
        for c in clients:
            ok = await self.send_play_event(c.id, audio_url, text=text, volume=volume)
            if ok:
                success_count += 1
        return success_count

    async def broadcast_control_event(
        self,
        event_name: str,
        data: Optional[Dict[str, Any]] = None,
        target_client_id: Optional[str] = None
    ) -> int:
        """接続中のクライアントへ制御イベント (rescan / self_update 等) を送信"""
        clients = list(self._clients.values())
        if target_client_id:
            clients = [c for c in clients if c.id == target_client_id]
        sent = 0
        payload = {"event": event_name, "data": data or {}}
        for c in clients:
            try:
                if not c.queue.full():
                    c.queue.put_nowait(payload)
                    sent += 1
            except Exception:
                pass
        return sent


client_speaker_service = ClientSpeakerService()
