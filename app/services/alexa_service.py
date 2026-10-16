import asyncio
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import DATA_DIR, BASE_DIR, settings

ALEXA_SCRIPT = BASE_DIR / "bin" / "alexa_remote_control.sh"
COOKIE_FILE = DATA_DIR / ".alexa.cookie"

class AlexaService:
    def __init__(self):
        self.script_path = ALEXA_SCRIPT
        self.cookie_path = COOKIE_FILE

    def is_enabled(self) -> bool:
        return self.cookie_path.exists() or bool(settings.refresh_token)

    async def _run_command(self, args: List[str]) -> str:
        env = os.environ.copy()
        env["SET_ALEXA_COOKIE_PATH"] = str(self.cookie_path)
        if settings.refresh_token:
            env["REFRESH_TOKEN"] = settings.refresh_token

        proc = await asyncio.create_subprocess_exec(
            "bash", str(self.script_path), *args,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = stderr.decode(errors="ignore")
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
        if not self.is_enabled():
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
                    "type": "alexa",
                    "isGroup": "group" in dev_name.lower() or "全室" in dev_name or "全体" in dev_name
                })
            return devices
        except Exception as e:
            print(f"[AlexaService] List devices error: {e}")
            return []

alexa_service = AlexaService()
