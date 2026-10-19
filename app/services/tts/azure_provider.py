import re
import xml.sax.saxutils
from typing import List, Dict, Any, Optional
import httpx
from app.services.tts.base import BaseTtsProvider
from app.services.tts.usage_tracker import tts_usage_tracker
from app.core.logger import get_logger

log = get_logger("TTS.Azure")

DEFAULT_AZURE_VOICES = [
    {"id": "ja-JP-NanamiNeural", "name": "七海 (Nanami) - 女性・標準", "gender": "Female"},
    {"id": "ja-JP-KeitaNeural", "name": "圭太 (Keita) - 男性・標準", "gender": "Male"},
    {"id": "ja-JP-AoiNeural", "name": "碧 (Aoi) - 女性・穏やか", "gender": "Female"},
    {"id": "ja-JP-DaichiNeural", "name": "大地 (Daichi) - 男性・低音", "gender": "Male"},
    {"id": "ja-JP-MayuNeural", "name": "真夕 (Mayu) - 女性・明るい", "gender": "Female"},
    {"id": "ja-JP-NaokiNeural", "name": "直樹 (Naoki) - 男性・案内", "gender": "Male"},
    {"id": "ja-JP-ShioriNeural", "name": "詩織 (Shiori) - 女性・ニュース", "gender": "Female"}
]

class AzureTtsProvider(BaseTtsProvider):
    """Azure Cognitive Services Speech REST API プロバイダー"""

    def __init__(
        self,
        api_key: str = "",
        region: str = "japaneast",
        enabled: bool = False,
        timeout_seconds: float = 5.0,
        default_voice_id: str = "azure:ja-JP-NanamiNeural"
    ):
        super().__init__(
            provider_id="azure",
            display_name="Azure Speech",
            enabled=enabled,
            timeout_seconds=timeout_seconds,
            default_voice_id=default_voice_id
        )
        self.api_key = api_key
        self.region = self._validate_region(region)
        self._cached_voices: List[Dict[str, Any]] = []

    @staticmethod
    def _validate_region(reg: Optional[str]) -> str:
        """SSRF防止: 英数字およびハイフンのみを許可 (デフォルト: japaneast)"""
        val = (reg or "japaneast").strip().lower()
        if not re.match(r"^[a-z0-9\-]+$", val):
            log.warning(f"[AzureTtsProvider] 無効なリージョン指定 '{reg}'。デフォルト 'japaneast' を使用します")
            return "japaneast"
        return val

    def update_config(self, api_key: Optional[str] = None, region: Optional[str] = None, enabled: Optional[bool] = None, timeout_seconds: Optional[float] = None, default_voice_id: Optional[str] = None):
        if api_key is not None:
            self.api_key = api_key
        if region is not None:
            self.region = self._validate_region(region)
        if enabled is not None:
            self.enabled = enabled
        if timeout_seconds is not None:
            self.timeout_seconds = timeout_seconds
        if default_voice_id is not None:
            self.default_voice_id = default_voice_id
        self._cached_voices = []

    async def is_available(self) -> bool:
        if not self.enabled or not self.api_key:
            return False
        try:
            safe_reg = self._validate_region(self.region)
            url = f"https://{safe_reg}.tts.speech.microsoft.com/cognitiveservices/voices/list"
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(url, headers={"Ocp-Apim-Subscription-Key": self.api_key})
                return res.status_code == 200
        except Exception:
            return False

    async def get_voices(self) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        if self._cached_voices:
            return self._cached_voices

        # API Key がある場合は動的に Azure API から取得
        if self.api_key:
            try:
                safe_reg = self._validate_region(self.region)
                url = f"https://{safe_reg}.tts.speech.microsoft.com/cognitiveservices/voices/list"
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    res = await client.get(url, headers={"Ocp-Apim-Subscription-Key": self.api_key})
                    if res.status_code == 200:
                        data = res.json()
                        voices = []
                        for v in data:
                            locale = v.get("Locale", "")
                            if locale != "ja-JP":
                                continue
                            short_name = v.get("ShortName", "")
                            gender = v.get("Gender", "Unknown")
                            local_name = v.get("LocalName", short_name.replace("ja-JP-", "").replace("Neural", ""))
                            voices.append({
                                "id": self.format_voice_id(short_name),
                                "name": f"{local_name} ({short_name.replace('ja-JP-', '')})",
                                "gender": gender,
                                "provider": self.provider_id,
                                "providerName": self.display_name,
                                "style": "Neural"
                            })
                        if voices:
                            self._cached_voices = voices
                            return voices
            except Exception as e:
                log.warning(f"[AzureTtsProvider] Azure API 話者動的取得失敗、プリセットを使用: {e}")

        # フォールバックプリセット
        preset = []
        for v in DEFAULT_AZURE_VOICES:
            preset.append({
                "id": self.format_voice_id(v["id"]),
                "name": v["name"],
                "gender": v["gender"],
                "provider": self.provider_id,
                "providerName": self.display_name,
                "style": "Neural"
            })
        self._cached_voices = preset
        return preset

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> bytes:
        if not self.api_key:
            raise ValueError("[AzureTtsProvider] Azure Speech API Key が設定されていません")

        raw_voice_name = self.extract_raw_voice_id(voice_id)
        if not raw_voice_name:
            raw_voice_name = self.extract_raw_voice_id(self.default_voice_id) or "ja-JP-NanamiNeural"

        escaped_text = xml.sax.saxutils.escape(text)
        rate_param = rate if rate.startswith(("+", "-")) else f"+{rate}"
        pitch_param = pitch if pitch.startswith(("+", "-")) else f"+{pitch}"

        ssml = f"""<speak version='1.0' xml:lang='ja-JP'>
    <voice xml:lang='ja-JP' name='{raw_voice_name}'>
        <prosody rate='{rate_param}' pitch='{pitch_param}'>
            {escaped_text}
        </prosody>
    </voice>
</speak>"""

        safe_reg = self._validate_region(self.region)
        url = f"https://{safe_reg}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
            "User-Agent": "SmartHomeSpeaker-VoiceHub"
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            res = await client.post(url, headers=headers, content=ssml.encode("utf-8"))
            if res.status_code != 200:
                if res.status_code == 429:
                    log.warning(f"[Azure Speech] HTTP 429 クォータ超過 (月間無料枠上限到達)。フォールバックが必要です: {res.text}")
                elif res.status_code == 401:
                    log.error(f"[Azure Speech] HTTP 401 認証失敗。API Key またはリージョンを確認してください: {res.text}")
                else:
                    log.warning(f"[Azure Speech] HTTP {res.status_code} 音声合成エラー: {res.text}")
                raise RuntimeError(f"[AzureTtsProvider] Azure Speech エラー: {res.status_code} - {res.text}")
            audio_bytes = res.content

        # 文字数の消費を記録 (Azure Neural)
        tts_usage_tracker.record_usage("azure", len(text), "neural")
        log.info(f"[Azure Speech] 音声合成成功 (voice={raw_voice_name}, {len(text)}文字, size={len(audio_bytes)}B)")

        return audio_bytes
