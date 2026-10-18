import base64
from typing import List, Dict, Any, Optional
import httpx
from app.services.tts.base import BaseTtsProvider
from app.services.tts.usage_tracker import tts_usage_tracker
from app.core.logger import logger

DEFAULT_GCP_VOICES = [
    {"id": "ja-JP-Neural2-B", "name": "Neural2-B (女性・標準)", "gender": "Female", "type": "neural"},
    {"id": "ja-JP-Neural2-C", "name": "Neural2-C (男性・標準)", "gender": "Male", "type": "neural"},
    {"id": "ja-JP-Wavenet-A", "name": "Wavenet-A (女性・高音)", "gender": "Female", "type": "neural"},
    {"id": "ja-JP-Wavenet-B", "name": "Wavenet-B (女性・落ち着き)", "gender": "Female", "type": "neural"},
    {"id": "ja-JP-Wavenet-C", "name": "Wavenet-C (男性・ニュース)", "gender": "Male", "type": "neural"},
    {"id": "ja-JP-Wavenet-D", "name": "Wavenet-D (男性・低音)", "gender": "Male", "type": "neural"},
    {"id": "ja-JP-Standard-A", "name": "Standard-A (女性・従来)", "gender": "Female", "type": "standard"},
    {"id": "ja-JP-Standard-B", "name": "Standard-B (女性・従来)", "gender": "Female", "type": "standard"},
]

class GcpTtsProvider(BaseTtsProvider):
    """Google Cloud Text-to-Speech API プロバイダー"""

    def __init__(
        self,
        api_key: str = "",
        enabled: bool = False,
        timeout_seconds: float = 5.0,
        default_voice_id: str = "gcp:ja-JP-Neural2-B"
    ):
        super().__init__(
            provider_id="gcp",
            display_name="Google Cloud TTS",
            enabled=enabled,
            timeout_seconds=timeout_seconds,
            default_voice_id=default_voice_id
        )
        self.api_key = api_key
        self._cached_voices: List[Dict[str, Any]] = []

    def update_config(self, api_key: Optional[str] = None, enabled: Optional[bool] = None, timeout_seconds: Optional[float] = None, default_voice_id: Optional[str] = None):
        if api_key is not None:
            self.api_key = api_key
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
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(
                    "https://texttospeech.googleapis.com/v1/voices",
                    params={"languageCode": "ja-JP", "key": self.api_key}
                )
                return res.status_code == 200
        except Exception:
            return False

    async def get_voices(self) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        if self._cached_voices:
            return self._cached_voices

        # API Key がある場合は動的に GCP から日本語ボイス一覧を取得
        if self.api_key:
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    res = await client.get(
                        "https://texttospeech.googleapis.com/v1/voices",
                        params={"languageCode": "ja-JP", "key": self.api_key}
                    )
                    if res.status_code == 200:
                        data = res.json()
                        voices = []
                        for v in data.get("voices", []):
                            v_name = v.get("name", "")
                            if not v_name.startswith("ja-JP-"):
                                continue
                            ssml_gender = v.get("ssmlGender", "NEUTRAL")
                            gender = "Female" if ssml_gender == "FEMALE" else "Male" if ssml_gender == "MALE" else "Unknown"
                            v_type = "standard" if "Standard" in v_name else "neural"
                            voices.append({
                                "id": self.format_voice_id(v_name),
                                "name": f"{v_name.replace('ja-JP-', '')} ({v_type.capitalize()})",
                                "gender": gender,
                                "provider": self.provider_id,
                                "providerName": self.display_name,
                                "style": v_type
                            })
                        if voices:
                            self._cached_voices = voices
                            return voices
            except Exception as e:
                logger.warning(f"[GcpTtsProvider] GCP API 話者動的取得失敗、プリセットを使用: {e}")

        # フォールバックプリセット
        preset = []
        for v in DEFAULT_GCP_VOICES:
            preset.append({
                "id": self.format_voice_id(v["id"]),
                "name": v["name"],
                "gender": v["gender"],
                "provider": self.provider_id,
                "providerName": self.display_name,
                "style": v["type"]
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
            raise ValueError("[GcpTtsProvider] GCP API Key が設定されていません")

        raw_voice_name = self.extract_raw_voice_id(voice_id)
        if not raw_voice_name:
            raw_voice_name = self.extract_raw_voice_id(self.default_voice_id) or "ja-JP-Neural2-B"

        # 話速スケール (0.25 〜 4.0, 標準 1.0)
        speaking_rate = 1.0
        try:
            if rate.endswith("%"):
                rate_num = float(rate.rstrip("%"))
                speaking_rate = max(0.5, min(2.0, 1.0 + (rate_num / 100.0)))
        except Exception:
            speaking_rate = 1.0

        # 音高スケール (-20.0 〜 20.0 semitones)
        pitch_val = 0.0
        try:
            if pitch.endswith("Hz"):
                pitch_num = float(pitch.rstrip("Hz"))
                pitch_val = max(-10.0, min(10.0, pitch_num / 20.0))
        except Exception:
            pitch_val = 0.0

        model_type = "standard" if "Standard" in raw_voice_name else "neural"

        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "ja-JP",
                "name": raw_voice_name
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": speaking_rate,
                "pitch": pitch_val
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            res = await client.post(
                "https://texttospeech.googleapis.com/v1/text:synthesize",
                params={"key": self.api_key},
                json=payload
            )
            if res.status_code != 200:
                raise RuntimeError(f"[GcpTtsProvider] GCP Text-to-Speech エラー: {res.status_code} - {res.text}")

            res_data = res.json()
            audio_content_b64 = res_data.get("audioContent")
            if not audio_content_b64:
                raise RuntimeError(f"[GcpTtsProvider] audioContent が空です")

        # 文字数の消費を記録
        tts_usage_tracker.record_usage("gcp", len(text), model_type)

        return base64.b64decode(audio_content_b64)
