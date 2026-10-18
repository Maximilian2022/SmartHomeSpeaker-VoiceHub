import asyncio
import json
import urllib.parse
from typing import List, Dict, Any, Optional
import httpx
from app.services.tts.base import BaseTtsProvider
from app.core.logger import get_logger

log = get_logger("TTS.VoiceEngine")

class VoicevoxFamilyProvider(BaseTtsProvider):
    """VOICEVOX / SHAREVOX / COEIROINK 共通エンジンプロバイダー"""

    def __init__(
        self,
        provider_id: str,
        display_name: str,
        base_url: str = "http://127.0.0.1:50021",
        enabled: bool = False,
        timeout_seconds: float = 5.0,
        default_voice_id: str = "2"
    ):
        super().__init__(
            provider_id=provider_id,
            display_name=display_name,
            enabled=enabled,
            timeout_seconds=timeout_seconds,
            default_voice_id=default_voice_id
        )
        self.base_url = base_url.rstrip("/")
        self._cached_voices: List[Dict[str, Any]] = []

    def update_config(self, base_url: Optional[str] = None, enabled: Optional[bool] = None, timeout_seconds: Optional[float] = None, default_voice_id: Optional[str] = None):
        if base_url is not None:
            self.base_url = base_url.rstrip("/")
        if enabled is not None:
            self.enabled = enabled
        if timeout_seconds is not None:
            self.timeout_seconds = timeout_seconds
        if default_voice_id is not None:
            self.default_voice_id = default_voice_id
        self._cached_voices = []  # キャッシュクリア

    async def is_available(self) -> bool:
        """エンジンがオンラインか確認 (GET /version または GET /speakers)"""
        if not self.enabled:
            return False
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/version")
                return res.status_code == 200
        except Exception:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    res = await client.get(f"{self.base_url}/speakers")
                    return res.status_code == 200
            except Exception:
                return False

    async def initialize_speaker(self, voice_id: str) -> bool:
        """指定したスピーカーモデルをバックグラウンドで事前ロード (VRAM初期化)"""
        if not self.enabled:
            return False
        raw_speaker_id = self.extract_raw_voice_id(voice_id)
        try:
            speaker_int = int(raw_speaker_id)
        except ValueError:
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 1. すでに初期化済みかチェック (SHAREVOX等では常時初期化済みの場合がある)
                try:
                    check_res = await client.get(
                        f"{self.base_url}/is_initialized_speaker",
                        params={"speaker": speaker_int}
                    )
                    if check_res.status_code == 200 and check_res.text.strip().lower() == "true":
                        log.info(f"[{self.display_name}] モデルは既に初期化済みです: speaker={speaker_int}")
                        return True
                except Exception:
                    pass

                # 2. 未初期化の場合のみ初期化リクエストを送信
                log.info(f"[{self.display_name}] モデル事前初期化 (initialize_speaker: {speaker_int}) を開始...")
                res = await client.post(
                    f"{self.base_url}/initialize_speaker",
                    params={"speaker": speaker_int}
                )
                if res.status_code in [200, 204]:
                    log.info(f"[{self.display_name}] モデル事前初期化完了: speaker={speaker_int}")
                    return True
                else:
                    log.warning(f"[{self.display_name}] モデル初期化応答: {res.status_code}")
                    return False
        except Exception as e:
            log.warning(f"[{self.display_name}] モデル事前初期化スキップまたは失敗: {e}")
            return False

    async def get_voices(self) -> List[Dict[str, Any]]:
        """GET /speakers を叩いてキャラクター・スタイル一覧を取得"""
        if not self.enabled:
            return []
        if self._cached_voices:
            return self._cached_voices

        try:
            async with httpx.AsyncClient(timeout=max(self.timeout_seconds, 15.0)) as client:
                res = await client.get(f"{self.base_url}/speakers")
                if res.status_code != 200:
                    log.error(f"[{self.display_name}] /speakers 取得失敗: {res.status_code}")
                    return []
                speakers_data = res.json()

            voices = []
            for spk in speakers_data:
                name = spk.get("name", "Unknown")
                styles = spk.get("styles", [])
                for style in styles:
                    style_id = style.get("id")
                    style_name = style.get("name", "ノーマル")
                    voice_label = f"{name} ({style_name})"
                    eng_type = getattr(self, "engine_type", "voicevox")
                    generic_label = getattr(self, "generic_name", eng_type.upper())
                    voices.append({
                        "id": f"{eng_type}:{style_id}",
                        "name": voice_label,
                        "gender": "Unknown",
                        "provider": eng_type,
                        "providerName": generic_label,
                        "style": style_name
                    })

            self._cached_voices = voices
            return voices
        except Exception as e:
            log.error(f"[{self.display_name}] 話者一覧取得エラー: {type(e).__name__}: {e}")
            return []

    async def _wav_to_mp3(self, wav_bytes: bytes) -> bytes:
        """FFmpeg で WAV バイナリを MP3 にストリーム変換"""
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-i", "pipe:0",
            "-f", "mp3",
            "-b:a", "128k",
            "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate(input=wav_bytes)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg WAV to MP3 conversion failed: {stderr.decode(errors='ignore')}")
        return stdout

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> bytes:
        raw_speaker_id = self.extract_raw_voice_id(voice_id)
        try:
            speaker_int = int(raw_speaker_id)
        except ValueError:
            speaker_int = int(self.extract_raw_voice_id(self.default_voice_id) or "2")

        # 1. 話速スケールの計算 (Edge TTS互換 "+20%" -> 1.2, "-10%" -> 0.9)
        speed_scale = 1.0
        try:
            if rate.endswith("%"):
                rate_num = float(rate.rstrip("%"))
                speed_scale = max(0.5, min(2.0, 1.0 + (rate_num / 100.0)))
        except Exception:
            speed_scale = 1.0

        # 2. 音高スケールの計算 ("+50Hz" 等)
        pitch_scale = 0.0
        try:
            if pitch.endswith("Hz"):
                pitch_num = float(pitch.rstrip("Hz"))
                pitch_scale = max(-0.15, min(0.15, pitch_num / 300.0))
        except Exception:
            pitch_scale = 0.0

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            # 1. audio_query の生成
            query_res = await client.post(
                f"{self.base_url}/audio_query",
                params={"text": text, "speaker": speaker_int}
            )
            if query_res.status_code != 200:
                raise RuntimeError(f"[{self.display_name}] /audio_query failed: {query_res.status_code} - {query_res.text}")

            query_data = query_res.json()
            query_data["speedScale"] = speed_scale
            query_data["pitchScale"] = pitch_scale

            # 2. synthesis の実行
            synth_res = await client.post(
                f"{self.base_url}/synthesis",
                params={"speaker": speaker_int},
                json=query_data,
                headers={"Content-Type": "application/json", "Accept": "audio/wav"}
            )
            if synth_res.status_code != 200:
                raise RuntimeError(f"[{self.display_name}] /synthesis failed: {synth_res.status_code} - {synth_res.text}")

            wav_bytes = synth_res.content

        # 3. WAV -> MP3 変換
        mp3_bytes = await self._wav_to_mp3(wav_bytes)
        log.info(f"[{self.display_name}] 音声合成成功 (speaker={speaker_int}, {len(text)}文字, wav={len(wav_bytes)}B -> mp3={len(mp3_bytes)}B)")
        return mp3_bytes


