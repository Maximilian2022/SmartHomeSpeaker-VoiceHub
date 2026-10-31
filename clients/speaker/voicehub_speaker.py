# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
#     "miniaudio>=1.59; sys_platform != 'darwin'",
# ]
# ///

import os
import re
import sys
import time
import json
import socket
import shutil
import hashlib
import tempfile
import argparse
import platform
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

# ==============================================================================
# プラットフォーム判定と定数
# ==============================================================================
IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

def get_platform_id() -> str:
    if IS_MAC:
        return "macos"
    elif IS_WIN:
        return "windows"
    elif IS_LINUX:
        return "linux"
    return "pc"

def get_default_device_name() -> str:
    hostname = socket.gethostname() or "PC"
    if IS_MAC:
        return f"{hostname} (Mac)"
    elif IS_WIN:
        return f"{hostname} (Win)"
    return f"{hostname} (Linux)"

def _normalize_volume(val: Optional[float]) -> tuple:
    """音量値を比率 (0.0〜1.0) とパーセント (0〜100) に正規化"""
    if val is None:
        return 1.0, 100
    try:
        f = float(val)
        if f > 1.0:
            vol_ratio = max(0.0, min(1.0, f / 100.0))
            vol_percent = int(max(0, min(100, f)))
        else:
            vol_ratio = max(0.0, min(1.0, f))
            vol_percent = int(vol_ratio * 100)
        return vol_ratio, vol_percent
    except (ValueError, TypeError):
        return 1.0, 100

