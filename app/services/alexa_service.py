import asyncio
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import DATA_DIR, BASE_DIR, settings

from app.services.alexa_proxy_service import AlexaAuthProxy

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
        self.devices_cache: List[Dict[str, Any]] = []

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

        print(f"[AlexaService] Starting pure Python proxy auth on {self.proxy_url}...")

        try:
            async def on_token_success(token: str):
                print(f"[AlexaService] Received token from Python proxy! Syncing devices...")
                self.proxy_running = False
                self.proxy_error = None
                settings.refresh_token = token
                try:
                    await self.list_devices()
                except Exception as e:
                    print(f"[AlexaService] Post-auth sync devices error: {e}")

            self.proxy_instance = AlexaAuthProxy(
                host_ip=host_ip,
                port=port,
                amazon_page="amazon.co.jp",
                on_success=on_token_success
            )
            await self.proxy_instance.start()

            return {
                "success": True,
                "loginUrl": self.proxy_url
            }
        except Exception as e:
            self.proxy_running = False
            self.proxy_error = str(e)
            print(f"[AlexaService] Failed to start Python proxy: {e}")
            raise RuntimeError(f"プロキシサーバーの起動に失敗しました: {e}")

    def stop_proxy_auth(self):
        if self.proxy_instance and self.proxy_instance.is_running:
            try:
                asyncio.create_task(self.proxy_instance.stop())
            except Exception:
                pass
        self.proxy_running = False
        self.proxy_url = None
        print("[AlexaService] Proxy stopped.")

    def logout(self):
        self.stop_proxy_auth()
        if self.credentials_path.exists():
            self.credentials_path.unlink(missing_ok=True)
        if self.cookie_path.exists():
            self.cookie_path.unlink(missing_ok=True)
        settings.refresh_token = ""
        self.devices_cache = []
        print("[AlexaService] Logged out.")

    async def _run_command(self, args: List[str]) -> str:
        if not self.is_configured():
            return ""
        env = os.environ.copy()
        env["SET_ALEXA_COOKIE_PATH"] = str(self.cookie_path)
        token = settings.refresh_token
        if not token and self.credentials_path.exists():
            try:
                data = json.loads(self.credentials_path.read_text(encoding="utf-8"))
                token = data.get("refreshToken", "")
            except Exception:
                pass
        if token:
            env["REFRESH_TOKEN"] = token

        proc = await asyncio.create_subprocess_exec(
            "bash", str(self.script_path), *args,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = stderr.decode(errors="ignore").strip()
            print(f"[AlexaService] Command error {args}: {err}")
            raise RuntimeError(err or "Alexa script execution failed")
        return stdout.decode(errors="ignore")

    async def speak(self, device_name: str, text: str) -> bool:
        clean_name = device_name.replace("alexa:", "").strip()
        try:
            await self._run_command(["-d", clean_name, "-e", f"speak:{text}"])
            return True
        except Exception as e:
            print(f"[AlexaService] Speak failed on {clean_name}: {e}")
            return False

    async def list_devices(self) -> List[Dict[str, Any]]:
        if not self.is_configured():
            return []
        try:
            out = await self._run_command(["-a"])
            devices = []
            for line in out.splitlines():
                line = line.strip()
                if not line or line.startswith(("#", "Available")):
                    continue
                dev_name = line.strip('"')
                devices.append({
                    "id": f"alexa_{dev_name.replace(' ', '_')}",
                    "name": f"Alexa ({dev_name})",
                    "ip": f"alexa:{dev_name}",
                    "model": "Amazon Echo",
                    "type": "alexa"
                })
            self.devices_cache = devices
            return devices
        except Exception as e:
            print(f"[AlexaService] List devices error: {e}")
            return []

alexa_service = AlexaService()
