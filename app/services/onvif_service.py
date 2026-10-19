import asyncio
import os
import re
import socket
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import httpx
from app.config import settings
from app.services.settings_service import settings_manager
from app.services.tts_service import tts_service
from app.services.dlna_service import dlna_service
from app.core.logger import get_logger

log = get_logger("ONVIF")

WS_DISCOVERY_PROBE = """<?xml version="1.0" encoding="utf-8"?>
<Envelope xmlns:tds="http://www.onvif.org/ver10/device/wsdl" 
          xmlns="http://www.w3.org/2003/05/soap-envelope" 
          xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <Header xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing">
    <wsa:MessageID>urn:uuid:{msg_id}</wsa:MessageID>
    <wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
    <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</wsa:Action>
  </Header>
  <Body>
    <Probe xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
           xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
           xmlns="http://schemas.xmlsoap.org/ws/2005/04/discovery">
      <Types>dn:NetworkVideoTransmitter tds:Device</Types>
      <Scopes />
    </Probe>
  </Body>
</Envelope>"""

class OnvifService:
    def __init__(self):
        self.cached_scan_results: List[Dict[str, Any]] = []
        self.is_scanning = False
        self.go2rtc_api_url = settings.go2rtc_api_url
        # カメラ複数台同時再生時の go2rtc / ネットワーク飽和防止用セマフォ
        self._semaphore = asyncio.Semaphore(3)

    async def send_soap(
        self,
        url_str: str,
        action: str,
        body_xml: str,
        username: str = "",
        password: str = ""
    ) -> str:
        # ONVIF Profile T 規格準拠: HTTP Digest 認証 (RFC 7616 / RFC 2617)
        soap_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:tds="http://www.onvif.org/ver10/device/wsdl"
               xmlns:trt="http://www.onvif.org/ver10/media/wsdl">
  <soap:Body>
    {body_xml}
  </soap:Body>