# ==============================================================================
# クロスプラットフォーム音声再生エンジン
# ==============================================================================
class AudioPlayer:
    def __init__(self):
        self._miniaudio_avail = False
        if not IS_MAC:
            try:
                import miniaudio
                self._miniaudio_avail = True
            except ImportError:
                self._miniaudio_avail = False

    def get_playback_devices(self) -> List[Dict[str, Any]]:
        """OS に接続されている全オーディオ出力デバイス（物理・仮想含む）を列挙"""
        if not IS_MAC and self._miniaudio_avail:
            try:
                import miniaudio
                devs: List[Dict[str, Any]] = []
                ctx = miniaudio.ffi.new("ma_context*")
                res = miniaudio.lib.ma_context_init(miniaudio.ffi.NULL, 0, miniaudio.ffi.NULL, ctx)
                if res != miniaudio.lib.MA_SUCCESS:
                    return devs
                try:
                    with miniaudio.ffi.new("ma_device_info**") as p_infos, miniaudio.ffi.new("ma_uint32*") as p_count:
                        res = miniaudio.lib.ma_context_get_devices(ctx, p_infos, p_count, miniaudio.ffi.NULL, miniaudio.ffi.NULL)
                        if res == miniaudio.lib.MA_SUCCESS:
                            seen_keys = set()
                            for i in range(p_count[0]):
                                info = p_infos[0][i]
                                raw_name = miniaudio.ffi.string(info.name)
                                try:
                                    name = raw_name.decode("utf-8")
                                except UnicodeDecodeError:
                                    name = raw_name.decode("cp932", errors="replace")
                                name = name.strip() or f"Speaker {i + 1}"
                                dev_id = miniaudio.ffi.new("ma_device_id *", info.id)
                                base_key = re.sub(r"[^a-zA-Z0-9_\u3000-\u9fff-]+", "_", name).strip("_") or f"out_{i}"
                                key = base_key
                                suffix = 2
                                while key in seen_keys:
                                    key = f"{base_key}_{suffix}"
                                    suffix += 1
                                seen_keys.add(key)
                                devs.append({
                                    "index": i,
                                    "key": key,
                                    "name": name,
                                    "isDefault": bool(info.isDefault),
                                    "ma_id": dev_id
                                })
                finally:
                    miniaudio.lib.ma_context_uninit(ctx)
                return devs
            except Exception as e:
                print(f"[Player] Device enumeration error: {e}", file=sys.stderr)
        return []

    def play(
        self,
        audio_data: bytes,
        volume: Optional[float] = None,
        output_key: Optional[str] = None,
        output_name: Optional[str] = None
    ) -> bool:
        """音声バイト列（MP3/WAV等）を指定されたローカルスピーカーで再生"""
        suffix = ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
            tf.write(audio_data)
            temp_path = tf.name

        try:
            if IS_MAC:
                return self._play_mac(temp_path, volume)
            elif IS_WIN:
                return self._play_windows(temp_path, audio_data, volume, output_key=output_key, output_name=output_name)
            else:
                return self._play_linux(temp_path, audio_data, volume, output_key=output_key, output_name=output_name)
        finally:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    def _resolve_miniaudio_device_id(self, output_key: Optional[str], output_name: Optional[str]):
        """指定された output_key / output_name（または OS 既定デバイス）の ma_device_id を取得"""
        devs = self.get_playback_devices()
        if not devs:
            return None, None
        if output_key and output_key != "default":
            for d in devs:
                if d["key"] == output_key:
                    return d["ma_id"], d["name"]
        if output_name:
            for d in devs:
                if d["name"] == output_name or output_name.lower() in d["name"].lower():
                    return d["ma_id"], d["name"]
        for d in devs:
            if d.get("isDefault"):
                return d["ma_id"], d["name"]
        return devs[0]["ma_id"], devs[0]["name"]

    def _play_mac(self, file_path: str, volume: Optional[float]) -> bool:
        """macOS: OS標準の afplay コマンドを使用（追加依存なし・極低メモリ・超低遅延）"""
        try:
            vol_ratio, _ = _normalize_volume(volume)
            cmd = ["afplay"]
            if volume is not None:
                cmd.extend(["-v", str(vol_ratio)])
            cmd.append(file_path)
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return res.returncode == 0
        except Exception as e:
            print(f"[Player] afplay error: {e}", file=sys.stderr)
            return False

    def _play_windows(
        self,
        file_path: str,
        audio_data: bytes,
        volume: Optional[float],
        output_key: Optional[str] = None,
        output_name: Optional[str] = None
    ) -> bool:
        """Windows: miniaudio または PowerShell MediaPlayer で音量指定再生"""
        vol_ratio, _ = _normalize_volume(volume)

        if self._miniaudio_avail:
            try:
                import miniaudio
                target_ma_id, resolved_name = self._resolve_miniaudio_device_id(output_key, output_name)
                try:
                    decoded = miniaudio.decode_file(file_path)
                    samples = decoded.samples
                    if vol_ratio < 0.99:
                        import array
                        a = array.array('h', samples)
                        for i in range(len(a)):
                            a[i] = int(a[i] * vol_ratio)
                        samples = a.tobytes()
                    device = miniaudio.PlaybackDevice(device_id=target_ma_id, nchannels=decoded.nchannels, sample_rate=decoded.sample_rate, format=decoded.format) if target_ma_id is not None else miniaudio.PlaybackDevice(nchannels=decoded.nchannels, sample_rate=decoded.sample_rate, format=decoded.format)
                    device.start(samples)
                    while device.is_running:
                        time.sleep(0.05)
                    device.close()
                    return True
                except Exception:
                    stream = miniaudio.stream_file(file_path)
                    if target_ma_id is not None:
                        device = miniaudio.PlaybackDevice(device_id=target_ma_id)
                    else:
                        device = miniaudio.PlaybackDevice()
                    device.start(stream)
                    while device.is_running:
                        time.sleep(0.05)
                    device.close()
                    return True
            except Exception as e:
                print(f"[Player] miniaudio error: {e}, falling back to PowerShell", file=sys.stderr)

        # PowerShell フォールバック (音量指定対応)
        try:
            escaped_path = file_path.replace("'", "''")
            ps_script = f"""
            Add-Type -AssemblyName presentationCore;
            $player = New-Object System.Windows.Media.MediaPlayer;
            $player.Open([System.Uri]'{escaped_path}');
            $player.Volume = {vol_ratio};
            $player.Play();
            Start-Sleep -Milliseconds 300;
            while ($player.NaturalDuration.HasTimeSpan -eq $false) {{ Start-Sleep -Milliseconds 100 }};
            $dur = $player.NaturalDuration.TimeSpan.TotalSeconds;
            Start-Sleep -Seconds ($dur + 0.2);
            $player.Close();
            """
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return res.returncode == 0
        except Exception as e:
            print(f"[Player] PowerShell MediaPlayer error: {e}", file=sys.stderr)
            return False

    def _play_linux(
        self,
        file_path: str,
        audio_data: bytes,
        volume: Optional[float],
        output_key: Optional[str] = None,
        output_name: Optional[str] = None
    ) -> bool:
        """Linux: miniaudio (デバイス指定対応) または paplay / mpv / ffplay / aplay (音量指定対応)"""
        vol_ratio, vol_percent = _normalize_volume(volume)

        # 1. 個別デバイス指定時は miniaudio で対象デバイスを直接指定して再生
        if self._miniaudio_avail and (output_key or output_name):
            try:
                import miniaudio
                target_ma_id, _ = self._resolve_miniaudio_device_id(output_key, output_name)
                try:
                    decoded = miniaudio.decode_file(file_path)
                    samples = decoded.samples
                    if vol_ratio < 0.99:
                        import array
                        a = array.array('h', samples)
                        for i in range(len(a)):
                            a[i] = int(a[i] * vol_ratio)
                        samples = a.tobytes()
                    device = miniaudio.PlaybackDevice(device_id=target_ma_id, nchannels=decoded.nchannels, sample_rate=decoded.sample_rate, format=decoded.format)
                    device.start(samples)
                    while device.is_running:
                        time.sleep(0.05)
                    device.close()
                    return True
                except Exception:
                    stream = miniaudio.stream_file(file_path)
                    device = miniaudio.PlaybackDevice(device_id=target_ma_id) if target_ma_id is not None else miniaudio.PlaybackDevice()
                    device.start(stream)
                    while device.is_running:
                        time.sleep(0.05)
                    device.close()
                    return True
            except Exception as e:
                print(f"[Player] Linux miniaudio targeted error: {e}", file=sys.stderr)

        # 2. 外部CLIツールの存在確認 (音量オプション付き)
        for cmd_name, cmd_args in [
            ("mpv", ["mpv", "--no-terminal", "--really-quiet", f"--volume={vol_percent}", file_path]),
            ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(vol_percent), file_path]),
            ("paplay", ["paplay", f"--volume={int(vol_ratio * 65536)}", file_path]),
            ("aplay", ["aplay", "-q", file_path])
        ]:
            if shutil.which(cmd_name):
                try:
                    res = subprocess.run(cmd_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if res.returncode == 0:
                        return True
                except Exception:
                    pass

        # 3. miniaudio フォールバック
        if self._miniaudio_avail:
            try:
                import miniaudio
                stream = miniaudio.stream_file(file_path)
                device = miniaudio.PlaybackDevice()
                device.start(stream)
                while device.is_running:
                    time.sleep(0.05)
                device.close()
                return True
            except Exception as e:
                print(f"[Player] Linux miniaudio error: {e}", file=sys.stderr)

        print("[Player] ❌ No suitable Linux audio player found (mpv/ffplay/paplay/miniaudio)", file=sys.stderr)
        return False

# ==============================================================================
# 自動起動管理 (Windows / macOS / Linux)
# ==============================================================================
class AutostartManager:
    """各OSネイティブのバックグラウンド自動起動を自己管理"""

    @staticmethod
    def _ensure_persistent_script() -> str:
        """ワンライナー (uv run https://...) 実行時でも永続パス (~/.voicehub/voicehub_speaker.py) に配置して参照"""
        current_file = Path(__file__).resolve()
        persistent_dir = Path.home() / ".voicehub"
        persistent_script = persistent_dir / "voicehub_speaker.py"
        try:
            persistent_dir.mkdir(parents=True, exist_ok=True)
            if current_file != persistent_script and current_file.exists():
                shutil.copy2(current_file, persistent_script)
            if persistent_script.exists():
                return str(persistent_script)
        except Exception:
            pass
        return str(current_file)

    @staticmethod
    def _find_uv_path() -> str:
        """PATH 未反映のシェル環境でも uv の絶対パスを確実に解決"""
        found = shutil.which("uv")
        if found:
            return str(Path(found).resolve())
        exe_name = "uv.exe" if IS_WIN else "uv"
        for candidate in [
            Path.home() / ".local" / "bin" / exe_name,
            Path.home() / ".cargo" / "bin" / exe_name,
        ]:
            if candidate.exists():
                return str(candidate.resolve())
        return "uv"

    @classmethod
    def get_current_cmd_args(cls, server: str, name: str, token: Optional[str]) -> tuple:
        script_path = cls._ensure_persistent_script()
        args = ["--server", server, "--name", name]
        if token:
            args.extend(["--token", token])
        return script_path, args

    @classmethod
    def enable(cls, server: str, name: str, token: Optional[str]) -> bool:
        cls.save_config(server, name, token)
        script_path, args = cls.get_current_cmd_args(server, name, token)
        uv_path = cls._find_uv_path()

        if IS_WIN:
            return cls._enable_windows(uv_path, script_path, args)
        elif IS_MAC:
            return cls._enable_macos(uv_path, script_path, args)
        elif IS_LINUX:
            return cls._enable_linux(uv_path, script_path, args)
        else:
            print("❌ このOSでの自動起動設定はサポートされていません")
            return False

    @classmethod
    def disable(cls, clean: bool = False) -> bool:
        if IS_WIN:
            return cls._disable_windows(clean=clean)
        elif IS_MAC:
            return cls._disable_macos(clean=clean)
        elif IS_LINUX:
            return cls._disable_linux(clean=clean)
        return False

    @staticmethod
    def load_saved_config() -> dict:
        config_file = Path.home() / ".voicehub" / "config.json"
        if config_file.exists():
            try:
                return json.loads(config_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    @staticmethod
    def save_config(server: str, name: str, token: Optional[str] = None):
        config_dir = Path.home() / ".voicehub"
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.json"
            data = {"server": server, "name": name}
            if token:
                data["token"] = token
            config_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def status(cls):
        if IS_WIN:
            cls._status_windows()
        elif IS_MAC:
            cls._status_macos()
        elif IS_LINUX:
            cls._status_linux()

    # --- Windows (スタートアップ VBScript で完全画面非表示常駐) ---
    @staticmethod
    def _get_windows_startup_vbs() -> Path:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            appdata = str(Path.home() / "AppData" / "Roaming")
        startup_dir = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return startup_dir / "VoiceHub_Speaker.vbs"

    @staticmethod
    def _stop_windows_background():
        """バックグラウンド常駐中の voicehub_speaker.py プロセスを停止"""
        try:
            ps_kill = (
                "Get-CimInstance Win32_Process | "
                "Where-Object { $_.CommandLine -like '*voicehub_speaker.py*' -and $_.CommandLine -notlike '*--autostart*' } | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_kill],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    @classmethod
    def _enable_windows(cls, uv_path: str, script_path: str, args: list) -> bool:
        persistent_dir = Path.home() / ".voicehub"
        persistent_dir.mkdir(parents=True, exist_ok=True)
        vbs_path = persistent_dir / "run_silent.vbs"

        args_str = " ".join([f'"{a}"' if " " in a else a for a in args])
        cmd_line = f'"{uv_path}" run "{script_path}" {args_str}'
        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{str(persistent_dir).replace('"', '""')}"
WScript.Sleep 15000
WshShell.Run "{cmd_line.replace('"', '""')}", 0, False
'''
        try:
            with open(vbs_path, "w", encoding="utf-8") as f:
                f.write(vbs_content)

            cls._stop_windows_background()

            # 旧スタートアップ VBS が残っていれば削除
            old_startup = cls._get_windows_startup_vbs()
            if old_startup.exists():
                try:
                    old_startup.unlink()
                except Exception:
                    pass

            # タスクスケジューラ (schtasks) に登録 (ログオン時 + ネットワーク待機遅延20秒)
            tr_cmd = f'wscript.exe //B "{str(vbs_path)}"'
            sch_cmd = [
                "schtasks", "/create",
                "/tn", "VoiceHub_Speaker",
                "/tr", tr_cmd,
                "/sc", "onlogon",
                "/delay", "0000:20",
                "/rl", "limited",
                "/f"
            ]
            res = subprocess.run(sch_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode != 0:
                # schtasks 権限等で失敗した場合はスタートアップフォルダへフォールバック
                with open(old_startup, "w", encoding="utf-8") as f:
                    f.write(vbs_content)

            # 今すぐバックグラウンド常駐を開始
            subprocess.Popen(
                ["wscript.exe", "//B", str(vbs_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("=" * 65)
            print("✅ Windows タスクスケジューラへの登録と常駐起動を完了しました！")
            print("   タスク名: VoiceHub_Speaker (ログオン時・ネットワーク待機起動)")
            print(f"   登録ファイル: {vbs_path}")
            print("   現在および次回PC起動時から、黒い画面を出さずに自動復帰・常駐します。")
            print("=" * 65)
            return True
        except Exception as e:
            print(f"❌ 自動起動登録に失敗しました: {e}")
            return False

    @classmethod
    def _disable_windows(cls, clean: bool = False) -> bool:
        cls._stop_windows_background()

        # 1. タスクスケジューラから削除
        try:
            subprocess.run(["schtasks", "/delete", "/tn", "VoiceHub_Speaker", "/f"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        # 2. 旧スタートアップ VBS 削除
        old_startup = cls._get_windows_startup_vbs()
        if old_startup.exists():
            try:
                old_startup.unlink()
            except Exception:
                pass

        # 3. run_silent.vbs 削除
        silent_vbs = Path.home() / ".voicehub" / "run_silent.vbs"
        if silent_vbs.exists():
            try:
                silent_vbs.unlink()
            except Exception:
                pass

        print("✅ Windows タスクスケジューラおよび自動起動登録を解除し、常駐プロセスを停止しました。")

        # 4. ローカル設定フォルダ (~/.voicehub) の削除確認
        persistent_dir = Path.home() / ".voicehub"
        if persistent_dir.exists():
            should_clean = clean
            if not should_clean and sys.stdin.isatty():
                try:
                    ans = input("\n❓ ローカル設定・キャッシュフォルダ (~/.voicehub) も完全に削除しますか？ [y/N]: ").strip().lower()
                    if ans == "y":
                        should_clean = True
                except Exception:
                    pass

            if should_clean:
                try:
                    shutil.rmtree(persistent_dir, ignore_errors=True)
                    print("🧹 ローカル設定・キャッシュフォルダ (~/.voicehub) を完全に削除しました。")
                except Exception as e:
                    print(f"⚠️ フォルダ削除エラー: {e}")
            else:
                print("ℹ️ ローカル設定・キャッシュフォルダ (~/.voicehub) は保持されました。")

        return True

    @classmethod
    def _status_windows(cls):
        vbs_path = cls._get_windows_startup_vbs()
        if vbs_path.exists():
            print(f"✅ 自動起動: 有効 (登録先: {vbs_path})")
        else:
            print("⚪ 自動起動: 無効 (未登録)")

    # --- macOS (LaunchAgents plist) ---
    @staticmethod
    def _get_macos_plist() -> Path:
        return Path.home() / "Library" / "LaunchAgents" / "com.voicehub.speaker.plist"

    @classmethod
    def _enable_macos(cls, uv_path: str, script_path: str, args: list) -> bool:
        plist_path = cls._get_macos_plist()
        plist_path.parent.mkdir(parents=True, exist_ok=True)

        full_args = [uv_path, "run", script_path] + args
        args_xml = "\n".join([f"        <string>{a}</string>" for a in full_args])

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.voicehub.speaker</string>
    <key>ProgramArguments</key>
    <array>
{args_xml}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/voicehub_speaker.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/voicehub_speaker.err</string>
</dict>
</plist>
"""
        try:
            with open(plist_path, "w", encoding="utf-8") as f:
                f.write(plist_content)
            # launchctl にロード
            subprocess.run(["launchctl", "unload", str(plist_path)], stderr=subprocess.DEVNULL)
            subprocess.run(["launchctl", "load", str(plist_path)], check=True)
            print("=" * 65)
            print("✅ macOS LaunchAgent (ログイン時自動起動) への登録が完了しました！")
            print(f"   登録ファイル: {plist_path}")
            print("   次回ログイン時からバックグラウンドで自動常駐します。")
            print("=" * 65)
            return True
        except Exception as e:
            print(f"❌ LaunchAgent 登録に失敗しました: {e}")
            return False

    @classmethod
    def _disable_macos(cls) -> bool:
        plist_path = cls._get_macos_plist()
        if plist_path.exists():
            subprocess.run(["launchctl", "unload", str(plist_path)], stderr=subprocess.DEVNULL)
            plist_path.unlink()
            print("✅ macOS LaunchAgent からの登録を解除しました。")
            return True
        print("ℹ️ 自動起動登録はされていませんでした。")
        return True

    @classmethod
    def _status_macos(cls):
        plist_path = cls._get_macos_plist()
        if plist_path.exists():
            print(f"✅ 自動起動: 有効 (登録先: {plist_path})")
        else:
            print("⚪ 自動起動: 無効 (未登録)")

    # --- Linux (systemd --user service) ---
    @staticmethod
    def _get_linux_service() -> Path:
        return Path.home() / ".config" / "systemd" / "user" / "voicehub-speaker.service"

    @classmethod
    def _enable_linux(cls, uv_path: str, script_path: str, args: list) -> bool:
        service_path = cls._get_linux_service()
        service_path.parent.mkdir(parents=True, exist_ok=True)

        args_str = " ".join([f'"{a}"' if " " in a else a for a in args])
        exec_start = f"{uv_path} run {script_path} {args_str}"

        service_content = f"""[Unit]
Description=VoiceHub PC Speaker Client
After=network.target sound.target

[Service]
Type=simple
ExecStart={exec_start}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""
        try:
            with open(service_path, "w", encoding="utf-8") as f:
                f.write(service_content)
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
            subprocess.run(["systemctl", "--user", "enable", "voicehub-speaker"], check=True)
            subprocess.run(["systemctl", "--user", "restart", "voicehub-speaker"], check=True)
            print("=" * 65)
            print("✅ Linux systemd --user サービスへの登録が完了しました！")
            print(f"   登録ファイル: {service_path}")
            print("   次回ログイン時または常時バックグラウンドで自動常駐します。")
            print("=" * 65)
            return True
        except Exception as e:
            print(f"❌ systemd サービス登録に失敗しました: {e}")
            return False

    @classmethod
    def _disable_linux(cls) -> bool:
        service_path = cls._get_linux_service()
        if service_path.exists():
            subprocess.run(["systemctl", "--user", "stop", "voicehub-speaker"], stderr=subprocess.DEVNULL)
            subprocess.run(["systemctl", "--user", "disable", "voicehub-speaker"], stderr=subprocess.DEVNULL)
            service_path.unlink()
            subprocess.run(["systemctl", "--user", "daemon-reload"], stderr=subprocess.DEVNULL)
            print("✅ Linux systemd サービスからの登録を解除しました。")
            return True
        print("ℹ️ 自動起動登録はされていませんでした。")
        return True

    @classmethod
    def _status_linux(cls):
        service_path = cls._get_linux_service()
        if service_path.exists():
            print(f"✅ 自動起動: 有効 (登録先: {service_path})")
        else:
            print("⚪ 自動起動: 無効 (未登録)")


# ==============================================================================
# メイン SSE クライアントサービス
# ==============================================================================
class VoiceHubSpeakerClient:
    def __init__(self, server_url: str, name: str, client_id: Optional[str] = None, token: Optional[str] = None):
        self.server_url = server_url.rstrip("/")
        self.name = name
        self.platform = get_platform_id()
        self.client_id = client_id or f"{self.platform}_{socket.gethostname().replace('.', '_')}"
        self.token = token
        self.player = AudioPlayer()
        self._running = True

    @staticmethod
    def _get_local_script_hash() -> str:
        """現在のクライアントスクリプトの SHA-256 ハッシュを計算"""
        try:
            current_file = Path(__file__).resolve()
            if current_file.exists():
                return hashlib.sha256(current_file.read_bytes()).hexdigest()
        except Exception:
            pass
        return ""

    async def _check_and_self_update(self, expected_hash: Optional[str] = None):
        """サーバー上の最新スクリプトをチェックし、更新があれば自動ダウンロード＆再起動"""
        import httpx
        local_hash = self._get_local_script_hash()
        if expected_hash and local_hash and expected_hash == local_hash:
            return

        script_url = f"{self.server_url}/clients/speaker/voicehub_speaker.py"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(script_url)
                if res.status_code != 200:
                    return
                new_bytes = res.content
                new_text = new_bytes.decode("utf-8", errors="replace")
                if "# /// script" not in new_text or "VoiceHubSpeakerClient" not in new_text:
                    return
                new_hash = hashlib.sha256(new_bytes).hexdigest()
                if local_hash and new_hash == local_hash:
                    return

                print(f"[{time.strftime('%H:%M:%S')}] 🔄 新しいバージョンのクライアントスクリプトを検出しました。自動アップデートを実行します...")
                # 1. 永続パス (~/.voicehub/voicehub_speaker.py) を更新
                persistent_dir = Path.home() / ".voicehub"
                persistent_dir.mkdir(parents=True, exist_ok=True)
                persistent_script = persistent_dir / "voicehub_speaker.py"
                persistent_script.write_bytes(new_bytes)

                # 2. 現在実行中のスクリプトパスも更新可能な場合は上書き
                try:
                    current_file = Path(__file__).resolve()
                    if current_file != persistent_script and current_file.exists():
                        current_file.write_bytes(new_bytes)
                except Exception:
                    pass

                print(f"[{time.strftime('%H:%M:%S')}] ✅ アップデート完了！プロセスを自動再起動します...")
                if IS_WIN:
                    vbs_path = AutostartManager._get_windows_startup_vbs()
                    if vbs_path.exists():
                        ps_restart = f"Start-Sleep -Seconds 1; wscript.exe //B '{str(vbs_path)}'"
                        subprocess.Popen(
                            ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_restart],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        os._exit(0)
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ 自動アップデート確認エラー: {e}")

    def _collect_outputs_meta(self) -> List[Dict[str, Any]]:
        devs = self.player.get_playback_devices()
        return [
            {
                "key": d["key"],
                "name": d["name"],
                "isDefault": bool(d.get("isDefault"))
            }
            for d in devs
        ]

    async def _report_outputs(self):
        import httpx
        outputs_meta = self._collect_outputs_meta()
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.server_url}/api/client-speakers/outputs",
                    json={"clientId": self.client_id, "outputs": outputs_meta},
                    headers=headers
                )
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ⚠️ 出力デバイス一覧送信エラー: {e}")

    async def run(self):
        try:
            import httpx
        except ImportError:
            print("=" * 65, file=sys.stderr)
            print("❌ エラー: 必要なパッケージ 'httpx' が見つかりません。", file=sys.stderr)
            print("", file=sys.stderr)
            print("💡 おすすめの実行方法:", file=sys.stderr)
            print("   同梱の 'run.bat' (Windows) または './run.sh' (Mac/Linux) を実行してください。", file=sys.stderr)
            print("   Python やパッケージの事前インストール不要で、自動セットアップされて即座に起動します。", file=sys.stderr)
            print("", file=sys.stderr)
            print("   手動でインストールする場合: pip install httpx miniaudio", file=sys.stderr)
            print("=" * 65, file=sys.stderr)
            return

        outputs_meta = self._collect_outputs_meta()
        print("=" * 65)
        print("🎙️ [VoiceHub PC Speaker Client]")
        print(f"   接続先サーバー : {self.server_url}")
        print(f"   スピーカー名   : {self.name}")
        print(f"   クライアントID : {self.client_id}")
        print(f"   プラットフォーム: {self.platform} ({platform.system()} {platform.release()})")
        if outputs_meta:
            print(f"   検出オーディオ出力 ({len(outputs_meta)}台):")
            for o in outputs_meta:
                mark = "★既定" if o.get("isDefault") else "     "
                print(f"     {mark} [{o['name']}]")
        print("=" * 65)
        print("VoiceHub サーバーへの常駐接続を開始します... (Ctrl+C で終了)\n")

        stream_url = f"{self.server_url}/api/client-speakers/stream"
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        backoff = 2.0
        while self._running:
            try:
                current_outputs = self._collect_outputs_meta()
                params = {
                    "name": self.name,
                    "id": self.client_id,
                    "platform": self.platform,
                    "outputs": json.dumps(current_outputs, ensure_ascii=False),
                    "script_hash": self._get_local_script_hash()
                }
                if self.token:
                    params["token"] = self.token

                # タイムアウトなしでSSEストリーミング接続
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("GET", stream_url, params=params, headers=headers) as resp:
                        if resp.status_code == 401:
                            print("❌ 認証エラー (HTTP 401): --token に正しい Webhook トークンまたは管理者パスワードを指定してください。")
                            await asyncio.sleep(30)
                            continue
                        elif resp.status_code == 429:
                            print("⚠️ レート制限中 (HTTP 429): しばらく待機してから再接続します...")
                            await asyncio.sleep(30)
                            continue
                        elif resp.status_code != 200:
                            print(f"⚠️ 接続エラー: HTTP {resp.status_code}。再試行します...")
                            await asyncio.sleep(backoff)
                            backoff = min(30.0, backoff * 1.5)
                            continue

                        # 正常接続
                        backoff = 2.0
                        print(f"[{time.strftime('%H:%M:%S')}] 🟢 VoiceHub サーバーに接続しました。アナウンス待機中...")

                        current_event = "message"
                        async for line in resp.aiter_lines():
                            line = line.strip()
                            if not line:
                                continue
                            if line.startswith(":"):
                                # keepalive コメント行
                                continue

                            if line.startswith("event:"):
                                current_event = line[len("event:"):].strip()
                            elif line.startswith("data:"):
                                data_str = line[len("data:"):].strip()
                                await self._handle_event(current_event, data_str)

            except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError) as e:
                print(f"[{time.strftime('%H:%M:%S')}] 🟡 サーバーから切断されました: {e} ({int(backoff)}秒後に自動再接続...)")
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 1.5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] ⚠️ 予期しないエラー: {e} ({int(backoff)}秒後に再試行)")
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 1.5)

        print("\n👋 クライアントを終了しました。")

    async def _handle_event(self, event_type: str, data_str: str):
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            data = {"raw": data_str}

        if event_type == "connected":
            print(f"[{time.strftime('%H:%M:%S')}] ✅ 登録完了: VoiceHub 上にスピーカーとして認識されました。")
            srv_hash = data.get("scriptHash")
            if srv_hash:
                await self._check_and_self_update(srv_hash)

        elif event_type == "self_update":
            await self._check_and_self_update(data.get("scriptHash"))

        elif event_type == "rescan":
            await self._report_outputs()

        elif event_type == "play":
            audio_url = data.get("audio_url")
            text = data.get("text", "")
            volume = data.get("volume")
            output_key = data.get("output_key")
            output_name = data.get("output_name")
            display_text = f"'{text}'" if text else "(音声ファイル)"
            target_label = f" -> [{output_name or output_key}]" if (output_name or output_key) else ""
            print(f"[{time.strftime('%H:%M:%S')}] 🔊 音声再生要求を受信{target_label}: {display_text}")

            if not audio_url:
                return

            # 相対パスの場合は完全URLに補完
            if audio_url.startswith("/"):
                audio_url = f"{self.server_url}{audio_url}"

            # 非同期で音声ファイルをダウンロードしてローカル再生
            asyncio.create_task(self._download_and_play(audio_url, volume, output_key, output_name))

    async def _download_and_play(
        self,
        audio_url: str,
        volume: Optional[float],
        output_key: Optional[str] = None,
        output_name: Optional[str] = None
    ):
        import httpx
        try:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(audio_url, headers=headers)
                if res.status_code == 200:
                    audio_bytes = res.content
                    # 別スレッドでブロック再生を実行（非同期ループをブロックさせない）
                    loop = asyncio.get_running_loop()
                    ok = await loop.run_in_executor(
                        None,
                        self.player.play,
                        audio_bytes,
                        volume,
                        output_key,
                        output_name
                    )
                    if ok:
                        print(f"[{time.strftime('%H:%M:%S')}] ✅ 再生完了")
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] ❌ 再生失敗")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] ❌ 音声ダウンロード失敗: HTTP {res.status_code}")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ❌ 音声取得/再生エラー: {e}")


# ==============================================================================
# CLI エントリーポイント
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Smart Speaker VoiceHub - PC Speaker Client (Windows / Mac / Linux)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 通常起動（フォアグラウンド実行）
  uv run voicehub_speaker.py --server http://192.168.1.100:8080 --name "My-PC"

  # 自動起動の有効化（次回PC起動時からバックグラウンド常駐）
  uv run voicehub_speaker.py --server http://192.168.1.100:8080 --name "My-PC" --autostart enable

  # 自動起動の解除
  uv run voicehub_speaker.py --autostart disable
        """
    )
    parser.add_argument("--server", default="http://localhost:8080", help="VoiceHub サーバーのURL (デフォルト: http://localhost:8080)")
    parser.add_argument("--name", default=get_default_device_name(), help="VoiceHub に表示されるスピーカー名 (デフォルト: ホスト名)")
    parser.add_argument("--id", default=None, help="一意のクライアントID (未指定時は自動生成)")
    parser.add_argument("--token", default=None, help="Webhook 認証トークン (VoiceHub でトークンが設定されている場合)")
    parser.add_argument("--autostart", choices=["enable", "disable", "status"], help="OS起動時の自動バックグラウンド起動を設定/解除/確認")
    parser.add_argument("--clean", action="store_true", help="自動起動解除時にローカル設定・キャッシュフォルダ (~/.voicehub) も完全削除")

    args = parser.parse_args()

    # 保存済み設定の自動ロード（引数が未指定の場合に復元）
    saved_cfg = AutostartManager.load_saved_config()
    if args.server == "http://localhost:8080" and saved_cfg.get("server"):
        args.server = saved_cfg["server"]
    if not args.token and saved_cfg.get("token"):
        args.token = saved_cfg["token"]

    # 自動起動オプションの処理
    if args.autostart:
        if args.autostart == "enable":
            AutostartManager.enable(args.server, args.name, args.token)
        elif args.autostart == "disable":
            AutostartManager.disable(clean=args.clean)
        elif args.autostart == "status":
            AutostartManager.status()
        return

    # 通常実行時も次回のために設定を保存
    AutostartManager.save_config(args.server, args.name, args.token)

    # 通常のクライアント実行
    client = VoiceHubSpeakerClient(
        server_url=args.server,
        name=args.name,
        client_id=args.id,
        token=args.token
    )
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\n終了しました。")


if __name__ == "__main__":
    main()
