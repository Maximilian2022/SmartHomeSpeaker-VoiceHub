import asyncio
import socket
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any, Optional
import httpx
from app.core.logger import get_logger

log = get_logger("DLNA")

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900

class DlnaService:
    def __init__(self):
        self.cached_devices: List[Dict[str, Any]] = []

    async def scan_devices(self, timeout_sec: float = 3.5) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        log.info(f"Scanning for DLNA MediaRenderer devices (timeout={timeout_sec}s)...")

        def _send_and_recv():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.settimeout(0.5)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            try:
                # MediaRenderer 探索 & 全体探索の両方を送信
                msg_mr = (
                    "M-SEARCH * HTTP/1.1\r\n"
                    f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
                    'MAN: "ssdp:discover"\r\n'
                    "MX: 2\r\n"
                    "ST: urn:schemas-upnp-org:device:MediaRenderer:1\r\n\r\n"
                ).encode("utf-8")
                sock.sendto(msg_mr, (SSDP_ADDR, SSDP_PORT))

                msg_all = (
                    "M-SEARCH * HTTP/1.1\r\n"
                    f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
                    'MAN: "ssdp:discover"\r\n'
                    "MX: 2\r\n"
                    "ST: ssdp:all\r\n\r\n"
                ).encode("utf-8")
                sock.sendto(msg_all, (SSDP_ADDR, SSDP_PORT))
            except Exception as e:
                log.warning(f"SSDP send error: {e}")

            locs = set()
            import time
            import re
            start = time.time()
            while time.time() - start < timeout_sec:
                try:
                    data, addr = sock.recvfrom(65535)
                    text = data.decode("utf-8", errors="ignore")
                    m = re.search(r'LOCATION:\s*([^\r\n]+)', text, re.IGNORECASE)
                    if m:
                        loc = m.group(1).strip()
                        locs.add(loc)
                except socket.timeout:
                    continue
                except Exception:
                    break
            sock.close()
            return locs

        locations = await loop.run_in_executor(None, _send_and_recv)

        discovered = []
        async with httpx.AsyncClient(timeout=3.5, headers={"User-Agent": "VoiceHub-DLNA/1.0"}) as client:
            tasks = [self._fetch_device_info(client, loc) for loc in locations]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, dict) and res.get("controlUrl"):
                    discovered.append(res)

        discovered.sort(key=lambda d: d.get("ip", ""))
        self.cached_devices = discovered
        log.info(f"DLNA Scan complete: {len(discovered)} MediaRenderer device(s) found.")
        return discovered

    async def _fetch_device_info(self, client: httpx.AsyncClient, location: str) -> Optional[Dict[str, Any]]:
        try:
            parsed_url = urlparse(location)
            if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
                log.warning(f"[DLNA] 不正なスキームまたはホスト名の URL を拒絶 (SSRF防止): {location}")
                return None

            resp = await client.get(location)
            if resp.status_code != 200:
                return None

            ip = parsed_url.hostname or ""
            port = parsed_url.port or 80

            root = ET.fromstring(resp.content)

            def get_tag_text(tag_name: str) -> str:
                tag_lower = tag_name.lower()
                for el in root.iter():
                    if el.tag.split("}")[-1].lower() == tag_lower and el.text:
                        return el.text.strip()
                return ""

            friendly_name = get_tag_text("friendlyName") or f"DLNA Speaker ({ip})"
            model_name = get_tag_text("modelName") or "DLNA MediaRenderer"
            udn = get_tag_text("UDN") or ""

            avt_control = ""
            rc_control = ""

            for el in root.iter():
                if el.tag.split("}")[-1].lower() == "service":
                    stype = ""
                    curl = ""
                    for child in el:
                        ctag = child.tag.split("}")[-1].lower()
                        if ctag == "servicetype" and child.text:
                            stype = child.text.strip()
                        elif ctag == "controlurl" and child.text:
                            curl = child.text.strip()
                    if "avtransport" in stype.lower() and curl:
                        avt_control = urljoin(location, curl)
                    elif "renderingcontrol" in stype.lower() and curl:
                        rc_control = urljoin(location, curl)

            if not avt_control:
                return None

            return {
                "id": f"dlna_{ip.replace('.', '_')}_{port}",
                "name": friendly_name,
                "friendlyName": friendly_name,
                "ip": ip,
                "port": port,
                "model": model_name,
                "udn": udn,
                "location": location,
                "controlUrl": avt_control,
                "renderingControlUrl": rc_control,
                "type": "dlna",
                "category": "dlna",
                "supportsAudio": True,
                "status": "ok"
            }
        except Exception:
            return None

    async def play_audio(
        self,
        device: Dict[str, Any],
        audio_url: str,
        volume_level: Optional[float] = None
    ) -> bool:
        dev_name = device.get("name") or device.get("ip")
        control_url = device.get("controlUrl")
        if not control_url:
            log.warning(f"No controlUrl for {dev_name}")
            return False

        log.info(f"Playing audio on DLNA device '{dev_name}' -> URL: {audio_url}")
        async with httpx.AsyncClient(timeout=4.0) as client:
            # 1. 音量設定（RenderingControl があり、かつ指定がある場合）
            rc_url = device.get("renderingControlUrl")
            if rc_url and volume_level is not None:
                try:
                    vol_int = int(volume_level * 100 if volume_level <= 1.0 else volume_level)
                    vol_int = max(0, min(100, vol_int))
                    soap_vol = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:SetVolume xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">
      <InstanceID>0</InstanceID>
      <Channel>Master</Channel>
      <DesiredVolume>{vol_int}</DesiredVolume>
    </u:SetVolume>
  </s:Body>