</soap:Envelope>"""

        headers = {
            "Content-Type": f'application/soap+xml; charset=utf-8; action="{action}"'
        }
        auth = httpx.DigestAuth(username, password) if username and password else None
        async with httpx.AsyncClient(auth=auth, timeout=4.0, verify=False) as client:
            resp = await client.post(url_str, content=soap_xml.encode("utf-8"), headers=headers)
            if 200 <= resp.status_code < 300:
                return resp.text
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")

    async def scan_devices(
        self,
        timeout_ms: int = 3500,
        username: str = "",
        password: str = ""
    ) -> List[Dict[str, Any]]:
        if self.is_scanning:
            return self.cached_scan_results
        self.is_scanning = True

        loop = asyncio.get_running_loop()
        discovered_map: Dict[str, Dict[str, Any]] = {}

        def _do_ws_discovery():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.settimeout(timeout_ms / 1000.0)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            msg_id = str(uuid.uuid4())
            probe_data = WS_DISCOVERY_PROBE.format(msg_id=msg_id).encode("utf-8")

            try:
                sock.sendto(probe_data, ("239.255.255.250", 3702))
                sock.sendto(probe_data, ("255.255.255.255", 3702))
            except Exception as e:
                print(f"[OnvifService] WS-Discovery send error: {e}")

            start_t = loop.time()
            limit = timeout_ms / 1000.0
            while loop.time() - start_t < limit:
                try:
                    data, addr = sock.recvfrom(65535)
                    ip = addr[0]
                    raw = data.decode("utf-8", errors="ignore")
                    if ip not in discovered_map:
                        discovered_map[ip] = {
                            "ip": ip,
                            "xaddrs": [],
                            "scopes": [],
                            "raw": raw
                        }
                    dev = discovered_map[ip]
                    x_m = re.search(r"<[^:]*:?XAddrs[^>]*>([^<]+)</[^:]*:?XAddrs>", raw, re.I)
                    if x_m:
                        for x in x_m.group(1).split():
                            if x not in dev["xaddrs"]:
                                dev["xaddrs"].append(x)
                    s_m = re.search(r"<[^:]*:?Scopes[^>]*>([^<]+)</[^:]*:?Scopes>", raw, re.I)
                    if s_m:
                        for s in s_m.group(1).split():
                            if s not in dev["scopes"]:
                                dev["scopes"].append(s)
                except socket.timeout:
                    break
                except Exception:
                    break
            sock.close()

        await loop.run_in_executor(None, _do_ws_discovery)

        onvif_config = settings_manager.get().get("onvif", {})
        default_user = username or onvif_config.get("defaultUsername", "admin")
        default_pass = password or onvif_config.get("defaultPassword", "")
        registered_list = onvif_config.get("registeredDevices", [])

        results = []
        for ip, info in discovered_map.items():
            port = 8000
            onvif_url = f"http://{ip}:8000/onvif/device_service"
            if info["xaddrs"]:
                try:
                    p = urlparse(info["xaddrs"][0])
                    port = p.port or 80
                    onvif_url = info["xaddrs"][0]
                except Exception:
                    pass
            elif ip.endswith((".211", ".212", ".235")):
                port = 2020
                onvif_url = f"http://{ip}:2020/onvif/device_service"

            model = "ONVIF Camera"
            custom_name = ""
            generic_name = ""
            is_profile_t = False
            auth_status = "unauthenticated"

            for s in info["scopes"]:
                dec = s
                if "Profile/T" in dec:
                    is_profile_t = True
                if "hardware/" in dec:
                    model = dec.split("hardware/")[1].split("/")[0]
                if "odm:name:" in dec:
                    custom_name = dec.split("odm:name:")[1].strip()
                elif "name/" in dec:
                    n = dec.split("name/")[1].split("/")[0].strip()
                    if n and n not in ("IPC", "IPC-BO", "Camera"):
                        generic_name = n

            # 登録済み設定の確認
            reg = next((r for r in registered_list if r.get("ip") == ip), None)
            u = (reg and reg.get("username")) or default_user
            p = (reg and reg.get("password")) or default_pass

            if p:
                try:
                    scopes_xml = await self.send_soap(
                        onvif_url,
                        "http://www.onvif.org/ver10/device/wsdl/GetScopes",
                        "<tds:GetScopes/>",
                        u, p
                    )
                    auth_status = "ok"
                    for item_m in re.finditer(r"<[^:]*:?ScopeItem[^>]*>([^<]+)</[^:]*:?ScopeItem>", scopes_xml, re.I):
                        val = item_m.group(1).strip()
                        if "Profile/T" in val:
                            is_profile_t = True
                        if "odm:name:" in val:
                            custom_name = val.split("odm:name:")[1].strip()
                        elif "hardware/" in val:
                            model = val.split("hardware/")[1].split("/")[0].strip()
                        elif "name/" in val and not custom_name:
                            n = val.split("name/")[1].split("/")[0].strip()
                            if n and n not in ("IPC", "IPC-BO"):
                                generic_name = n

                    # GetDeviceInformation
                    try:
                        dev_info_xml = await self.send_soap(
                            onvif_url,
                            "http://www.onvif.org/ver10/device/wsdl/GetDeviceInformation",
                            "<tds:GetDeviceInformation/>",
                            u, p
                        )
                        m_m = re.search(r"<[^:]*:?Model[^>]*>([^<]+)</[^:]*:?Model>", dev_info_xml, re.I)
                        if m_m and m_m.group(1).strip():
                            model = m_m.group(1).strip()
                    except Exception:
                        pass
                except Exception as e:
                    auth_status = "unauthorized" if "401" in str(e) else "error"

            friendly_name = custom_name or generic_name or ""
            display_name = friendly_name or (model if model != "ONVIF Camera" else f"Camera-{ip}")

            results.append({
                "id": f"onvif_{ip.replace('.', '_')}",
                "ip": ip,
                "port": port,
                "onvifUrl": onvif_url,
                "model": model,
                "name": display_name,
                "friendlyName": friendly_name,
                "status": auth_status,
                "isProfileT": is_profile_t,
                "hasProfileT": is_profile_t,
                "supportsAudio": is_profile_t,
                "audioBackchannelSupported": is_profile_t,
                "type": "onvif",
                "category": "onvif",
                "isRegistered": any(r.get("ip") == ip and r.get("enabled", True) for r in registered_list)
            })

        results.sort(key=lambda d: [int(x) for x in d["ip"].split(".")])
        self.cached_scan_results = results
        self.is_scanning = False
        return results

    async def scan_all_devices(
        self,
        timeout_ms: int = 3500,
        username: str = "",
        password: str = ""
    ) -> List[Dict[str, Any]]:
        """ONVIFカメラとDLNAスピーカーを並行スキャンして一覧に統合"""
        onvif_task = asyncio.create_task(self.scan_devices(timeout_ms, username, password))
        dlna_task = asyncio.create_task(dlna_service.scan_devices(timeout_ms / 1000.0))

        onvif_res, dlna_res = await asyncio.gather(onvif_task, dlna_task, return_exceptions=True)
        all_devices = []
        if isinstance(onvif_res, list):
            all_devices.extend(onvif_res)
        if isinstance(dlna_res, list):
            # 登録済み状態の付与
            reg_list = settings_manager.get().get("onvif", {}).get("registeredDevices", [])
            for d in dlna_res:
                d["isRegistered"] = any(r.get("ip") == d["ip"] and r.get("enabled", True) for r in reg_list)
            all_devices.extend(dlna_res)

        return all_devices

    async def play_audio(
        self,
        camera: Dict[str, Any],
        audio_url_or_path: str,
        duration: float = 8.0,
        volume_level: Optional[float] = None
    ) -> Dict[str, Any]:
        onvif_config = settings_manager.get().get("onvif", {})
        raw_ip = camera.get("rawIp") or camera.get("ip", "").replace("onvif:", "")
        username = camera.get("username")
        password = camera.get("password")
        if not password or not username:
            for reg in onvif_config.get("registeredDevices", []):
                if reg.get("ip") == raw_ip:
                    if not username:
                        username = reg.get("username")
                    if not password:
                        password = reg.get("password")
                    break
        username = username or onvif_config.get("defaultUsername", "admin")
        password = password or onvif_config.get("defaultPassword", "")
        rtsp_port = camera.get("rtspPort", 554)
        onvif_port = camera.get("port", 8000)
        stream_name = f"onvif_{raw_ip.replace('.', '_')}"

        # 1. go2rtc にストリームを登録 (PUT)
        rtsp_url = f"rtsp://{username}:{password}@{raw_ip}:{rtsp_port}/h264Preview_01_main"
        onvif_src_url = f"onvif://{username}:{password}@{raw_ip}:{onvif_port}"
        await self._ensure_go2rtc_stream(stream_name, rtsp_url, onvif_src_url)

        # 2. 音量調整 (volumeLevel 指定時)
        resolved_url = audio_url_or_path
        if volume_level is not None:
            norm_vol = volume_level / 100.0 if volume_level > 1.0 else volume_level
            norm_vol = max(0.01, min(2.0, norm_vol))
            if norm_vol != 1.0:
                resolved_url = await tts_service.adjust_volume(audio_url_or_path, norm_vol)

        if not resolved_url.startswith(("http://", "https://")):
            filename = os.path.basename(resolved_url)
            resolved_url = f"http://127.0.0.1:8080/voice/{filename}"

        # 3. 音声を go2rtc バックチャンネルにプッシュ (PCMU)
        src_param = f"ffmpeg:{resolved_url}#audio=pcmu#input=file"
        params = {"dst": stream_name, "src": src_param}
        push_url = f"{self.go2rtc_api_url}/api/streams"

        log.info(f"Starting audio playback on {camera.get('name', raw_ip)} ({raw_ip}) URL: {resolved_url}")

        async with self._semaphore:
            # タイムアウトを15秒に拡大 & can't find consumer 時の自動リトライ (最大2回)
            last_err = None
            for attempt in range(2):
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.post(push_url, params=params)
                        if resp.status_code == 200:
                            last_err = None
                            break
                        err_text = resp.text
                        if "consumer" in err_text and attempt == 0:
                            log.warning(f"go2rtc consumer not ready yet for {stream_name}, retrying stream register and waiting 0.8s...")
                            await self._ensure_go2rtc_stream(stream_name, rtsp_url, onvif_src_url)
                            await asyncio.sleep(0.8)
                            continue
                        raise RuntimeError(f"go2rtc 再生リクエスト失敗 (HTTP {resp.status_code}): {err_text}")
                except httpx.ReadTimeout:
                    if attempt == 0:
                        log.warning(f"go2rtc ReadTimeout on {stream_name}, retrying once with 0.8s delay...")
                        await asyncio.sleep(0.8)
                        continue
                    raise RuntimeError(f"go2rtc 接続タイムアウト (カメラ側応答遅延): {stream_name}")
                except Exception as e:
                    last_err = e
                    if attempt == 0:
                        await asyncio.sleep(0.8)
                        continue
                    raise

            if last_err:
                raise last_err

        # 再生完了待機後にセッション安全切断
        play_sec = max(3.0, duration + 1.5)
        asyncio.create_task(self._cleanup_stream_session(stream_name, play_sec))

        return {"success": True, "message": "Playback started"}

    async def _cleanup_stream_session(self, stream_name: str, delay_sec: float):
        await asyncio.sleep(delay_sec)
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                # 1. アクティブなコンシューマ切断
                await client.post(f"{self.go2rtc_api_url}/api/streams", params={"dst": stream_name, "src": ""})
                # 2. カメラのRTSP認証情報を含むストリーム定義自体の削除 (情報漏洩防止)
                await client.delete(f"{self.go2rtc_api_url}/api/streams", params={"src": stream_name})
                log.info(f"Stream session and definition cleared for {stream_name}")
        except Exception as e:
            log.warning(f"ONVIF stream cleanup warning for {stream_name}: {e}")

    async def _ensure_go2rtc_stream(self, stream_name: str, rtsp_url: str, onvif_url: str):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # go2rtc PUT: src パラメータを複数渡す
                put_url = f"{self.go2rtc_api_url}/api/streams"
                await client.put(put_url, params={"name": stream_name, "src": [rtsp_url, onvif_url]})
        except Exception as e:
            log.warning(f"go2rtc Stream Register Warning for {stream_name}: {e}")

onvif_service = OnvifService()
