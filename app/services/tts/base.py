from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseTtsProvider(ABC):
    """外部音声エンジン (TTS) プロバイダーの基底抽象クラス"""

    def __init__(
        self,
        provider_id: str,
        display_name: str,
        enabled: bool = False,
        timeout_seconds: float = 5.0,
        default_voice_id: str = ""
    ):
        self.provider_id = provider_id
        self.display_name = display_name
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self.default_voice_id = default_voice_id

    @abstractmethod
    async def is_available(self) -> bool:
        """エンジンの接続状態（ヘルスチェック）を確認"""
        pass

    @abstractmethod
    async def get_voices(self) -> List[Dict[str, Any]]:
        """利用可能な話者一覧を取得。
        各要素: {
            "id": "voicevox:2",
            "name": "四国めたん (ノーマル)",
            "gender": "Female" | "Male" | "Unknown",
            "provider": "voicevox",
            "providerName": "VOICEVOX",
            "style": "ノーマル"
        }
        """
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> bytes:
        """テキストから音声バイナリ（MP3 または WAV）を合成して返却"""
        pass

    async def initialize_speaker(self, voice_id: str) -> bool:
        """モデルの事前ロード（プリロード/ウォームアップ）。
        VOICEVOX系などのコールドスタート遅延を防止するために使用。デフォルトはTrueを返却。
        """
        return True

    def format_voice_id(self, raw_id: str) -> str:
        """プロバイダー固有のプレフィックス付き ID に正規化 (例: voicevox:2)"""
        if raw_id.startswith(f"{self.provider_id}:"):
            return raw_id
        return f"{self.provider_id}:{raw_id}"

    def extract_raw_voice_id(self, prefixed_id: str) -> str:
        """プレフィックスを除去した内部用 ID を取得 (例: voicevox:2 -> 2)"""
        prefix = f"{self.provider_id}:"
        if prefixed_id.startswith(prefix):
            return prefixed_id[len(prefix):]
        return prefixed_id
