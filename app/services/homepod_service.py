import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import pyatv
from pyatv.const import Protocol
from app.config import DATA_DIR
from app.core.logger import get_logger

log = get_logger("HomePod")
HOMEPOD_CACHE_FILE = DATA_DIR / "homepod_devices.json"

class HomePodService:
    def __init__(self):
        self.devices_cache: List[Dict[str, Any]] = self._load_cache()

    def _load_cache(self) -> List[Dict[str, Any]]:
        if HOMEPOD_CACHE_FILE.exists():
            try:
                with open(HOMEPOD_CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    log.info(f"Loaded {len(data)} HomePod devices from cache.")
                    return data
            except Exception as e:
                log.warning(f"Failed to load HomePod cache: {e}")
        return []

    def _save_cache(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(HOMEPOD_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.devices_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"HomePod cache save error: {e}")

    async def scan_devices(self, timeout: int = 4) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        log.info(f"Scanning for HomePod devices (timeout={timeout}s)...")
        try:
            results = await pyatv.scan(loop, timeout=timeout)
            devices = []
            for conf in results:
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

            # 全体グループを先頭に追加
            full_list = [
                {
                    "id": "homepod_ALL",
                    "name": "全室 HomePod",
                    "ip": "homepod:ALL",
                    "model": "Apple HomePod Group",
                    "type": "homepod",
                    "isGroup": True
                },
                *devices
            ]
            self.devices_cache = full_list
            self._save_cache()
            log.info(f"Scan complete: {len(devices)} HomePod(s) discovered.")
            return full_list
        except Exception as e:
            log.error(f"HomePod scan error: {e}")
            return self.devices_cache

    async def set_volume(self, target_ip_or_id: str, volume: float) -> bool:
        """
        HomePod の音量を設定 (0〜100 または 0.0〜1.0)
        """
        loop = asyncio.get_running_loop()
        clean_target = target_ip_or_id.replace("homepod:", "").strip()
        vol_percent = float(volume * 100) if volume <= 1.0 else float(volume)
        vol_percent = max(0.0, min(100.0, vol_percent))

        found = next((
            d for d in self.devices_cache
            if d.get("rawIp") == clean_target
            or d.get("name") == clean_target
            or d.get("ip") == f"homepod:{clean_target}"
            or d.get("id") == target_ip_or_id
        ), None)
        target_host = found.get("rawIp") if found and found.get("rawIp") else clean_target

        try:
            hosts = [target_host] if "." in target_host else None
            atvs = await pyatv.scan(loop, hosts=hosts, timeout=4)
            selected = None
            for a in atvs:
                if a.identifier == target_host or str(a.address) == target_host or a.name == target_host:
                    selected = a
                    break
            if not selected and atvs:
                selected = atvs[0]

            if not selected:
                log.error(f"HomePod device not found for volume set: {target_host}")
                return False

            atv = await pyatv.connect(selected, loop)
            try:
                if hasattr(atv, "audio") and hasattr(atv.audio, "set_volume"):
                    await atv.audio.set_volume(vol_percent)
                    log.info(f"✅ Successfully set HomePod volume to {vol_percent}%: {target_host}")
                    return True
                else:
                    log.warning(f"HomePod device {target_host} does not support audio.set_volume")
                    return False
            finally:
                atv.close()
        except Exception as e:
            log.error(f"❌ Failed to set volume on HomePod {target_host}: {e}")
            return False

    async def play_audio(self, target_ip_or_id: str, audio_path: str, volume_level: Optional[float] = None) -> bool:
        """
        ローカル音声ファイル (mp3/wav) を AirPlay 経由で HomePod に直接ストリーミング
        """
        loop = asyncio.get_running_loop()
        clean_target = target_ip_or_id.replace("homepod:", "").strip()

        # ALL の場合は個別全台へ並行ストリーミング
        if clean_target.upper() == "ALL":
            individuals = [d for d in self.devices_cache if d.get("ip") != "homepod:ALL" and d.get("rawIp")]
            if not individuals:
                log.warning("No individual HomePods found in cache for ALL group.")
                return False
            log.info(f"Broadcasting to all HomePods ({len(individuals)} devices)...")
            tasks = [self.play_audio(d["rawIp"], audio_path, volume_level=volume_level) for d in individuals]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return any(r is True for r in results)

        if not os.path.exists(audio_path):
            log.error(f"Audio file not found: {audio_path}")
            return False

        # キャッシュから rawIp を検索
        found = next((
            d for d in self.devices_cache
            if d.get("mac") == clean_target
            or d.get("rawIp") == clean_target
            or d.get("rawName") == clean_target
            or d.get("name") == clean_target
            or d.get("ip") == f"homepod:{clean_target}"
            or d.get("id") == target_ip_or_id
        ), None)

        target_host = found.get("rawIp") if found and found.get("rawIp") else clean_target
        log.info(f"Connecting to HomePod: target='{target_host}' (raw='{target_ip_or_id}') file='{audio_path}'")

        try:
            hosts = [target_host] if "." in target_host else None
            atvs = await pyatv.scan(loop, hosts=hosts, timeout=4)
            selected = None
            for a in atvs:
                if a.identifier == target_host or str(a.address) == target_host or a.name == target_host:
                    selected = a
                    break
            if not selected and atvs:
                selected = atvs[0]

            if not selected:
                log.error(f"HomePod device not found for target: {target_host}")
                return False

            atv = await pyatv.connect(selected, loop)
            try:
                # 音量指定がある場合は再生前に反映
                if volume_level is not None and hasattr(atv, "audio") and hasattr(atv.audio, "set_volume"):
                    try:
                        vol_f = float(volume_level * 100) if volume_level <= 1.0 else float(volume_level)
                        await atv.audio.set_volume(max(0.0, min(100.0, vol_f)))
                    except Exception as ve:
                        log.warning(f"Failed to set volume on HomePod before stream: {ve}")

                log.info(f"Streaming file to HomePod ({selected.name or target_host})...")
                await atv.stream.stream_file(audio_path)
                log.info(f"✅ HomePod stream completed successfully on {selected.name or target_host}")
                return True
            finally:
                atv.close()
        except Exception as e:
            log.error(f"❌ Failed to stream to HomePod {target_host}: {e}")
            return False

homepod_service = HomePodService()
