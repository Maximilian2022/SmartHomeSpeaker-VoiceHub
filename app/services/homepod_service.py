import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pyatv
from pyatv.const import Protocol
from app.config import DATA_DIR

HOMEPOD_CACHE_FILE = DATA_DIR / "homepod_devices.json"

class HomePodService:
    def __init__(self):
        self.devices_cache: List[Dict[str, Any]] = self._load_cache()

    def _load_cache(self) -> List[Dict[str, Any]]:
        if HOMEPOD_CACHE_FILE.exists():
            try:
                with open(HOMEPOD_CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_cache(self):
        try:
            with open(HOMEPOD_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.devices_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[HomePodService] Cache save error: {e}")

    async def scan_devices(self, timeout: int = 4) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        try:
            results = await pyatv.scan(loop, timeout=timeout)
            devices = []
            for conf in results:
                # AirPlay または RAOP プロトコルを持つ端末を抽出
                has_airplay = any(service.protocol in (Protocol.AirPlay, Protocol.RAOP) for service in conf.services)
                if has_airplay:
                    ip = str(conf.address)
                    dev_info = {
                        "id": f"homepod_{ip.replace('.', '_')}",
                        "name": conf.name or f"HomePod ({ip})",
                        "rawName": conf.name,
                        "ip": f"homepod:{ip}",
                        "rawIp": ip,
                        "model": "Apple HomePod",
                        "type": "homepod"
                    }
                    devices.append(dev_info)

            self.devices_cache = devices
            self._save_cache()
            return devices
        except Exception as e:
            print(f"[HomePodService] Scan error: {e}")
            return self.devices_cache

    async def play_audio(self, target_ip_or_id: str, audio_url: str) -> bool:
        loop = asyncio.get_running_loop()
        clean_ip = target_ip_or_id.replace("homepod:", "")
        try:
            # 1. デバイスのスキャン/特定
            results = await pyatv.scan(loop, hosts=[clean_ip], timeout=3)
            if not results:
                # 名前やIDでキャッシュから検索
                cached = next((d for d in self.devices_cache if d["rawIp"] == clean_ip or d["name"] == target_ip_or_id), None)
                if cached:
                    results = await pyatv.scan(loop, hosts=[cached["rawIp"]], timeout=3)

            if not results:
                print(f"[HomePodService] Device not found: {clean_ip}")
                return False

            conf = results[0]
            atv = await pyatv.connect(conf, loop)
            try:
                await atv.stream.play_url(audio_url)
                # 再生コマンド発行後、少し待機してクローズ
                await asyncio.sleep(1.5)
                return True
            finally:
                atv.close()
        except Exception as e:
            print(f"[HomePodService] Play error on {clean_ip}: {e}")
            return False

homepod_service = HomePodService()