</s:Envelope>"""
                    await client.post(
                        rc_url,
                        content=soap_vol.encode("utf-8"),
                        headers={
                            "Content-Type": 'text/xml; charset="utf-8"',
                            "SOAPAction": '"urn:schemas-upnp-org:service:RenderingControl:1#SetVolume"'
                        }
                    )
                except Exception as e:
                    log.warning(f"DLNA SetVolume error on {dev_name}: {e}")

            # 2. SetAVTransportURI
            soap_uri = f"""<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:SetAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <CurrentURI>{audio_url}</CurrentURI>
      <CurrentURIMetaData></CurrentURIMetaData>
    </u:SetAVTransportURI>
  </s:Body>
</s:Envelope>"""
            try:
                res1 = await client.post(
                    control_url,
                    content=soap_uri.encode("utf-8"),
                    headers={
                        "Content-Type": 'text/xml; charset="utf-8"',
                        "SOAPAction": '"urn:schemas-upnp-org:service:AVTransport:1#SetAVTransportURI"'
                    }
                )
                if res1.status_code >= 400:
                    log.error(f"DLNA SetAVTransportURI error (HTTP {res1.status_code}): {res1.text[:200]}")
                    return False
            except Exception as e:
                log.error(f"DLNA SetAVTransportURI request failed on {dev_name}: {e}")
                return False

            # 3. Play
            soap_play = """<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <s:Body>
    <u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
      <InstanceID>0</InstanceID>
      <Speed>1</Speed>
    </u:Play>
  </s:Body>
</s:Envelope>"""
            try:
                res2 = await client.post(
                    control_url,
                    content=soap_play.encode("utf-8"),
                    headers={
                        "Content-Type": 'text/xml; charset="utf-8"',
                        "SOAPAction": '"urn:schemas-upnp-org:service:AVTransport:1#Play"'
                    }
                )
                if res2.status_code < 400:
                    log.info(f"✅ DLNA playback started successfully on '{dev_name}'")
                    return True
                else:
                    log.error(f"DLNA Play command error (HTTP {res2.status_code}): {res2.text[:200]}")
                    return False
            except Exception as e:
                log.error(f"DLNA Play request failed on {dev_name}: {e}")
                return False

dlna_service = DlnaService()
