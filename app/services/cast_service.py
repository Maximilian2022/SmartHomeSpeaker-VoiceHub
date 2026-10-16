import asyncio
import pychromecast
from pychromecast.controllers.media import MediaController
from typing import Dict, Any, Optional

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
            print(f"[CastService] Connect failed to {host}:{port}: {e}")
            return None

    def _sync_play(self, host: str, port: int, media_url: str, volume_level: Optional[float] = None) -> bool:
        cast = self._get_cast(host, port)
        if not cast:
            return False

        try:
            if volume_level is not None:
                cast.set_volume(max(0.0, min(1.0, float(volume_level))), timeout=2.0)

            mc: MediaController = cast.media_controller
            mc.play_media(media_url, "audio/mp3")
            mc.block_until_active(timeout=4.0)
            print(f"[CastService] Playback started on {host}:{port}: {media_url}")
            return True
        except Exception as e:
            print(f"[CastService] Play failed on {host}:{port}: {e}")
            return False

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
