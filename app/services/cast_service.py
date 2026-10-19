import asyncio
import pychromecast
from pychromecast.controllers.media import MediaController
from typing import Dict, Any, Optional
from app.core.logger import get_logger

log = get_logger("Cast")

class CastService:
    def __init__(self):
        self._cast_cache: Dict[str, pychromecast.Chromecast] = {}

    def _get_cast(self, host: str, port: int = 8009) -> Optional[pychromecast.Chromecast]:
        key = f"{host}:{port}"
        if key in self._cast_cache:
            try:
                c = self._cast_cache[key]
                if c.socket_client and c.socket_client.is_connected:
                    return c
            except Exception:
                pass

        try:
            cast = pychromecast.get_chromecast_from_host((host, port, None, None, None), timeout=4.0)
            cast.start()
            cast.wait(timeout=4.0)
            self._cast_cache[key] = cast
            return cast
        except Exception as e:
            log.warning(f"Connect failed to {host}:{port}: {e}")
            return None

    def _sync_play(self, host: str, port: int, media_url: str, volume_level: Optional[float] = None) -> bool:
        cast = self._get_cast(host, port)
        if not cast:
            return False

        try:
            if volume_level is not None:
                try:
                    vol_f = float(volume_level)
                    cast.set_volume(max(0.0, min(1.0, vol_f)), timeout=2.0)
                except (ValueError, TypeError):
                    pass

            mc: MediaController = cast.media_controller
            mc.play_media(media_url, "audio/mp3")
            mc.block_until_active(timeout=4.0)
            log.info(f"Playback started on {host}:{port}: {media_url}")
            return True
        except Exception as e:
            log.error(f"Play failed on {host}:{port}: {e}")
            return False

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
