import asyncio
import io
from typing import List, Dict, Any
import edge_tts
from app.services.tts.base import BaseTtsProvider
from app.core.logger import logger

EDGE_VOICES = [
    {"id": "ja-JP-NanamiNeural", "name": "七海 (Nanami) - 女性・標準", "gender": "Female"},
    {"id": "ja-JP-KeitaNeural", "name": "圭太 (Keita) - 男性・標準", "gender": "Male"},
    {"id": "ja-JP-AoiNeural", "name": "碧 (Aoi) - 女性・穏やか", "gender": "Female"},
    {"id": "ja-JP-DaichiNeural", "name": "大地 (Daichi) - 男性・低音", "gender": "Male"},
    {"id": "ja-JP-MayuNeural", "name": "真夕 (Mayu) - 女性・明るい", "gender": "Female"},
    {"id": "ja-JP-NaokiNeural", "name": "直樹 (Naoki) - 男性・案内", "gender": "Male"},
    {"id": "ja-JP-ShioriNeural", "name": "詩織 (Shiori) - 女性・ニュース", "gender": "Female"}
]

class EdgeTtsProvider(BaseTtsProvider):
    """Edge-TTS プロバイダー（標準・無料・常時利用可能）"""

    def __init__(self):
        super().__init__(
            provider_id="edge",
            display_name="Edge-TTS (標準)",
            enabled=True,
            timeout_seconds=5.0,
            default_voice_id="ja-JP-NanamiNeural"
        )

    async def is_available(self) -> bool:
        # Edge TTS はクラウド無料エンドポイントのため常時利用可能
        return True

    async def get_voices(self) -> List[Dict[str, Any]]:
        result = []
        for v in EDGE_VOICES:
            result.append({
                "id": v["id"],  # 互換性のためプレーンなIDも保持しつつ判定可能
                "name": v["name"],
                "gender": v["gender"],
                "provider": self.provider_id,
                "providerName": self.display_name,
                "style": "標準"
            })
        return result

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> bytes:
        raw_id = self.extract_raw_voice_id(voice_id)
        if not raw_id:
            raw_id = self.default_voice_id

        rate_param = rate if rate.startswith(("+", "-")) else f"+{rate}"
        pitch_param = pitch if pitch.startswith(("+", "-")) else f"+{pitch}"

        communicate = edge_tts.Communicate(
            text=text,
            voice=raw_id,
            rate=rate_param,
            pitch=pitch_param
        )

        buffer = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.extend(chunk["data"])

        if not buffer:
            raise RuntimeError(f"Edge TTS returned empty audio for text: {text[:20]}")

        return bytes(buffer)
