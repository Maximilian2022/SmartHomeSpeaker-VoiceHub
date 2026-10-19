import asyncio
import glob
import json
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import DATA_DIR, BASE_DIR, settings
from app.services.alexa_proxy_service import AlexaAuthProxy
from app.core.logger import get_logger

log = get_logger("Alexa")

ALEXA_SCRIPT = BASE_DIR / "bin" / "alexa_remote_control.sh"
COOKIE_FILE = DATA_DIR / ".alexa.cookie"
CREDENTIALS_FILE = DATA_DIR / "alexa_credentials.json"

class AlexaService:
    def __init__(self):
        self.script_path = ALEXA_SCRIPT
        self.cookie_path = COOKIE_FILE
        self.credentials_path = CREDENTIALS_FILE
        self.proxy_instance: Optional[AlexaAuthProxy] = None
        self.proxy_running: bool = False
        self.proxy_url: Optional[str] = None
        self.proxy_error: Optional[str] = None
        self._proxy_timer_task: Optional[asyncio.Task] = None
        self.devices_cache: List[Dict[str, Any]] = []
        self._last_devices_fetch_time: float = 0.0
        # Amazon Alexa レートリミットおよび /tmp/.alexa.cmd ファイル競合防止用セマフォ (完全直列化: 1並列)
        self._semaphore = asyncio.Semaphore(1)

    def is_configured(self) -> bool:
        if self.credentials_path.exists():
            try:
                data = json.loads(self.credentials_path.read_text(encoding="utf-8"))
                if data and (data.get("refreshToken") or data.get("localCookie")):
                    return True
            except Exception:
                pass
        return self.cookie_path.exists() or bool(settings.refresh_token)

    def is_enabled(self) -> bool:
        return self.is_configured() or bool(settings.alexa_enabled)

    def get_auth_status(self, host_ip: str = "127.0.0.1") -> Dict[str, Any]:
        return {
            "enabled": self.is_enabled(),
            "configured": self.is_configured(),
            "proxyRunning": self.proxy_running,
            "proxyUrl": self.proxy_url,
            "proxyError": self.proxy_error,
            "deviceCount": len(self.devices_cache)
        }

    async def start_proxy_auth(self, host_ip: str = "127.0.0.1", port: int = 8081) -> Dict[str, Any]:
        if self.proxy_running and self.proxy_instance and self.proxy_instance.is_running:
            return {
                "success": True,
                "alreadyRunning": True,
                "loginUrl": self.proxy_url
            }

        self.proxy_running = True
        self.proxy_error = None
        self.proxy_url = f"http://{host_ip}:{port}"

        log.info(f"Starting pure Python proxy auth on {self.proxy_url}...")

        try:
            async def on_token_success(token: str):
                log.info("Received token from Python proxy! Syncing devices...")
                self.stop_proxy_auth()
                settings.refresh_token = token
                try:
                    await self.list_devices(force_refresh=True)
                except Exception as e:
                    log.error(f"Post-auth sync devices error: {e}")

            self.proxy_instance = AlexaAuthProxy(
                host_ip=host_ip,
                port=port,
                amazon_page="amazon.co.jp",
                on_success=on_token_success
            )
            await self.proxy_instance.start()

            # 10分間 (600秒) 放置された場合の自動停止タイマーを設定
            if self._proxy_timer_task and not self._proxy_timer_task.done():
                self._proxy_timer_task.cancel()

            async def _auto_stop_timer():
                try:
                    await asyncio.sleep(600)
                    if self.proxy_running:
                        log.info("Proxy auth timed out after 10 minutes. Stopping proxy automatically.")
                        self.stop_proxy_auth()
                except asyncio.CancelledError:
                    pass

            self._proxy_timer_task = asyncio.create_task(_auto_stop_timer())

            return {
                "success": True,
                "loginUrl": self.proxy_url
            }
        except Exception as e:
            self.stop_proxy_auth()
            self.proxy_error = str(e)
            log.error(f"Failed to start Python proxy: {e}")
            raise RuntimeError(f"プロキシサーバーの起動に失敗しました: {e}")

    def stop_proxy_auth(self):
        if self._proxy_timer_task and not self._proxy_timer_task.done():
            self._proxy_timer_task.cancel()
            self._proxy_timer_task = None

        if self.proxy_instance and self.proxy_instance.is_running:
            try:
                asyncio.create_task(self.proxy_instance.stop())
            except Exception:
                pass
        self.proxy_running = False
        self.proxy_url = None
        log.info("Proxy stopped.")

    def logout(self):
        self.stop_proxy_auth()
        if self.credentials_path.exists():
            self.credentials_path.unlink(missing_ok=True)
        if self.cookie_path.exists():
            self.cookie_path.unlink(missing_ok=True)

        # /tmp 配下のクッキー・デバイスリスト・コマンド一時ファイルも完全削除
        for pattern in ["/tmp/.alexa.cookie", "/tmp/.alexa.devicelist*", "/tmp/.alexa.cmd*"]:
            for f in glob.glob(pattern):
                try:
                    os.remove(f)
                except OSError:
                    pass

        settings.refresh_token = ""
        self.devices_cache = []
        log.info("Logged out.")

    async def _run_command(
        self,
        args: List[str],
        retry_on_rate_limit: bool = True,
        extra_env: Optional[Dict[str, str]] = None
    ) -> str:
        if not self.is_configured():
            log.warning("Alexa is not configured, command ignored.")
            return ""
        env = os.environ.copy()
        # スクリプト実仕様に合わせて TMP ディレクトリを DATA_DIR に指定し、ロケールを ja-JP に設定
        env["TMP"] = str(DATA_DIR)
        env["TTS_LOCALE"] = "ja-JP"
        env["SET_ALEXA_COOKIE_PATH"] = str(self.cookie_path)
        env["AMAZON"] = os.environ.get("ALEXA_AMAZON", "amazon.co.jp")
        env["ALEXA"] = os.environ.get("ALEXA_ALEXA", "alexa.amazon.co.jp")

        if extra_env:
            env.update(extra_env)

        token = settings.refresh_token
        if not token and self.credentials_path.exists():
            try:
                data = json.loads(self.credentials_path.read_text(encoding="utf-8"))
                token = data.get("refreshToken", "")
            except Exception as e:
                log.warning(f"Failed to read credentials file: {e}")
        if token:
            env["REFRESH_TOKEN"] = token

        cmd_str = f"bash {self.script_path} {' '.join(args)}"

        async with self._semaphore:
            max_attempts = 2 if retry_on_rate_limit else 1
            for attempt in range(max_attempts):
                log.info(f"Executing: {cmd_str} (attempt {attempt + 1}/{max_attempts})")
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "bash", str(self.script_path), *args,
                        env=env,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=35.0)
                    out_str = stdout.decode(errors="ignore").strip()
                    err_str = stderr.decode(errors="ignore").strip()

                    # レート制限 (Rate exceeded) 検知時のループ再試行 (再帰呼び出しを排除してデッドロック防止)
                    combined_output = f"{out_str} {err_str}".lower()
                    if "rate exceed" in combined_output:
                        if attempt == 0 and retry_on_rate_limit:
                            log.warning(f"Amazon Alexa Rate Limit detected for '{cmd_str}', waiting 1.2s and retrying within loop...")
                            await asyncio.sleep(1.2)
                            continue
                        else:
                            raise RuntimeError(f"Alexa API Rate Limit exceeded: {out_str or err_str}")

                    if proc.returncode != 0:
                        log.error(f"Command failed (code {proc.returncode}): {err_str or out_str}")
                        raise RuntimeError(err_str or out_str or "Alexa script execution failed")

                    # 次のリクエストとの間に最低限のインターバル (レート制限・クッキー破損防止)
                    await asyncio.sleep(0.15)
                    log.info(f"Command succeeded: {out_str[:120]}")
                    return out_str
                except asyncio.TimeoutError:
                    log.error(f"Command timed out after 35s: {cmd_str}")
                    raise TimeoutError("Alexa command timed out")
                except Exception as e:
                    if attempt < max_attempts - 1 and "rate exceed" in str(e).lower():
                        continue
                    log.error(f"Execution error on {cmd_str}: {e}")
                    raise

    async def speak(self, device_name: str, text: str, volume_level: Optional[float] = None) -> bool:
        clean_name = device_name.replace("alexa:", "").strip()
        clean_name = re.sub(r"^Alexa \((.+)\)$", r"\1", clean_name)
        log.info(f"Speak request to target='{clean_name}' (raw='{device_name}'): '{text[:30]}'")

        try:
            clean_text = text.replace("'", "").replace('"', '')
            extra_env: Dict[str, str] = {}
            if volume_level is not None:
                vol_int = int(volume_level * 100) if volume_level <= 1.0 else int(volume_level)
                vol_int = max(1, min(100, vol_int))
                extra_env["SPEAKVOL"] = str(vol_int)
                log.info(f"Setting Alexa SPEAKVOL to {vol_int}% for speech sequence")

            await self._run_command(["-d", clean_name, "-e", f"speak:{clean_text}"], extra_env=extra_env)
            log.info(f"✅ Successfully spoke to Alexa device: {clean_name}")
            return True
        except Exception as e:
            log.error(f"❌ Failed to speak to Alexa device {clean_name}: {e}")
            return False

    async def set_volume(self, device_name: str, volume: int) -> bool:
        clean_name = device_name.replace("alexa:", "").strip()
        clean_name = re.sub(r"^Alexa \((.+)\)$", r"\1", clean_name)
        vol_int = max(0, min(100, int(volume)))
        try:
            await self._run_command(["-d", clean_name, "-e", f"vol:{vol_int}"])
            log.info(f"✅ Successfully set Alexa volume to {vol_int}%: {clean_name}")
            return True
        except Exception as e:
            log.error(f"❌ Failed to set Alexa volume for {clean_name}: {e}")
            return False

    async def list_devices(self, force_refresh: bool = False, cache_ttl: float = 300.0) -> List[Dict[str, Any]]:
        if not self.is_configured():
            log.info("Alexa not configured, skipping device listing.")
            return []

        now = time.time()
        if not force_refresh and self.devices_cache and (now - self._last_devices_fetch_time < cache_ttl):
            log.debug(f"Returning {len(self.devices_cache)} cached Alexa devices (TTL: {int(cache_ttl - (now - self._last_devices_fetch_time))}s left)")
            return self.devices_cache

        try:
            out = await self._run_command(["-a"], retry_on_rate_limit=False)
            devices = []
            for line in out.splitlines():
                line = line.strip()
                if not line or line.startswith(("#", "Available", "the following")):
                    continue
                dev_name = line.strip('"')
                is_grp = dev_name.lower() in ("全部", "全部の部屋", "all", "everywhere", "全室") or "グループ" in dev_name
                devices.append({
                    "id": f"alexa_{dev_name.replace(' ', '_')}",
                    "name": f"Alexa ({dev_name})",
                    "rawName": dev_name,
                    "ip": f"alexa:{dev_name}",
                    "model": "Amazon Echo Group" if is_grp else "Amazon Echo",
                    "type": "alexa",
                    "isGroup": is_grp
                })
            self.devices_cache = devices
            self._last_devices_fetch_time = now
            log.info(f"Discovered {len(devices)} Alexa device(s) (including groups).")
            return devices
        except Exception as e:
            log.error(f"Failed to list Alexa devices: {e}")
            return self.devices_cache

alexa_service = AlexaService()