class VoicevoxProvider(VoicevoxFamilyProvider):
    """VOICEVOX プロバイダー"""
    def __init__(self, base_url: str = "http://127.0.0.1:50021", enabled: bool = False, timeout_seconds: float = 5.0, default_voice_id: str = "voicevox:2"):
        super().__init__(
            provider_id="voicevox",
            display_name="VOICEVOX",
            base_url=base_url,
            enabled=enabled,
            timeout_seconds=timeout_seconds,
            default_voice_id=default_voice_id
        )


class SharevoxProvider(VoicevoxFamilyProvider):
    """SHAREVOX プロバイダー"""
    def __init__(self, base_url: str = "http://127.0.0.1:50025", enabled: bool = False, timeout_seconds: float = 5.0, default_voice_id: str = "sharevox:21"):
        super().__init__(
            provider_id="sharevox",
            display_name="SHAREVOX",
            base_url=base_url,
            enabled=enabled,
            timeout_seconds=timeout_seconds,
            default_voice_id=default_voice_id
        )


class CoeiroinkProvider(VoicevoxFamilyProvider):
    """COEIROINK プロバイダー (v2 API対応)"""
    def __init__(self, base_url: str = "http://127.0.0.1:50031", enabled: bool = False, timeout_seconds: float = 5.0, default_voice_id: str = "coeiroink:140"):
        super().__init__(
            provider_id="coeiroink",
            display_name="COEIROINK",
            base_url=base_url,
            enabled=enabled,
            timeout_seconds=timeout_seconds,
            default_voice_id=default_voice_id
        )
        self._style_to_uuid: Dict[int, str] = {}
        self._fallback_uuid: Optional[str] = None
        self._fallback_style_id: Optional[int] = None

    async def is_available(self) -> bool:
        """COEIROINK v2 稼働チェック (GET /v1/engine_info または GET /)"""
        if not self.enabled:
            return False
        timeout = min(self.timeout_seconds, 3.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.get(f"{self.base_url}/v1/engine_info")
                if res.status_code == 200:
                    return True
        except Exception:
            pass

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.get(f"{self.base_url}/")
                return res.status_code == 200
        except Exception:
            return False

    async def initialize_speaker(self, voice_id: str) -> bool:
        """COEIROINK は専用初期化エンドポイントを持たないため接続確認および話者キャッシュ先読みを実施"""
        avail = await self.is_available()
        if avail and not self._cached_voices:
            try:
                await self.get_voices()
            except Exception:
                pass
        return avail

    async def get_voices(self) -> List[Dict[str, Any]]:
        """GET /v1/speakers を叩いてキャラクター・スタイル一覧を取得"""
        if not self.enabled:
            return []
        if self._cached_voices:
            return self._cached_voices

        try:
            async with httpx.AsyncClient(timeout=max(self.timeout_seconds, 15.0)) as client:
                res = await client.get(f"{self.base_url}/v1/speakers")
                if res.status_code != 200:
                    log.error(f"[{self.display_name}] /v1/speakers 取得失敗: {res.status_code}")
                    return []
                speakers_data = res.json()

            voices = []
            for spk in speakers_data:
                speaker_name = spk.get("speakerName", "Unknown")
                speaker_uuid = spk.get("speakerUuid", "")
                styles = spk.get("styles", [])
                for style in styles:
                    style_id = style.get("styleId")
                    style_name = style.get("styleName", "ノーマル")
                    voice_label = f"{speaker_name} ({style_name})"

                    if style_id is not None:
                        try:
                            s_int = int(style_id)
                            self._style_to_uuid[s_int] = speaker_uuid
                            if self._fallback_uuid is None:
                                self._fallback_uuid = speaker_uuid
                                self._fallback_style_id = s_int
                        except (ValueError, TypeError):
                            pass

                    # 識別子フォーマット: coeiroink:{style_id} または coeiroink:{uuid}:{style_id}
                    voice_key = f"{speaker_uuid}:{style_id}" if speaker_uuid else str(style_id)
                    voices.append({
                        "id": f"coeiroink:{voice_key}",
                        "name": voice_label,
                        "gender": "Unknown",
                        "provider": "coeiroink",
                        "providerName": "COEIROINK",
                        "style": style_name
                    })

            self._cached_voices = voices
            return voices
        except Exception as e:
            log.error(f"[{self.display_name}] 話者一覧取得エラー: {type(e).__name__}: {e}")
            return []

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> bytes:
        raw_id = self.extract_raw_voice_id(voice_id)

        # 1. 話者UUIDとスタイルIDの解決
        speaker_uuid = ""
        style_id = 0
        if ":" in raw_id:
            parts = raw_id.split(":", 1)
            speaker_uuid = parts[0]
            try:
                style_id = int(parts[1])
            except ValueError:
                style_id = self._fallback_style_id or 140
        else:
            try:
                style_id = int(raw_id)
                speaker_uuid = self._style_to_uuid.get(style_id, self._fallback_uuid or "")
            except ValueError:
                style_id = self._fallback_style_id or 140
                speaker_uuid = self._fallback_uuid or ""

        # キャッシュが空でUUIDが取れなかった場合は一度話者一覧を引く
        if not speaker_uuid and not self._style_to_uuid:
            await self.get_voices()
            speaker_uuid = self._style_to_uuid.get(style_id, self._fallback_uuid or "")

        # 2. 話速スケールの計算
        speed_scale = 1.0
        try:
            if rate.endswith("%"):
                rate_num = float(rate.rstrip("%"))
                speed_scale = max(0.5, min(2.0, 1.0 + (rate_num / 100.0)))
        except Exception:
            speed_scale = 1.0

        # 3. POST /v1/predict 呼び出し (WAVを直接返却)
        req_payload = {
            "speakerUuid": speaker_uuid,
            "styleId": style_id,
            "text": text,
            "speedScale": speed_scale
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            res = await client.post(
                f"{self.base_url}/v1/predict",
                json=req_payload,
                headers={"Content-Type": "application/json", "Accept": "audio/wav"}
            )
            if res.status_code != 200:
                raise RuntimeError(f"[{self.display_name}] /v1/predict 失敗: {res.status_code} - {res.text}")
            wav_bytes = res.content

        # 4. WAV -> MP3 変換
        mp3_bytes = await self._wav_to_mp3(wav_bytes)
        return mp3_bytes

