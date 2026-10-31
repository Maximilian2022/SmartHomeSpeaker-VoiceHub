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
from app.core.logger import get_logger

log = get_logger("DeviceManager")

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

            formatted_ip = f"{ip}:{port}" if is_group else ip
            # Cast グループは同名ごとに集約（複数IP/ポートの重複排除）
            key = f"group_{fn}" if is_group else ip
            dev_id = f"group_{re.sub(r'[^a-zA-Z0-9_]', '_', fn)}" if is_group else f"dev_{ip.replace('.', '_')}"

            dev_data = {
                "id": dev_id,
                "name": fn,
                "ip": formatted_ip,
                "host": ip,
                "port": port,
                "model": md,
                "isGroup": is_group,
                "type": "google"
            }
            if is_group:
                dev_data["candidateEndpoints"] = [{"host": ip, "port": port, "ip": formatted_ip}]

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

        # ソート: 有効端末優先 -> お気に入り最優先 -> カテゴリ順 -> デフォルト優先 -> 名前順
        for d in results:
            d["label"] = settings_manager.get_label_for_device(d.get("id"), d.get("ip"))
            d["disabled"] = settings_manager.is_device_disabled(d.get("id"), d.get("ip"), d.get("name"))

        results.sort(key=lambda d: (
            1 if d.get("disabled") else 0,
            0 if d.get("isFavorite") else 1,
            self.get_device_category_order(d),
            0 if d.get("isDefault") else 1,
            d.get("label") or d.get("name", "")
        ))

        return results

    def get_current_devices_sync(self) -> List[Dict[str, Any]]:
        """同期コンテキスト（find_device等）向けにキャッシュされている全デバイス辞書リストを返却"""
        results: List[Dict[str, Any]] = []

        # 1. Google Cast
        with self._lock:
            for dev in self.devices.values():
                d = dict(dev)
                d["label"] = settings_manager.get_label_for_device(d.get("id"), d.get("ip"))
                d["disabled"] = settings_manager.is_device_disabled(d.get("id"), d.get("ip"), d.get("name"))
                results.append(d)

        # 2. Alexa
        if alexa_service.is_enabled() and alexa_service.devices_cache:
            for ad in alexa_service.devices_cache:
                d = dict(ad)
                d["label"] = settings_manager.get_label_for_device(d.get("id"), d.get("ip"))
                d["disabled"] = settings_manager.is_device_disabled(d.get("id"), d.get("ip"), d.get("name"))
                results.append(d)

        # 3. HomePod
        if homepod_service.devices_cache:
            for hd in homepod_service.devices_cache:
                d = dict(hd)
                d["label"] = settings_manager.get_label_for_device(d.get("id"), d.get("ip"))
                d["disabled"] = settings_manager.is_device_disabled(d.get("id"), d.get("ip"), d.get("name"))
                results.append(d)

        # 4. ONVIF / DLNA
        onvif_config = settings_manager.get().get("onvif", {})
        if onvif_config.get("enabled", True):
            for dev in onvif_config.get("registeredDevices", []):
                if dev.get("enabled", True):
                    dtype = dev.get("type", "onvif")
                    raw_ip = str(dev.get("ip", "")).replace("onvif:", "").replace("dlna:", "").replace("tapo:", "")
                    prefix = f"{dtype}:{raw_ip}"
                    dev_id = dev.get("id") or f"{dtype}_{raw_ip.replace('.', '_')}"
                    dev_name = dev.get("name") or dev.get("friendlyName") or f"{dtype.upper()} ({raw_ip})"
                    d = {
                        "id": dev_id,
                        "name": dev_name,
                        "ip": prefix,
                        "rawIp": raw_ip,
                        "port": dev.get("port", 8000),
                        "model": dev.get("model", ""),
                        "type": dtype,
                        "label": settings_manager.get_label_for_device(dev_id, prefix),
                        "disabled": settings_manager.is_device_disabled(dev_id, prefix, dev_name)
                    }
                    results.append(d)

        # 5. Client
        for cd in client_speaker_service.get_active_devices(include_disabled=True):
            d = dict(cd)
            d["label"] = settings_manager.get_label_for_device(d.get("id"), d.get("ip"))
            d["disabled"] = settings_manager.is_device_disabled(d.get("id"), d.get("ip"), d.get("name"))
            results.append(d)

        return results

    def find_device(self, query: str) -> Optional[Dict[str, Any]]:
        if not query:
            return None
        norm = query.strip()
        norm_lower = norm.lower()

        # 0. カスタムラベル照合 (最優先・全体で一意)
        labels = settings_manager.get_device_labels()
        target_dev_key = None
        for k, v in labels.items():
            if v and str(v).strip().lower() == norm_lower:
                target_dev_key = k
                break

        if target_dev_key:
            # 現在の検出デバイスから検索
            for d in self.get_current_devices_sync():
                if d.get("id") == target_dev_key or d.get("ip") == target_dev_key or d.get("rawIp") == target_dev_key:
                    return d
            # まだキャッシュに完全一致しない場合は target_dev_key でフォールバック照合
            if target_dev_key.lower() != norm_lower:
                fallback_found = self.find_device(target_dev_key)
                if fallback_found:
                    return fallback_found

        onvif_config = settings_manager.get().get("onvif", {})
        reg_devices = [d for d in onvif_config.get("registeredDevices", []) if d.get("enabled", True)]

        # クライアントスピーカー (Windows / Mac / Linux PC)
        if norm.startswith("client:") or norm.startswith("pc:"):
            c_dev = client_speaker_service.find_device_dict(norm)
            if c_dev:
                return c_dev

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

        # クライアントスピーカーの名前・出力デバイス名照合
        c_dev_by_name = client_speaker_service.find_device_dict(norm)
        if c_dev_by_name:
            return c_dev_by_name

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
                if existing.get("isGroup") and data.get("isGroup"):
                    # 同名グループの候補エンドポイント（他スピーカーIP/ポート）を蓄積
                    endpoints = existing.setdefault("candidateEndpoints", [])
                    new_ep = {"host": data.get("host"), "port": data.get("port"), "ip": data.get("ip")}
                    if not any(ep.get("host") == new_ep["host"] and ep.get("port") == new_ep["port"] for ep in endpoints):
                        endpoints.append(new_ep)
                else:
                    existing["port"] = data.get("port", existing.get("port", 8009))
                    existing["isGroup"] = data.get("isGroup", existing.get("isGroup", False))
                    existing["model"] = data.get("model", existing.get("model"))
            else:
                self.devices[key] = data

    def promote_group_endpoint(self, group_name_or_id: str, new_host: str, new_port: int) -> Optional[str]:
        """発話成功時などに、Google Cast グループの代表エンドポイントを切り替え、デフォルト端末も成り代わり更新"""
        with self._lock:
            target_dev = None
            for d in self.devices.values():
                if d.get("isGroup") and (d.get("name") == group_name_or_id or d.get("id") == group_name_or_id or d.get("ip") == group_name_or_id):
                    target_dev = d
                    break
            if not target_dev:
                return None

            old_ip = target_dev.get("ip")
            new_formatted_ip = f"{new_host}:{new_port}"
            target_dev["host"] = new_host
            target_dev["port"] = new_port
            target_dev["ip"] = new_formatted_ip

            # エンドポイントリストの先頭へ昇格
            endpoints = target_dev.setdefault("candidateEndpoints", [])
            matched_ep = next((ep for ep in endpoints if ep.get("host") == new_host and ep.get("port") == new_port), None)
            if matched_ep:
                endpoints.remove(matched_ep)
                endpoints.insert(0, matched_ep)
            else:
                endpoints.insert(0, {"host": new_host, "port": new_port, "ip": new_formatted_ip})

            # デフォルト端末として設定されていた場合は自動で成り代わり更新
            current_default = settings_manager.get_default_device_id()
            if current_default and (current_default == old_ip or current_default == target_dev.get("id") or current_default in [ep.get("ip") for ep in endpoints]):
                settings_manager.set_default_device_id(new_formatted_ip)
                log.info(f"[DeviceManager] デフォルト端末を Google Cast グループの新エンドポイント '{new_formatted_ip}' に自動成り代わり更新しました")

            return new_formatted_ip

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
