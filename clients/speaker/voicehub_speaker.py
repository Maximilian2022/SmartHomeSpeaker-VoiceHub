# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "httpx>=0.27.0",
#     "miniaudio>=1.59; sys_platform != 'darwin'",
# ]
# ///

import os
import sys
import time
import json
import socket
import shutil
import tempfile
import argparse
import platform
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

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

    def play(self, audio_data: bytes, volume: Optional[float] = None) -> bool:
        """音声バイト列（MP3/WAV等）をローカルスピーカーで再生"""
        # 一時ファイルに保存して再生
        suffix = ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
            tf.write(audio_data)
            temp_path = tf.name

        try:
            if IS_MAC:
                return self._play_mac(temp_path, volume)
            elif IS_WIN:
                return self._play_windows(temp_path, audio_data, volume)
            else:
                return self._play_linux(temp_path, audio_data, volume)
        finally:
            # 再生完了またはエラー後に一時ファイル削除（Windows等のファイルロック解放待ち含む）
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    def _play_mac(self, file_path: str, volume: Optional[float]) -> bool:
        """macOS: OS標準の afplay コマンドを使用（追加依存なし・極低メモリ・超低遅延）"""
        try:
            cmd = ["afplay"]
            if volume is not None:
                # afplay -v <0.0-1.0または255等> (通常 0.0〜1.0)
                cmd.extend(["-v", str(max(0.0, min(1.0, float(volume))))])
            cmd.append(file_path)
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return res.returncode == 0
        except Exception as e:
            print(f"[Player] afplay error: {e}", file=sys.stderr)
            return False

    def _play_windows(self, file_path: str, audio_data: bytes, volume: Optional[float]) -> bool:
        """Windows: miniaudio または PowerShell MediaPlayer で再生"""
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
                print(f"[Player] miniaudio error: {e}, falling back to PowerShell", file=sys.stderr)

        # PowerShell フォールバック
        try:
            escaped_path = file_path.replace("'", "''")
            ps_script = f"""
            Add-Type -AssemblyName presentationCore;
            $player = New-Object System.Windows.Media.MediaPlayer;
            $player.Open([System.Uri]'{escaped_path}');
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

    def _play_linux(self, file_path: str, audio_data: bytes, volume: Optional[float]) -> bool:
        """Linux: paplay / mpv / ffplay / aplay または miniaudio"""
        # 1. 外部CLIツールの存在確認
        for cmd_name, cmd_args in [
            ("mpv", ["mpv", "--no-terminal", "--really-quiet", file_path]),
            ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", file_path]),
            ("paplay", ["paplay", file_path]),
            ("aplay", ["aplay", "-q", file_path])
        ]:
            if shutil.which(cmd_name):
                try:
                    res = subprocess.run(cmd_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if res.returncode == 0:
                        return True
                except Exception:
                    pass

        # 2. miniaudio フォールバック
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
    def get_current_cmd_args(server: str, name: str, token: Optional[str]) -> list:
        script_path = str(Path(__file__).resolve())
        args = ["--server", server, "--name", name]
        if token:
            args.extend(["--token", token])
        return script_path, args

    @classmethod
    def enable(cls, server: str, name: str, token: Optional[str]) -> bool:
        script_path, args = cls.get_current_cmd_args(server, name, token)
        uv_path = shutil.which("uv") or "uv"

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
    def disable(cls) -> bool:
        if IS_WIN:
            return cls._disable_windows()
        elif IS_MAC:
            return cls._disable_macos()
        elif IS_LINUX:
            return cls._disable_linux()
        return False

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

    @classmethod
    def _enable_windows(cls, uv_path: str, script_path: str, args: list) -> bool:
        vbs_path = cls._get_windows_startup_vbs()
        vbs_path.parent.mkdir(parents=True, exist_ok=True)
        
        args_str = " ".join([f'"{a}"' if " " in a else a for a in args])
        cmd_line = f'"{uv_path}" run "{script_path}" {args_str}'
        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "{cmd_line.replace('"', '""')}", 0, False
'''
        try:
            with open(vbs_path, "w", encoding="utf-8") as f:
                f.write(vbs_content)
            print("=" * 65)
            print("✅ Windows スタートアップへの登録が完了しました！")
            print(f"   登録ファイル: {vbs_path}")
            print("   次回PC起動時から、黒い画面を出さずにバックグラウンドで自動常駐します。")
            print("=" * 65)
            return True
        except Exception as e:
            print(f"❌ スタートアップ登録に失敗しました: {e}")
            return False

    @classmethod
    def _disable_windows(cls) -> bool:
        vbs_path = cls._get_windows_startup_vbs()
        if vbs_path.exists():
            vbs_path.unlink()
            print("✅ Windows スタートアップからの登録を解除しました。")
            return True
        print("ℹ️ スタートアップ登録はされていませんでした。")
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

        print("=" * 65)
        print("🎙️ [VoiceHub PC Speaker Client]")
        print(f"   接続先サーバー : {self.server_url}")
        print(f"   スピーカー名   : {self.name}")
        print(f"   クライアントID : {self.client_id}")
        print(f"   プラットフォーム: {self.platform} ({platform.system()} {platform.release()})")
        print("=" * 65)
        print("VoiceHub サーバーへの常駐接続を開始します... (Ctrl+C で終了)\n")

        stream_url = f"{self.server_url}/api/client-speakers/stream"
        params = {
            "name": self.name,
            "id": self.client_id,
            "platform": self.platform
        }
        if self.token:
            params["token"] = self.token

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        backoff = 2.0
        while self._running:
            try:
                # タイムアウトなしでSSEストリーミング接続
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("GET", stream_url, params=params, headers=headers) as resp:
                        if resp.status_code == 401:
                            print("❌ 認証エラー (HTTP 401): --token に正しい Webhook トークンまたは管理者パスワードを指定してください。")
                            await asyncio.sleep(5)
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

        elif event_type == "play":
            audio_url = data.get("audio_url")
            text = data.get("text", "")
            volume = data.get("volume")
            display_text = f"'{text}'" if text else "(音声ファイル)"
            print(f"[{time.strftime('%H:%M:%S')}] 🔊 音声再生要求を受信: {display_text}")

            if not audio_url:
                return

            # 相対パスの場合は完全URLに補完
            if audio_url.startswith("/"):
                audio_url = f"{self.server_url}{audio_url}"

            # 非同期で音声ファイルをダウンロードしてローカル再生
            asyncio.create_task(self._download_and_play(audio_url, volume))

    async def _download_and_play(self, audio_url: str, volume: Optional[float]):
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
                    ok = await loop.run_in_executor(None, self.player.play, audio_bytes, volume)
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

    args = parser.parse_args()

    # 自動起動オプションの処理
    if args.autostart:
        if args.autostart == "enable":
            AutostartManager.enable(args.server, args.name, args.token)
        elif args.autostart == "disable":
            AutostartManager.disable()
        elif args.autostart == "status":
            AutostartManager.status()
        return

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
