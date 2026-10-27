import asyncio
import time
from typing import Dict, Any, List, Optional
from app.core.logger import get_logger

log = get_logger("ClientSpeaker")

class ClientSpeakerInfo:
    def __init__(self, client_id: str, name: str, ip: str, platform: str = "pc", queue: Optional[asyncio.Queue] = None):
        self.id = client_id
        self.name = name
        self.ip = ip
        self.platform = platform  # macos, windows, linux, pc
        self.queue = queue or asyncio.Queue(maxsize=50)
        self.connected_at = time.time()
        self.last_seen = time.time()

    def touch(self):
        self.last_seen = time.time()

    def to_device_dict(self) -> Dict[str, Any]:
        """DeviceManager と互換性のあるスピーカー情報辞書を生成"""
        clean_id = self.id.replace(" ", "_").replace(":", "_").replace(".", "_")
        dev_id = f"client_{clean_id}"
        prefix_ip = f"client:{self.id}"
        
        model_name = "PC Speaker"
        p_lower = (self.platform or "").lower()
        if "mac" in p_lower or "darwin" in p_lower:
            model_name = "Mac Speaker"
        elif "win" in p_lower:
            model_name = "Windows Speaker"
        elif "linux" in p_lower:
            model_name = "Linux Speaker"

        return {
            "id": dev_id,
            "name": self.name or f"PC ({self.ip})",
            "ip": prefix_ip,
            "rawIp": self.ip,
            "model": model_name,
            "type": "client",
            "platform": self.platform,
            "isOnline": True,
            "isDefault": False,
            "isFavorite": False
        }


class ClientSpeakerService:
    """
    Windows / Mac / Linux 等の外部 PC クライアントを
    SSE (Server-Sent Events) 経由でスピーカーとして管理・音声配信するサービス
    """
    def __init__(self):
        self._clients: Dict[str, ClientSpeakerInfo] = {}
        self._lock = asyncio.Lock()

    async def register(self, client_id: str, name: str, ip: str, platform: str = "pc") -> asyncio.Queue:
        """クライアントの接続を登録し、イベント受信用キューを返却"""
        async with self._lock:
            # 既存の接続があればキューをクリーンアップ
            if client_id in self._clients:
                old = self._clients[client_id]
                log.info(f"Re-registering client speaker: id={client_id}, name='{name}' (was '{old.name}')")
            
            queue: asyncio.Queue = asyncio.Queue(maxsize=50)
            info = ClientSpeakerInfo(
                client_id=client_id,
                name=name or f"PC ({ip})",
                ip=ip,
                platform=platform,
                queue=queue
            )
            self._clients[client_id] = info
            count = len(self._clients)
        
        log.info(f"💻 Client speaker connected: '{name}' (id={client_id}, ip={ip}, platform={platform}). Active client speakers: {count}")
        return queue

    async def unregister(self, client_id: str):
        """クライアントの切断を処理"""
        async with self._lock:
            removed = self._clients.pop(client_id, None)
            count = len(self._clients)
        
        if removed:
            log.info(f"💻 Client speaker disconnected: '{removed.name}' (id={client_id}). Active client speakers: {count}")

    def get_active_devices(self) -> List[Dict[str, Any]]:
        """現在接続中の全クライアントスピーカーのリストを取得"""
        # 同期読み出し用にスレッドセーフ（辞書のコピー）
        clients = list(self._clients.values())
        return [c.to_device_dict() for c in clients]

    def find_client(self, query: str) -> Optional[ClientSpeakerInfo]:
        """クエリ（id, name, または 'client:<id>'）からクライアントを検索"""
        if not query:
            return None
        norm = query.strip()
        if norm.startswith("client:"):
            norm = norm[len("client:"):]
        
        # 1. ID 完全一致
        if norm in self._clients:
            return self._clients[norm]
        
        # 2. 名前の完全一致または小文字一致
        norm_lower = norm.lower()
        for c in self._clients.values():
            if c.name == norm or c.name.lower() == norm_lower or c.id.lower() == norm_lower:
                return c
        return None

    async def send_play_event(
        self,
        client_id: str,
        audio_url: str,
        text: str = "",
        volume: Optional[float] = None
    ) -> bool:
        """指定されたクライアントスピーカーへ音声再生イベントを送信"""
        client = self.find_client(client_id)
        if not client:
            log.warning(f"Client speaker not found: query='{client_id}'")
            return False

        payload = {
            "event": "play",
            "data": {
                "audio_url": audio_url,
                "text": text,
                "volume": volume
            }
        }

        try:
            if client.queue.full():
                try:
                    client.queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            client.queue.put_nowait(payload)
            client.touch()
            log.info(f"Sent audio play event to client speaker '{client.name}' (id={client.id})")
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
        """全クライアントスピーカーへ一斉に音声再生イベントを送信"""
        clients = list(self._clients.values())
        if not clients:
            return 0

        success_count = 0
        for c in clients:
            ok = await self.send_play_event(c.id, audio_url, text=text, volume=volume)
            if ok:
                success_count += 1
        return success_count


client_speaker_service = ClientSpeakerService()
