import asyncio
import threading
import pychromecast
from pychromecast.controllers.media import MediaController
from typing import Dict, Any, Optional
from app.core.logger import get_logger

log = get_logger("Cast")

class CastService:
    def __init__(self):
        self._cast_cache: Dict[str, pychromecast.Chromecast] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _safe_disconnect(cast: Optional[pychromecast.Chromecast]):
        """Chromecast インスタンスのソケットスレッドを確実に終了・解放する"""
        if not cast:
            return
        try:
            cast.disconnect(timeout=0.5)
        except Exception:
            pass

    def _get_cast(self, host: str, port: int = 8009) -> Optional[pychromecast.Chromecast]:
        key = f"{host}:{port}"
        with self._lock:
            if key in self._cast_cache:
                try:
                    c = self._cast_cache[key]
                    if c.socket_client and c.socket_client.is_connected:
                        return c
                except Exception:
                    c = self._cast_cache.get(key)
                self._cast_cache.pop(key, None)
                self._safe_disconnect(c)

        is_group = (port != 8009)
        conn_timeout = 3.0 if is_group else 3.5
        cast = None
        try:
            # tries=1 により接続失敗時のバックグラウンド無限リトライスレッド蓄積を防止
            cast = pychromecast.get_chromecast_from_host(
                (host, port, None, None, None),
                tries=1,
                retry_wait=1.0,
                timeout=conn_timeout
            )
            cast.start()
            cast.wait(timeout=conn_timeout)
            with self._lock:
                old = self._cast_cache.pop(key, None)
                if old and old is not cast:
                    self._safe_disconnect(old)
                self._cast_cache[key] = cast
            return cast
        except Exception as e:
            self._safe_disconnect(cast)
            with self._lock:
                self._cast_cache.pop(key, None)
            log.warning(f"Connect failed to {host}:{port}: {e}")
            return None

    def purge_cache(self, host: str, port: int = 8009):
        key = f"{host}:{port}"
        with self._lock:
            cast = self._cast_cache.pop(key, None)
        self._safe_disconnect(cast)

    def _sync_play(self, host: str, port: int, media_url: str, volume_level: Optional[float] = None) -> bool:
        key = f"{host}:{port}"
        cast = self._get_cast(host, port)
        if not cast:
            return False

        try:
            if volume_level is not None:
                try:
                    vol_f = max(0.0, min(1.0, float(volume_level)))
                    cast.set_volume(vol_f, timeout=2.0)
                except Exception as ve:
                    # 音量設定タイムアウト等が発生しても音声再生自体は中断せず続行する
                    log.warning(f"Volume adjustment skipped on {host}:{port}: {ve}")

            mc: MediaController = cast.media_controller
            mc.play_media(media_url, "audio/mpeg")
            mc.block_until_active(timeout=4.0)
            log.info(f"Playback started on {host}:{port}: {media_url}")
            return True
        except Exception as e:
            with self._lock:
                popped = self._cast_cache.pop(key, None)
            self._safe_disconnect(popped or cast)
            log.error(f"Play failed on {host}:{port}: {e}")
            return False

    def _sync_stop(self, host: str, port: int, expected_media_url: Optional[str] = None) -> bool:
        """現在再生中のメディアを即停止する（VoiceHub配信音声以外を誤停止しないよう可能な範囲で照合）"""
        key = f"{host}:{port}"
        cast = None
        with self._lock:
            c = self._cast_cache.get(key)
            try:
                if c and c.socket_client and c.socket_client.is_connected:
                    cast = c
            except Exception:
                cast = None
        if not cast:
            cast = self._get_cast(host, port)
        if not cast:
            return False
        try:
            mc: MediaController = cast.media_controller
            status = getattr(mc, "status", None)
            content_id = getattr(status, "content_id", None) if status else None
            # 既に他のコンテンツ (YouTube / Spotify 等) を再生中なら停止しない
            if expected_media_url and content_id and expected_media_url != content_id:
                c_str = str(content_id)
                if "/voice/" not in c_str and "/sound/" not in c_str:
                    log.info(f"Skip stop on {host}:{port}: active content_id does not match VoiceHub ({content_id})")
                    return False
            mc.stop()
            log.info(f"⏹️ Stopped Cast playback on {host}:{port}")
            return True
        except Exception as e:
            log.warning(f"Stop failed on {host}:{port}: {e}")
            return False

    async def stop_playback(self, host: str, port: int = 8009, expected_media_url: Optional[str] = None) -> bool:
        return await asyncio.to_thread(self._sync_stop, host, port, expected_media_url)

    def _sync_set_volume(self, host: str, port: int, volume_level: float) -> bool:
        cast = self._get_cast(host, port)
        if not cast:
            return False
        try:
            vol_f = max(0.0, min(1.0, float(volume_level)))
            cast.set_volume(vol_f, timeout=2.0)
            log.info(f"Set volume to {vol_f*100:.0f}% on {host}:{port}")
            return True
        except Exception as e:
            log.error(f"Set volume failed on {host}:{port}: {e}")
            return False

    async def set_volume(self, host: str, port: int = 8009, volume_level: float = 0.5) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_set_volume, host, port, volume_level)

    async def play_audio(
        self,
        host: str,
        port: int = 8009,
        media_url: str = "",
        volume_level: Optional[float] = None
    ) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_play, host, port, media_url, volume_level)

cast_service = CastService()
