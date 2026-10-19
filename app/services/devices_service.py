import asyncio
import re
import subprocess
from typing import List, Dict, Any, Optional
from app.services.settings_service import settings_manager
from app.services.alexa_service import alexa_service
from app.services.homepod_service import homepod_service

def decode_avahi_string(s: str) -> str:
    r"""Avahi の \DDD (10進数バイトエスケープ) を UTF-8 デコード"""
    if not s:
        return ""
    try:
        byte_arr = bytearray()
        i = 0
        while i < len(s):
            if s[i] == "\\" and i + 3 < len(s) and s[i+1:i+4].isdigit():
                byte_arr.append(int(s[i+1:i+4]))
                i += 4
            else:
                byte_arr.extend(s[i].encode("utf-8"))
                i += 1
        return byte_arr.decode("utf-8", errors="ignore")
    except Exception:
        return s

class DeviceManager:
    def __init__(self):
        self.devices: Dict[str, Dict[str, Any]] = {}
        # 初回スキャン
        self.scan_google_devices()

    def get_default_device_ip(self) -> str:
        configured = settings_manager.get_default_device_id()
        if configured:
            return configured
        first_dev = next(iter(self.devices.values()), None)
        return first_dev["ip"] if first_dev else ""

    def set_default_device_ip(self, dev_id: str) -> str:
        return settings_manager.set_default_device_id(dev_id)

    def get_device_category_order(self, dev: Dict[str, Any]) -> int:
        dtype = (dev.get("type") or "google").lower()
        name = (dev.get("name") or "").lower()
        model = (dev.get("model") or "").lower()
        ip = (dev.get("ip") or "").lower()

        is_group = bool(
            dev.get("isGroup") or
            ip.endswith(":all") or
            "group" in model or
            "グループ" in model or
            "全室" in name or
            "グループ" in name
        )

        if is_group:
            if dtype == "google": return 1
            if dtype == "alexa": return 2
            if dtype == "homepod": return 3
            return 1
        else:
            if dtype == "google": return 4
            if dtype == "alexa": return 5
            if dtype == "homepod": return 6
            if dtype == "dlna": return 7
            if dtype == "onvif": return 8
            return 4

    async def get_devices(self) -> List[Dict[str, Any]]:
        default_ip = self.get_default_device_ip()
        results: List[Dict[str, Any]] = []

        # 1. Google Cast デバイス
        for dev in self.devices.values():
            d = dict(dev)
            d["isDefault"] = (d["ip"] == default_ip)
            results.append(d)

        # 2. Alexa デバイス
        if alexa_service.is_enabled():
            try:
                alexa_devs = await alexa_service.list_devices()
                for ad in alexa_devs:
                    d = dict(ad)
                    d["isDefault"] = (d.get("ip") == default_ip or d.get("id") == default_ip)
                    results.append(d)
            except Exception as e:
                print(f"[DeviceManager] Alexa list error: {e}")

        # 3. HomePod デバイス
        try:
            hp_devs = homepod_service.devices_cache
            for hd in hp_devs:
                d = dict(hd)
                d["isDefault"] = (d["ip"] == default_ip)
                results.append(d)
        except Exception as e:
            print(f"[DeviceManager] HomePod list error: {e}")

        # 4. ONVIF & DLNA 登録済みデバイス
        onvif_config = settings_manager.get().get("onvif", {})
        if onvif_config.get("enabled", True):
            for dev in onvif_config.get("registeredDevices", []):
                if dev.get("enabled", True):
                    dtype = dev.get("type", "onvif")
                    raw_ip = dev.get("ip", "")
                    prefix = f"{dtype}:{raw_ip}"
                    results.append({
                        "id": dev.get("id") or f"{dtype}_{raw_ip.replace('.', '_')}",
                        "name": dev.get("name") or dev.get("friendlyName") or f"{dtype.upper()} ({raw_ip})",
                        "ip": prefix,
                        "rawIp": raw_ip,
                        "port": dev.get("port", 8000),
                        "model": dev.get("model") or ("ONVIF Speaker" if dtype == "onvif" else "DLNA Speaker"),
                        "type": dtype,
                        "username": dev.get("username"),
                        "hasPassword": bool(dev.get("password")),
                        "controlUrl": dev.get("controlUrl"),
                        "renderingControlUrl": dev.get("renderingControlUrl"),
                        "isDefault": (prefix == default_ip)
                    })

        # ソート: カテゴリ順 -> デフォルト優先 -> 名前順
        results.sort(key=lambda d: (
            self.get_device_category_order(d),
            0 if d.get("isDefault") else 1,
            d.get("name", "")
        ))

        return results

    def find_device(self, query: str) -> Optional[Dict[str, Any]]:
        if not query:
            return None
        norm = query.strip()
        norm_lower = norm.lower()

        onvif_config = settings_manager.get().get("onvif", {})
        reg_devices = [d for d in onvif_config.get("registeredDevices", []) if d.get("enabled", True)]

        # ONVIF / DLNA プレフィックス
        if norm.startswith("onvif:") or norm.startswith("dlna:"):
            dtype, target_ip = norm.split(":", 1)
            found = next((d for d in reg_devices if (d.get("ip") == target_ip or d.get("id") == target_ip) and d.get("type", "onvif") == dtype), None)
            if found:
                return {
                    "id": found.get("id") or f"{dtype}_{found['ip'].replace('.', '_')}",
                    "name": found.get("name") or f"{dtype.upper()} ({found['ip']})",
                    "ip": f"{dtype}:{found['ip']}",
                    "rawIp": found["ip"],
                    "port": found.get("port", 8000),
                    "model": found.get("model", ""),
                    "type": dtype,
                    "username": found.get("username"),
                    "password": found.get("password"),
                    "controlUrl": found.get("controlUrl"),
                    "renderingControlUrl": found.get("renderingControlUrl")
                }

        # HomePod
        if norm.startswith("homepod:") or "homepod" in norm_lower:
            hp_target = norm.replace("homepod:", "")
            found = next((d for d in homepod_service.devices_cache if d.get("rawIp") == hp_target or d.get("name") == hp_target or d.get("ip") == f"homepod:{hp_target}"), None)
            if found:
                return found
            return {
                "id": f"homepod_{re.sub(r'[^a-zA-Z0-9]', '_', hp_target)}",
                "name": f"HomePod ({hp_target})",
                "ip": f"homepod:{hp_target}",
                "model": "Apple HomePod",
                "type": "homepod"
            }

        # Alexa (二重ラップ防止 ＆ キャッシュ照合)
        m_alexa = re.match(r"^Alexa \((.+)\)$", norm, re.IGNORECASE)
        clean_alexa = m_alexa.group(1) if m_alexa else norm.replace("alexa:", "")

        if norm.startswith("alexa:") or "alexa" in norm_lower or "echo" in norm_lower or m_alexa:
            return {
                "id": f"alexa_{clean_alexa.replace(' ', '_')}",
                "name": f"Alexa ({clean_alexa})",
                "ip": f"alexa:{clean_alexa}",
                "model": "Amazon Echo",
                "type": "alexa"
            }

        # Alexa キャッシュ内の名前照合（カスタムグループ名等で "echo" や "alexa" を含まない場合でもヒットさせる）
        if alexa_service.is_enabled() and alexa_service.devices_cache:
            for ad in alexa_service.devices_cache:
                raw_name = ad.get("rawName") or ad.get("name", "")
                ad_name = ad.get("name", "")
                if norm_lower in (raw_name.lower(), ad_name.lower(), ad.get("id", "").lower()):
                    c_name = raw_name or ad_name.replace("Alexa (", "").rstrip(")")
                    return {
                        "id": ad.get("id") or f"alexa_{c_name.replace(' ', '_')}",
                        "name": f"Alexa ({c_name})",
                        "ip": f"alexa:{c_name}",
                        "model": "Amazon Echo",
                        "type": "alexa"
                    }

        # 登録済み ONVIF / DLNA の名前一致
        for d in reg_devices:
            if (d.get("name") and d["name"].lower() == norm_lower) or d.get("ip") == norm:
                dtype = d.get("type", "onvif")
                return {
                    "id": d.get("id") or f"{dtype}_{d['ip'].replace('.', '_')}",
                    "name": d.get("name"),
                    "ip": f"{dtype}:{d['ip']}",
                    "rawIp": d["ip"],
                    "port": d.get("port", 8000),
                    "model": d.get("model", ""),
                    "type": dtype,
                    "username": d.get("username"),
                    "password": d.get("password"),
                    "controlUrl": d.get("controlUrl"),
                    "renderingControlUrl": d.get("renderingControlUrl")
                }

        # Google Cast IP / 完全一致 (グループ優先)
        if norm in self.devices:
            return self.devices[norm]

        for dev in self.devices.values():
            if dev.get("isGroup") and (dev.get("name", "").lower() == norm_lower or dev.get("ip") == norm or dev.get("id") == norm):
                return dev
        for dev in self.devices.values():
            if not dev.get("isGroup") and (dev.get("name", "").lower() == norm_lower or dev.get("ip") == norm or dev.get("id") == norm):
                return dev

        # 部分一致
        for dev in self.devices.values():
            if dev.get("isGroup") and (norm_lower in dev.get("name", "").lower() or dev.get("name", "").lower() in norm_lower):
                return dev
        for dev in self.devices.values():
            if not dev.get("isGroup") and (norm_lower in dev.get("name", "").lower()):
                return dev

        # IP 形式直打ち (例: 192.168.11.85 または 192.168.11.85:32094)
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$", norm):
            parts = norm.split(":")
            h = parts[0]
            p = int(parts[1]) if len(parts) > 1 else 8009
            return {
                "id": norm,
                "name": norm,
                "ip": norm,
                "host": h,
                "port": p,
                "model": "Custom IP",
                "type": "google",
                "isGroup": (p != 8009)
            }

        return None

    def scan_google_devices(self):
        """avahi-browse による Google Cast デバイス・グループ自動検出"""
        try:
            res = subprocess.run(
                ["avahi-browse", "-r", "-t", "-p", "_googlecast._tcp"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode != 0 or not res.stdout:
                return

            for line in res.stdout.splitlines():
                parts = line.split(";")
                if len(parts) > 7 and parts[0] == "=" and parts[2] == "IPv4" and parts[7]:
                    ip = parts[7]
                    port = int(parts[8]) if len(parts) > 8 and parts[8].isdigit() else 8009
                    txt_raw = parts[9] if len(parts) > 9 else ""
                    name = f"Cast-{ip}"
                    model = "Google Cast"

                    fn_m = re.search(r'"fn=([^"]+)"', txt_raw)
                    if fn_m:
                        name = decode_avahi_string(fn_m.group(1))
                    elif len(parts) > 3 and parts[3]:
                        name = decode_avahi_string(parts[3])

                    md_m = re.search(r'"md=([^"]+)"', txt_raw)
                    if md_m:
                        model = decode_avahi_string(md_m.group(1))

                    is_group = (model == "Google Cast Group") or (len(parts) > 3 and parts[3].startswith("Google-Cast-Group"))
                    key = f"group_{ip}_{port}" if is_group else ip
                    formatted_ip = f"{ip}:{port}" if is_group else ip

                    if key in self.devices:
                        existing = self.devices[key]
                        if fn_m:
                            existing["name"] = name
                        existing["port"] = port
                        existing["isGroup"] = is_group
                        continue

                    self.devices[key] = {
                        "id": f"group_{port}_{ip.replace('.', '_')}" if is_group else f"dev_{ip.replace('.', '_')}",
                        "name": name,
                        "ip": formatted_ip,
                        "host": ip,
                        "port": port,
                        "model": model,
                        "isGroup": is_group,
                        "type": "google"
                    }
        except Exception as e:
            print(f"[DeviceManager] Avahi scan error: {e}")

device_manager = DeviceManager()
