import asyncio
import re
import threading
import time
from typing import List, Dict, Any, Optional
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener, InterfaceChoice, IPVersion
from app.services.settings_service import settings_manager
from app.services.alexa_service import alexa_service
from app.services.homepod_service import homepod_service
from app.services.client_speaker_service import client_speaker_service

def decode_avahi_string(s: str) -> str:
    r"""後方互換用: 文字列をそのまま返却"""
    return s or ""

class CastServiceListener(ServiceListener):
    def __init__(self, manager: "DeviceManager"):
        self.manager = manager

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self._process_service(zc, type_, name)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self._process_service(zc, type_, name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def _process_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        try:
            info = zc.get_service_info(type_, name)
            if not info:
                return

            props = {}
            for k, v in info.properties.items():
                key = k.decode("utf-8", "ignore") if isinstance(k, bytes) else str(k)
                val = v.decode("utf-8", "ignore") if isinstance(v, bytes) else str(v)
                props[key] = val

            # IPv4 アドレスを優先取得
            ip = None
            for addr in info.parsed_scoped_addresses():
                if "." in addr:
                    ip = addr
                    break
            if not ip:
                return

            port = info.port or 8009
            fn = props.get("fn") or name.split(".")[0]
            md = props.get("md") or "Google Cast"
            is_group = (md == "Google Cast Group") or name.startswith("Google-Cast-Group")

            key = f"group_{ip}_{port}" if is_group else ip
            formatted_ip = f"{ip}:{port}" if is_group else ip

            dev_data = {
                "id": f"group_{port}_{ip.replace('.', '_')}" if is_group else f"dev_{ip.replace('.', '_')}",
                "name": fn,
                "ip": formatted_ip,
                "host": ip,
                "port": port,
                "model": md,
                "isGroup": is_group,
                "type": "google"
            }

            self.manager.update_device(key, dev_data)
        except Exception as e:
            print(f"[DeviceManager] Cast mDNS process error: {e}")

class DeviceManager:
    def __init__(self):
        self.devices: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._zc: Optional[Zeroconf] = None
        self._browser: Optional[ServiceBrowser] = None
        self._start_zeroconf()

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
            if dtype in ("client", "pc"): return 7
            if dtype == "dlna": return 8
            if dtype == "onvif": return 9
            if dtype == "tapo": return 10
            return 4

    async def get_devices(self) -> List[Dict[str, Any]]:
        default_ip = self.get_default_device_ip()
        favs = set(settings_manager.get_favorite_devices())
        results: List[Dict[str, Any]] = []

        # 1. Google Cast デバイス
        for dev in self.devices.values():
            d = dict(dev)
            d["isDefault"] = (d["ip"] == default_ip)
            d["isFavorite"] = (d.get("ip") in favs or d.get("id") in favs or d.get("name") in favs)
            results.append(d)

        # 2. Alexa デバイス
        if alexa_service.is_enabled():
            try:
                alexa_devs = await alexa_service.list_devices()
                for ad in alexa_devs:
                    d = dict(ad)
                    d["isDefault"] = (d.get("ip") == default_ip or d.get("id") == default_ip)
                    d["isFavorite"] = (d.get("ip") in favs or d.get("id") in favs or d.get("name") in favs)
                    results.append(d)
            except Exception as e:
                print(f"[DeviceManager] Alexa list error: {e}")

        # 3. HomePod デバイス
        try:
            hp_devs = homepod_service.devices_cache
            for hd in hp_devs:
                d = dict(hd)
                d["isDefault"] = (d["ip"] == default_ip)
                d["isFavorite"] = (d.get("ip") in favs or d.get("id") in favs or d.get("name") in favs)
                results.append(d)
        except Exception as e:
            print(f"[DeviceManager] HomePod list error: {e}")

        # 4. ONVIF & DLNA & Tapo 登録済みデバイス
        onvif_config = settings_manager.get().get("onvif", {})
        if onvif_config.get("enabled", True):
            for dev in onvif_config.get("registeredDevices", []):
                if dev.get("enabled", True):
                    dtype = dev.get("type", "onvif")
                    raw_ip = str(dev.get("ip", "")).replace("onvif:", "").replace("dlna:", "").replace("tapo:", "")
                    prefix = f"{dtype}:{raw_ip}"
                    default_model = "Tapo Camera" if dtype == "tapo" else ("ONVIF Speaker" if dtype == "onvif" else "DLNA Speaker")
                    dev_id = dev.get("id") or f"{dtype}_{raw_ip.replace('.', '_')}"
                    dev_name = dev.get("name") or dev.get("friendlyName") or f"{dtype.upper()} ({raw_ip})"
                    is_fav = (prefix in favs or raw_ip in favs or dev_id in favs or dev_name in favs)
                    results.append({
                        "id": dev_id,
                        "name": dev_name,
                        "ip": prefix,
                        "rawIp": raw_ip,
                        "port": dev.get("port", 8000),
                        "model": dev.get("model") or default_model,
                        "type": dtype,
                        "username": dev.get("username"),
                        "hasPassword": bool(dev.get("password") or dev.get("passwordHash")),
                        "controlUrl": dev.get("controlUrl"),
                        "renderingControlUrl": dev.get("renderingControlUrl"),
                        "isDefault": (prefix == default_ip),
                        "isFavorite": is_fav
                    })

        # 5. クライアントスピーカー (Windows / Mac / Linux PC)
        try:
            client_devs = client_speaker_service.get_active_devices()
            for cd in client_devs:
                d = dict(cd)
                d["isDefault"] = (d["ip"] == default_ip or d["id"] == default_ip)
                d["isFavorite"] = (d.get("ip") in favs or d.get("id") in favs or d.get("name") in favs)
                results.append(d)
        except Exception as e:
            print(f"[DeviceManager] Client speaker list error: {e}")

        # ソート: お気に入り最優先 -> カテゴリ順 -> デフォルト優先 -> 名前順
        results.sort(key=lambda d: (
            0 if d.get("isFavorite") else 1,
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

        # クライアントスピーカー (Windows / Mac / Linux PC)
        if norm.startswith("client:") or norm.startswith("pc:"):
            c = client_speaker_service.find_client(norm)
            if c:
                return c.to_device_dict()

        # ONVIF / DLNA / TAPO プレフィックス
        if norm.startswith("onvif:") or norm.startswith("dlna:") or norm.startswith("tapo:"):
            dtype, target_ip = norm.split(":", 1)
            target_ip = target_ip.replace("onvif:", "").replace("dlna:", "").replace("tapo:", "")
            found = next((d for d in reg_devices if (str(d.get("ip")).replace("onvif:", "").replace("dlna:", "").replace("tapo:", "") == target_ip or d.get("id") == target_ip) and d.get("type", "onvif") == dtype), None)
            if found:
                clean_ip = str(found["ip"]).replace("onvif:", "").replace("dlna:", "").replace("tapo:", "")
                return {
                    "id": found.get("id") or f"{dtype}_{clean_ip.replace('.', '_')}",
                    "name": found.get("name") or f"{dtype.upper()} ({clean_ip})",
                    "ip": f"{dtype}:{clean_ip}",
                    "rawIp": clean_ip,
                    "port": found.get("port", 8000),
                    "model": found.get("model", ""),
                    "type": dtype,
                    "username": found.get("username"),
                    "password": found.get("password"),
                    "passwordHash": found.get("passwordHash"),
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

        # 登録済み ONVIF / DLNA / Tapo の名前一致
        for d in reg_devices:
            clean_ip = str(d.get("ip", "")).replace("onvif:", "").replace("dlna:", "").replace("tapo:", "")
            if (d.get("name") and d["name"].lower() == norm_lower) or clean_ip == norm or d.get("ip") == norm:
                dtype = d.get("type", "onvif")
                return {
                    "id": d.get("id") or f"{dtype}_{clean_ip.replace('.', '_')}",
                    "name": d.get("name"),
                    "ip": f"{dtype}:{clean_ip}",
                    "rawIp": clean_ip,
                    "port": d.get("port", 8000),
                    "model": d.get("model", ""),
                    "type": dtype,
                    "username": d.get("username"),
                    "password": d.get("password"),
                    "passwordHash": d.get("passwordHash"),
                    "controlUrl": d.get("controlUrl"),
                    "renderingControlUrl": d.get("renderingControlUrl")
                }

        # クライアントスピーカーの名前照合
        c_by_name = client_speaker_service.find_client(norm)
        if c_by_name:
            return c_by_name.to_device_dict()

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

        # IP 形式直打ち (例: 192.168.1.100 または 192.168.1.100:32094)
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

    def _start_zeroconf(self):
        try:
            if self._zc is None:
                self._zc = Zeroconf(interfaces=InterfaceChoice.All, ip_version=IPVersion.All)
                self._listener = CastServiceListener(self)
                self._browser = ServiceBrowser(self._zc, "_googlecast._tcp.local.", self._listener)
        except Exception as e:
            print(f"[DeviceManager] Zeroconf start error: {e}")

    def update_device(self, key: str, data: Dict[str, Any]):
        with self._lock:
            if key in self.devices:
                existing = self.devices[key]
                if data.get("name"):
                    existing["name"] = data["name"]
                existing["port"] = data.get("port", existing.get("port", 8009))
                existing["isGroup"] = data.get("isGroup", existing.get("isGroup", False))
                existing["model"] = data.get("model", existing.get("model"))
            else:
                self.devices[key] = data

    def scan_google_devices(self, timeout: float = 2.0):
        """Zeroconf によるデバイス再スキャン（待機してmDNSパケット収集）"""
        try:
            if self._zc is None:
                self._start_zeroconf()
            # バックグラウンドリスナーがパケットを処理する待機時間
            time.sleep(timeout)
        except Exception as e:
            print(f"[DeviceManager] Zeroconf scan error: {e}")

    def close(self):
        """リソース解放"""
        try:
            if self._browser:
                self._browser.cancel()
                self._browser = None
            if self._zc:
                self._zc.close()
                self._zc = None
        except Exception as e:
            print(f"[DeviceManager] Zeroconf close error: {e}")

device_manager = DeviceManager()
