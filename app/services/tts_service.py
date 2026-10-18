import asyncio
import hashlib
import io
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.config import VOICE_DIR, SOUND_DIR
from app.core.logger import get_logger
from app.services.settings_service import settings_manager

log = get_logger("TTS")
from app.services.tts import (
    BaseTtsProvider,
    EdgeTtsProvider,
    VoicevoxFamilyProvider,
    VoicevoxProvider,
    SharevoxProvider,
    CoeiroinkProvider,
    GcpTtsProvider,
    AzureTtsProvider,
    tts_usage_tracker
)

class TtsService:
    """すべての TTS プロバイダーを統合管理し、フォールバックおよび緊急最速並行生成を提供するファサードサービス"""

    def __init__(self):
        self.voice_dir = VOICE_DIR
        self.sound_dir = SOUND_DIR
        self.max_cache_bytes = 200 * 1024 * 1024  # 200MB

        # 静的プロバイダーのインスタンス化
        self.edge_provider = EdgeTtsProvider()
        self.azure_provider = AzureTtsProvider()
        self.gcp_provider = GcpTtsProvider()

        # 動的ローカル音声エンジンプロバイダーリスト
        self.voice_engine_providers: List[BaseTtsProvider] = []

        # プレフィックス別プロバイダーマップ
        self.providers: Dict[str, BaseTtsProvider] = {
            "edge": self.edge_provider,
            "azure": self.azure_provider,
            "gcp": self.gcp_provider
        }

        # 設定のロードと適用
        self.sync_settings()

    def is_azure_active(self) -> bool:
        """Azure Speech が有効かつ API キーが設定されているかを判定"""
        return bool(self.azure_provider.enabled and self.azure_provider.api_key.strip())

    def sync_settings(self):
        """settings_manager の設定を各プロバイダーに反映（動的エンジン群の追加・更新・削除を含む）"""
        conf = settings_manager.get().get("tts_providers", {})

        # 1. Azure
        az = conf.get("azure", {})
        self.azure_provider.update_config(
            api_key=az.get("apiKey", ""),
            region=az.get("region", "japaneast"),
            enabled=bool(az.get("enabled", False)),
            timeout_seconds=float(az.get("timeoutSeconds", 5.0)),
            default_voice_id=az.get("defaultVoiceId", "azure:ja-JP-NanamiNeural")
        )

        # 2. GCP
        gcp = conf.get("gcp", {})
        self.gcp_provider.update_config(
            api_key=gcp.get("apiKey", ""),
            enabled=bool(gcp.get("enabled", False)),
            timeout_seconds=float(gcp.get("timeoutSeconds", 5.0)),
            default_voice_id=gcp.get("defaultVoiceId", "gcp:ja-JP-Neural2-B"),
            fallback_on_quota_near_limit=bool(gcp.get("fallbackOnQuotaNearLimit", True))
        )

        # 3. 動的ローカル音声エンジン群 (voice_engines) の反映
        self.voice_engine_providers.clear()
        self.providers = {
            "edge": self.edge_provider,
            "azure": self.azure_provider,
            "gcp": self.gcp_provider
        }

        v_engines = conf.get("voice_engines", [])
        for eng in v_engines:
            if not isinstance(eng, dict):
                continue
            e_id = str(eng.get("id") or "").strip()
            if not e_id:
                continue
            e_type = str(eng.get("type") or "voicevox").lower().strip()
            e_name = str(eng.get("name") or e_type.upper()).strip()
            e_url = str(eng.get("baseUrl") or "http://127.0.0.1:50021").rstrip("/")
            e_enabled = bool(eng.get("enabled", False))
            e_timeout = float(eng.get("timeoutSeconds", 5.0))
            e_def_voice = eng.get("defaultVoiceId") or f"{e_id}:2"

            if e_type == "coeiroink":
                p = CoeiroinkProvider(
                    base_url=e_url,
                    enabled=e_enabled,
                    timeout_seconds=e_timeout,
                    default_voice_id=e_def_voice
                )
            elif e_type == "sharevox":
                p = SharevoxProvider(
                    base_url=e_url,
                    enabled=e_enabled,
                    timeout_seconds=e_timeout,
                    default_voice_id=e_def_voice
                )
            else:
                p = VoicevoxFamilyProvider(
                    provider_id=e_id,
                    display_name=e_name,
                    base_url=e_url,
                    enabled=e_enabled,
                    timeout_seconds=e_timeout,
                    default_voice_id=e_def_voice
                )

            p.provider_id = e_id
            p.display_name = e_name
            p.engine_type = e_type
            p.is_gpu = bool(eng.get("isGpu", False))
            p.latency_ms = eng.get("latencyMs")
            self.providers[e_id] = p
            self.voice_engine_providers.append(p)

        # 同一種別（voicevox / sharevox / coeiroink）の複数登録時における GPU / 高速機優先選定
        for etype in ["voicevox", "sharevox", "coeiroink"]:
            matching = [p for p in self.voice_engine_providers if getattr(p, "engine_type", "") == etype and p.enabled]
            if matching:
                # GPU優先 (is_gpu: True > False), レイテンシが小さい順 (Noneは最後)
                sorted_matching = sorted(
                    matching,
                    key=lambda ep: (not getattr(ep, "is_gpu", False), getattr(ep, "latency_ms", 9999) if getattr(ep, "latency_ms") is not None else 9999)
                )
                self.providers[etype] = sorted_matching[0]
            elif f"{etype}_default" in self.providers:
                self.providers[etype] = self.providers[f"{etype}_default"]

        # バックグラウンドで有効なローカルモデルの事前初期化をトリガー（イベントループ稼働時のみ）
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.warmup_enabled_speakers())
        except RuntimeError:
            pass

    async def warmup_enabled_speakers(self):
        """有効な音声エンジンの推奨デフォルトモデルをバックグラウンド事前初期化"""
        for p in self.voice_engine_providers:
            if p.enabled:
                try:
                    await p.initialize_speaker(p.default_voice_id)
                    await p.get_voices()
                except Exception as e:
                    log.warning(f"[TtsService] {p.display_name} 事前初期化スキップ: {e}")

    def resolve_provider(self, voice_id: Optional[str]) -> Tuple[BaseTtsProvider, str]:
        """voice_id から適切なプロバイダーと正規化ボイスIDを特定。
        Azure有効時は Edge-TTS を通常選択から隠し、プレーンIDも Azure へルーティングする。
        """
        azure_active = self.is_azure_active()

        if not voice_id:
            if azure_active:
                return self.azure_provider, self.azure_provider.default_voice_id
            return self.edge_provider, self.edge_provider.default_voice_id

        # プレフィックス判定
        for pid, provider in self.providers.items():
            if voice_id.startswith(f"{pid}:"):
                return provider, voice_id

        # プレフィックスなしの場合 (Nanami 等)
        if azure_active:
            # Azure 有効時は Azure の同名ボイスへマッピング
            mapped_azure = f"azure:{voice_id}"
            return self.azure_provider, mapped_azure

        # Edge-TTS (標準)
        return self.edge_provider, voice_id

    async def get_voices(self, include_edge_fallback: bool = False) -> List[Dict[str, Any]]:
        """有効なすべてのプロバイダーから話者一覧を非同期収集。
        Azure有効時は、Edge-TTS を選択肢から除外（いざというときの最終手段として待機）。
        """
        self.sync_settings()
        azure_active = self.is_azure_active()

        tasks = []
        # プロバイダーの重複を避ける（エイリアス対策）
        unique_providers = list({id(p): p for p in self.providers.values()}.values())

        for p in unique_providers:
            if p.provider_id == "edge":
                # Azure が有効な場合は Edge-TTS を話者選択から除外（明示的指定がない限り）
                if not azure_active or include_edge_fallback:
                    tasks.append(p.get_voices())
            elif p.enabled:
                tasks.append(p.get_voices())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_voices: List[Dict[str, Any]] = []
        seen_voice_keys = set()
        for r in results:
            if isinstance(r, list):
                for v in r:
                    vid = v.get("id")
                    vkey = f"{v.get('provider')}:{v.get('name')}"
                    if vid and vid not in seen_voice_keys and vkey not in seen_voice_keys:
                        seen_voice_keys.add(vid)
                        seen_voice_keys.add(vkey)
                        all_voices.append(v)
            elif isinstance(r, Exception):
                log.error(f"[TtsService] 話者取得タスク例外: {r}")

        return all_voices

    def get_fallback_candidates(self, exclude_provider_id: Optional[str] = None) -> List[Tuple[BaseTtsProvider, str]]:
        """段階的フォールバック（Cascading Fallback）試行リストを優先順序で生成:
        1. Azure Speech (有効な場合)
        2. Google Cloud TTS (有効な場合)
        3. 有効なローカル音声エンジン群 (VOICEVOX / SHAREVOX / COEIROINK 等)
        4. 最終手段: Edge-TTS
        """
        candidates: List[Tuple[BaseTtsProvider, str]] = []
        seen_pids = set()
        if exclude_provider_id:
            seen_pids.add(exclude_provider_id)

        # 1. Azure Speech
        if self.is_azure_active() and self.azure_provider.provider_id not in seen_pids:
            candidates.append((self.azure_provider, self.azure_provider.default_voice_id))
            seen_pids.add(self.azure_provider.provider_id)

        # 2. GCP Cloud TTS
        if self.gcp_provider.enabled and bool(self.gcp_provider.api_key.strip()) and self.gcp_provider.provider_id not in seen_pids:
            # 無料枠9割到達時の課金防止フォールバック判定
            if self.gcp_provider.fallback_on_quota_near_limit and self.gcp_provider.is_quota_near_limit("neural", threshold=0.9):
                log.warning("[TtsService] GCP Cloud TTS の当月無料枠が9割に達しているため、課金防止安全ガードによりフォールバック候補から除外します")
            else:
                candidates.append((self.gcp_provider, self.gcp_provider.default_voice_id))
                seen_pids.add(self.gcp_provider.provider_id)

        # 3. 有効なローカル音声エンジン群 (GPU搭載機・高速応答機を最優先にソート)
        sorted_engines = sorted(
            self.voice_engine_providers,
            key=lambda ep: (not getattr(ep, "is_gpu", False), getattr(ep, "latency_ms", 9999) if getattr(ep, "latency_ms") is not None else 9999)
        )
        for p in sorted_engines:
            if p.enabled and p.provider_id not in seen_pids:
                candidates.append((p, p.default_voice_id))
                seen_pids.add(p.provider_id)

        # 4. 最終手段: Edge-TTS
        if self.edge_provider.provider_id not in seen_pids:
            candidates.append((self.edge_provider, self.edge_provider.default_voice_id))
            seen_pids.add(self.edge_provider.provider_id)

        return candidates

    def get_providers_status(self) -> Dict[str, Any]:
        """プロバイダー設定および当月文字数使用状況を取得"""
        conf = settings_manager.get().get("tts_providers", {})
        stats = tts_usage_tracker.get_stats()

        providers_info = {}
        for pid, p in self.providers.items():
            sub_conf = conf.get(pid, {})
            providers_info[pid] = {
                "id": pid,
                "name": p.display_name,
                "enabled": p.enabled,
                "timeoutSeconds": p.timeout_seconds,
                "defaultVoiceId": p.default_voice_id,
                "config": sub_conf
            }
            if pid == "gcp":
                providers_info[pid]["fallbackOnQuotaNearLimit"] = getattr(p, "fallback_on_quota_near_limit", True)

        return {
            "success": True,
            "urgentFastest": conf.get("urgentFastest", True),
            "isAzureActive": self.is_azure_active(),
            "providers": providers_info,
            "voice_engines": conf.get("voice_engines", []),
            "usage": stats
        }

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
        except Exception:
            return 3.0

    async def _synthesize_raw(
        self,
        text: str,
        voice: str = "ja-JP-NanamiNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        urgent: bool = False
    ) -> Tuple[bytes, str, bool]:
        """音声バイナリを合成。緊急速報時の並行最速生成、および多段フォールバックパイプライン
        （指定エンジン → Azure → GCP → VoiceEngines → 最終手段 Edge-TTS）を含む。
        返却: (audio_bytes, used_voice_id, was_fallback)
        """
        conf = settings_manager.get().get("tts_providers", {})
        urgent_fastest = conf.get("urgentFastest", True)
        azure_active = self.is_azure_active()

        # 1. 緊急速報 (urgent) かつ 最速生成が有効な場合
        if urgent and urgent_fastest:
            # Azure有効時は Edge-TTS を除外して待機させ、正規エンジンのみで最速レースを実施
            active_providers = [
                p for p in self.providers.values()
                if p.enabled and (not azure_active or p.provider_id != "edge")
            ]
            # GCP 9割到達ガード（並行最速レースからも除外）
            if self.gcp_provider.fallback_on_quota_near_limit and self.gcp_provider.is_quota_near_limit("neural", threshold=0.9):
                active_providers = [p for p in active_providers if p.provider_id != "gcp"]

            # ユニーク化
            active_providers = list({id(p): p for p in active_providers}.values())

            if len(active_providers) > 1:
                log.info(f"[TtsService] 緊急速報最速並行生成 (Fastest Wins) 開始: 対象プロバイダー {len(active_providers)}件")
                tasks = []
                provider_map = {}
                for p in active_providers:
                    target_voice = p.default_voice_id
                    t = asyncio.create_task(p.synthesize(text, target_voice, rate, pitch))
                    tasks.append(t)
                    provider_map[t] = (p, target_voice)

                while tasks:
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for completed_task in done:
                        try:
                            audio_bytes = completed_task.result()
                            if audio_bytes and len(audio_bytes) > 0:
                                p, v_id = provider_map[completed_task]
                                log.info(f"[TtsService] ★ 最速生成完了プロバイダー: {p.display_name} ({v_id})")
                                for pt in pending:
                                    pt.cancel()
                                return audio_bytes, v_id, False
                        except Exception as e:
                            p, v_id = provider_map[completed_task]
                            log.warning(f"[TtsService] 最速並行生成タスク失敗 ({p.display_name}): {e}")
                    tasks = list(pending)

                log.warning("[TtsService] 最速並行生成タスクがすべて失敗したため、段階的フォールバックを開始します")

        # 2. 一次プロバイダー特定と合成試行
        provider, resolved_voice = self.resolve_provider(voice)
        primary_failed = False

        # GCP の無料枠9割到達チェック（課金防止安全ガード）
        if provider.provider_id == "gcp" and self.gcp_provider.fallback_on_quota_near_limit:
            raw_voice = self.gcp_provider.extract_raw_voice_id(resolved_voice)
            m_type = "standard" if "Standard" in raw_voice else "neural"
            if self.gcp_provider.is_quota_near_limit(m_type, threshold=0.9):
                log.warning(
                    f"[TtsService] GCP Cloud TTS ({m_type}) の当月無料枠が9割に達しているため、課金防止安全ガードによりスキップし段階的フォールバックへ移行します"
                )
                primary_failed = True

        if not primary_failed and (provider.enabled or provider.provider_id == "edge"):
            try:
                audio = await asyncio.wait_for(
                    provider.synthesize(text, resolved_voice, rate, pitch),
                    timeout=provider.timeout_seconds
                )
                if audio and len(audio) > 0:
                    return audio, resolved_voice, False
                primary_failed = True
            except asyncio.TimeoutError:
                log.warning(f"[TtsService] 一次プロバイダー {provider.display_name} がタイムアウト ({provider.timeout_seconds}s) しました")
                primary_failed = True
            except Exception as e:
                log.warning(f"[TtsService] 一次プロバイダー {provider.display_name} 合成エラー: {e}")
                primary_failed = True
        else:
            if not primary_failed:
                log.info(f"[TtsService] 一次プロバイダー {provider.display_name} は無効化されています")
            primary_failed = True

        # 3. 段階的フォールバック（Cascading Fallback）
        fallback_candidates = self.get_fallback_candidates(exclude_provider_id=provider.provider_id)
        log.info(f"[TtsService] 段階的フォールバックチェーン開始 (候補 {len(fallback_candidates)} 件)")

        for fb_provider, fb_voice in fallback_candidates:
            try:
                log.info(f"[TtsService] 🔄 フォールバック試行中: {fb_provider.display_name} ({fb_voice})")
                fb_audio = await asyncio.wait_for(
                    fb_provider.synthesize(text, fb_voice, rate, pitch),
                    timeout=fb_provider.timeout_seconds
                )
                if fb_audio and len(fb_audio) > 0:
                    log.info(f"[TtsService] ✅ フォールバック成功: {fb_provider.display_name}")
                    return fb_audio, fb_voice, True
            except Exception as fb_err:
                log.warning(f"[TtsService] ⚠️ フォールバック失敗 ({fb_provider.display_name}): {fb_err}")

        # 4. すべてのフォールバックが失敗した場合、最後の命綱として Edge-TTS を強制試行
        if provider.provider_id != "edge":
            try:
                log.warning("[TtsService] 全エンジン障害。最後の命綱として Edge-TTS を強制試行します")
                edge_audio = await self.edge_provider.synthesize(
                    text, self.edge_provider.default_voice_id, rate, pitch
                )
                if edge_audio and len(edge_audio) > 0:
                    log.info("[TtsService] 🛡️ 最後の命綱 Edge-TTS での音声合成に成功しました")
                    return edge_audio, self.edge_provider.default_voice_id, True
            except Exception as edge_err:
                log.error(f"[TtsService] 最終フォールバック Edge-TTS も失敗しました: {edge_err}")

        raise RuntimeError("すべての音声エンジン（最終命綱 Edge-TTS 含む）での合成に失敗しました")

    async def synthesize(
        self,
        text: str,
        voice: str = "ja-JP-NanamiNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        chime: str = "dingdong",
        urgent: bool = False
    ) -> Dict[str, Any]:
        text = text.strip()
        if not text:
            raise ValueError("Text cannot be empty")

        key = self._generate_cache_key(text, voice, rate, pitch, chime)
        filename = f"speech_{key}.mp3"
        final_path = self.voice_dir / filename

        # キャッシュヒットチェック
        if final_path.exists() and final_path.stat().st_size > 0:
            duration = await self.get_audio_duration(final_path)
            log.info(f"[TTS] 音声キャッシュ HIT: key={key[:8]}..., voice={voice}, dur={duration:.1f}s, text='{text[:25]}...'")
            return {
                "filename": filename,
                "filepath": str(final_path),
                "duration": duration,
                "cached": True,
                "voice": voice,
                "fallback": False
            }

        log.info(f"[TTS] 音声キャッシュ MISS: 新規合成開始 (文字数={len(text)}, voice={voice}, chime={chime}, urgent={urgent}) -> '{text[:30]}...'")

        # 1. 音声バイナリの合成（フォールバックまたは最速並行生成）
        raw_bytes, actual_voice, was_fallback = await self._synthesize_raw(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
            urgent=urgent
        )

        raw_filename = f"raw_{key}.mp3"
        raw_path = self.voice_dir / raw_filename
        with open(raw_path, "wb") as f:
            f.write(raw_bytes)

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
        log.info(f"[TTS] 音声合成・チャイム結合完了: file={filename}, dur={duration:.1f}s, voice={actual_voice}, fallback={was_fallback}")
        self._cleanup_lru_cache()

        return {
            "filename": filename,
            "filepath": str(final_path),
            "duration": duration,
            "cached": False,
            "voice": actual_voice,
            "fallback": was_fallback
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
            log.error(f"[TtsService] Cache cleanup error: {e}")

tts_service = TtsService()
