import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import edge_tts
from app.config import VOICE_DIR, SOUND_DIR

VOICES = [
    {"id": "ja-JP-NanamiNeural", "name": "Nanami (女性・標準)", "gender": "Female"},
    {"id": "ja-JP-KeitaNeural", "name": "Keita (男性・標準)", "gender": "Male"},
    {"id": "ja-JP-AoiNeural", "name": "Aoi (女性・穏やか)", "gender": "Female"},
    {"id": "ja-JP-DaichiNeural", "name": "Daichi (男性・低音)", "gender": "Male"},
    {"id": "ja-JP-MayuNeural", "name": "Mayu (女性・明るい)", "gender": "Female"},
    {"id": "ja-JP-NaokiNeural", "name": "Naoki (男性・案内)", "gender": "Male"},
    {"id": "ja-JP-ShioriNeural", "name": "Shiori (女性・ニュース)", "gender": "Female"}
]

class TtsService:
    def __init__(self):
        self.voice_dir = VOICE_DIR
        self.sound_dir = SOUND_DIR
        self.max_cache_bytes = 200 * 1024 * 1024  # 200MB

    def get_voices(self):
        return VOICES

    def get_cache_stats(self) -> Dict[str, Any]:
        try:
            files = list(self.voice_dir.glob("*.mp3"))
            total_bytes = sum(f.stat().st_size for f in files)
            return {
                "count": len(files),
                "totalBytes": total_bytes,
                "totalMB": f"{total_bytes / 1024 / 1024:.2f}",
                "maxMB": "1024"
            }
        except Exception:
            return {"count": 0, "totalBytes": 0, "totalMB": "0", "maxMB": "1024"}

    def _generate_cache_key(self, text: str, voice: str, rate: str, pitch: str, chime: str) -> str:
        raw = f"{text}_{voice}_{rate}_{pitch}_{chime}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    async def get_audio_duration(self, filepath: Path) -> float:
        """ffprobe を使用して音声ファイルの正確な秒数を取得"""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(filepath)
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            dur = float(stdout.decode().strip())
            return dur
        except Exception as e:
            return 3.0

    async def synthesize(
        self,
        text: str,
        voice: str = "ja-JP-NanamiNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        chime: str = "dingdong"
    ) -> Dict[str, Any]:
        text = text.strip()
        if not text:
            raise ValueError("Text cannot be empty")

        key = self._generate_cache_key(text, voice, rate, pitch, chime)
        filename = f"speech_{key}.mp3"
        final_path = self.voice_dir / filename

        # キャッシュヒット
        if final_path.exists() and final_path.stat().st_size > 0:
            duration = await self.get_audio_duration(final_path)
            return {
                "filename": filename,
                "filepath": str(final_path),
                "duration": duration,
                "cached": True
            }

        # 1. Edge TTS で raw 音声を生成
        raw_filename = f"raw_{key}.mp3"
        raw_path = self.voice_dir / raw_filename

        rate_param = rate if rate.startswith(("+", "-")) else f"+{rate}"
        pitch_param = pitch if pitch.startswith(("+", "-")) else f"+{pitch}"

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate_param,
            pitch=pitch_param
        )
        await communicate.save(str(raw_path))

        # 2. チャイムの結合
        chime_file = self.sound_dir / f"{chime}.mp3"
        if chime != "none" and chime_file.exists():
            # FFmpeg concat フィルターで安全に結合
            cmd = [
                "ffmpeg", "-y",
                "-i", str(chime_file),
                "-i", str(raw_path),
                "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[out]",
                "-map", "[out]",
                "-b:a", "128k",
                str(final_path)
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            if raw_path.exists():
                raw_path.unlink()
        else:
            shutil.move(str(raw_path), str(final_path))

        duration = await self.get_audio_duration(final_path)
        self._cleanup_lru_cache()

        return {
            "filename": filename,
            "filepath": str(final_path),
            "duration": duration,
            "cached": False
        }

    async def adjust_volume(self, source_path_or_url: str, volume_level: float) -> str:
        """FFmpeg で音量を事前調整したキャッシュファイルを生成 (ONVIF/DLNA用)"""
        filename = Path(source_path_or_url.split("?")[0]).name
        input_path = self.voice_dir / filename
        if not input_path.exists():
            return source_path_or_url

        vol_percent = round(volume_level * 100)
        output_filename = f"{input_path.stem}_vol{vol_percent}{input_path.suffix}"
        output_path = self.voice_dir / output_filename

        if output_path.exists() and output_path.stat().st_size > 0:
            return f"http://127.0.0.1:8080/voice/{output_filename}"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-filter:a", f"volume={volume_level:.2f}",
            str(output_path)
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

        if output_path.exists():
            return f"http://127.0.0.1:8080/voice/{output_filename}"
        return f"http://127.0.0.1:8080/voice/{filename}"

    def _cleanup_lru_cache(self):
        try:
            files = list(self.voice_dir.glob("*.mp3"))
            total_size = sum(f.stat().st_size for f in files)
            if total_size > self.max_cache_bytes:
                files.sort(key=lambda f: f.stat().st_atime)
                for f in files:
                    if total_size <= self.max_cache_bytes * 0.7:
                        break
                    size = f.stat().st_size
                    f.unlink(missing_ok=True)
                    total_size -= size
        except Exception as e:
            print(f"[TtsService] Cache cleanup error: {e}")

tts_service = TtsService()
