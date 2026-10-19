import asyncio
import base64
import hashlib
import json
import re
import secrets
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from urllib.parse import urlencode, parse_qs, urlparse, urlunparse

import aiohttp
from aiohttp import web

from app.config import DATA_DIR, settings

ALEXA_APP_VERSION = "2.2.651540.0"
CREDENTIALS_FILE = DATA_DIR / "alexa_credentials.json"

SUCCESS_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Amazon Alexa 連携完了</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f172a;
      color: #f8fafc;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
    }
    .card {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 16px;
      padding: 40px 32px;
      text-align: center;
      max-width: 480px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .icon {
      font-size: 56px;
      margin-bottom: 16px;
    }
    h1 {
      font-size: 24px;
      color: #4ade80;
      margin-top: 0;
      margin-bottom: 12px;
    }
    p {
      color: #94a3b8;
      line-height: 1.6;
      margin-bottom: 24px;
    }
    .close-btn {
      background: #3b82f6;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 15px;
      font-weight: bold;
      cursor: pointer;
    }
    .close-btn:hover {
      background: #2563eb;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✅</div>
    <h1>Amazon Alexa 連携が完了しました！</h1>
    <p>認証トークンの取得に成功しました。<br>このウィンドウまたはタブを閉じて、Voice Hub の管理画面にお戻りください。</p>
    <button class="close-btn" onclick="window.close()">ウィンドウを閉じる</button>
  </div>
</body>
</html>
"""

class AlexaAuthProxy:
    def __init__(
        self,
        host_ip: str,
        port: int = 8081,
        amazon_page: str = "amazon.co.jp",
        on_success: Optional[Callable[[str], Any]] = None
    ):
        self.host_ip = host_ip
        self.port = port
        self.amazon_page = amazon_page
        self.on_success = on_success
        
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        self.cookies: Dict[str, str] = {}
        self.is_running = False
        self.last_error: Optional[str] = None
        
        # PKCE parameters
        self.code_verifier = secrets.token_urlsafe(32)
        h = hashlib.sha256(self.code_verifier.encode("utf-8")).digest()
        self.code_challenge = base64.urlsafe_b64encode(h).decode("utf-8").rstrip("=")
        
        # Device ID
        raw_dev = secrets.token_hex(16).upper()
        self.device_id = raw_dev.encode().hex() + "23413249564c5635564d32573831"
        
        # FRC (313 random bytes base64)
        self.frc = base64.b64encode(secrets.token_bytes(313)).decode("utf-8")
        
        # map-md
        self.map_md = base64.b64encode(json.dumps({
            "device_user_dictionary": [],
            "device_registration_data": {"software_version": "1"},
            "app_identifier": {"app_version": ALEXA_APP_VERSION, "bundle_id": "com.amazon.echo"}
        }).encode("utf-8")).decode("utf-8")

    @property
    def proxy_base_url(self) -> str:
        return f"http://{self.host_ip}:{self.port}"

    def build_initial_signin_url(self) -> str:
        handle = "_jp" if self.amazon_page.endswith(".jp") else ""
        lang = "ja_JP" if self.amazon_page.endswith(".jp") else "en_US"
        query = {
            "openid.return_to": f"https://www.{self.amazon_page}/ap/maplanding",
            "openid.assoc_handle": f"amzn_dp_project_dee_ios{handle}",
            "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
            "pageId": f"amzn_dp_project_dee_ios{handle}",
            "accountStatusPolicy": "P1",
            "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.mode": "checkid_setup",
            "openid.ns.oa2": f"http://www.{self.amazon_page}/ap/ext/oauth/2",
            "openid.oa2.client_id": f"device:{self.device_id}",
            "openid.ns.pape": "http://specs.openid.net/extensions/pape/1.0",
            "openid.oa2.response_type": "code",
            "openid.ns": "http://specs.openid.net/auth/2.0",
            "openid.pape.max_auth_age": "0",
            "openid.oa2.scope": "device_auth_access",
            "openid.oa2.code_challenge_method": "S256",
            "openid.oa2.code_challenge": self.code_challenge,
            "language": lang
        }
        return f"https://www.{self.amazon_page}/ap/signin?" + urlencode(query)

    def _replace_hosts_forward(self, content: str) -> str:
        """Replace Amazon hosts with proxy host in responses sent to browser."""
        base = self.proxy_base_url
        content = content.replace(f"https://www.{self.amazon_page}", base)
        content = content.replace(f"https://alexa.{self.amazon_page}", base)
        content = content.replace(f"https://{self.amazon_page}", base)
        return content

    def _replace_hosts_backward(self, content: str) -> str:
        """Replace proxy host with Amazon hosts in requests sent to Amazon."""
        base = self.proxy_base_url
        return content.replace(base, f"https://www.{self.amazon_page}")

    async def _handle_success(self, auth_code: str) -> web.Response:
        print(f"[AlexaProxy] Captured auth_code: {auth_code[:10]}... exchanging for token...")
        try:
            token = await self.exchange_code_for_token(auth_code)
            if token:
                print(f"[AlexaProxy] Token exchange SUCCESS! refreshToken: {token[:12]}...")
                # Save credentials
                cred_data = {
                    "refreshToken": token,
                    "amazonPage": self.amazon_page,
                    "deviceId": self.device_id,
                    "loginDate": asyncio.get_event_loop().time()
                }
                CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
                CREDENTIALS_FILE.write_text(json.dumps(cred_data, indent=2), encoding="utf-8")
                settings.refresh_token = token
                
                if self.on_success:
                    try:
                        res = self.on_success(token)
                        if asyncio.iscoroutine(res):
                            asyncio.create_task(res)
                    except Exception as ex:
                        print(f"[AlexaProxy] on_success callback error: {ex}")

                # Auto stop proxy after 5 seconds
                asyncio.get_event_loop().call_later(5, lambda: asyncio.create_task(self.stop()))
                return web.Response(text=SUCCESS_HTML, content_type="text/html", status=200)
            else:
                self.last_error = "トークンの取得に失敗しました (Amazon からのレスポンスが無効です)"
                return web.Response(text=f"<h3>エラー: トークンの取得に失敗しました。</h3>", content_type="text/html", status=500)
        except Exception as e:
            self.last_error = str(e)
            print(f"[AlexaProxy] Token exchange error: {e}")
            return web.Response(text="<h3>エラーが発生しました。詳細はサーバーログを確認してください。</h3>", content_type="text/html", status=500)

    async def exchange_code_for_token(self, auth_code: str) -> Optional[str]:
        register_url = f"https://api.{self.amazon_page}/auth/register"
        website_cookies = [{"Name": k, "Value": v} for k, v in self.cookies.items()]

        payload = {
            "requested_extensions": ["device_info", "customer_info"],
            "cookies": {
                "domain": f".{self.amazon_page}",
                "website_cookies": website_cookies
            },
            "registration_data": {
                "domain": "Device",
                "app_version": ALEXA_APP_VERSION,
                "device_serial_number": self.device_id,
                "device_type": "A2IVLV5VM2W81",
                "device_name": "%FIRST_NAME%'s Alexa",
                "os_version": "16.6",
                "device_model": "iPhone",
                "app_name": "Amazon Alexa"
            },
            "auth_data": {
                "client_id": self.device_id,
                "authorization_code": auth_code,
                "code_verifier": self.code_verifier,
                "code_algorithm": "SHA-256",
                "client_domain": "DeviceLegacy"
            },
            "user_context_map": {
                "frc": self.frc
            },
            "requested_token_type": ["bearer", "mac_dms", "website_cookies"]
        }

        cookie_hdr = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
        headers = {
            "User-Agent": f"AmazonWebView/Amazon Alexa/{ALEXA_APP_VERSION}/iOS/16.6/iPhone",
            "Accept-Language": "ja-JP",
            "Accept-Charset": "utf-8",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Cookie": cookie_hdr,
            "Accept": "application/json",
            "x-amzn-identity-auth-domain": f"api.{self.amazon_page}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(register_url, json=payload, headers=headers) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text)
                except Exception:
                    print(f"[AlexaProxy] Non-JSON response from register API: {text[:200]}")
                    return None
                
                if "response" in data and "success" in data["response"]:
                    tokens = data["response"]["success"].get("tokens", {})
                    bearer = tokens.get("bearer", {})
                    refresh_token = bearer.get("refresh_token")
                    return refresh_token
                else:
                    print(f"[AlexaProxy] Register response failed: {data}")
                    return None

    async def handle_proxy(self, request: web.Request) -> web.StreamResponse:
        path = request.path
        query_str = request.query_string
        
        # 1. Success page
        if path == "/cookie-success":
            return web.Response(text=SUCCESS_HTML, content_type="text/html", status=200)

        # 2. Check for authorization_code in query parameters or maplanding
        auth_code = request.query.get("openid.oa2.authorization_code")
        if auth_code:
            return await self._handle_success(auth_code)

        # 3. Root request redirects to signin flow
        if path == "/" or path == "":
            initial_url = self.build_initial_signin_url()
            parsed = urlparse(initial_url)
            local_target = f"{parsed.path}?{parsed.query}"
            return web.HTTPFound(location=local_target)

        # 4. Proxy request to Amazon
        target_url = f"https://www.{self.amazon_page}{path}"
        if query_str:
            target_url += f"?{query_str}"

        # Collect client cookies
        for k, v in request.cookies.items():
            self.cookies[k] = v

        # Read body if POST
        body = await request.read()
        if body and ("application/x-www-form-urlencoded" in request.headers.get("Content-Type", "")):
            try:
                decoded = body.decode("utf-8")
                fixed = self._replace_hosts_backward(decoded)
                body = fixed.encode("utf-8")
            except Exception:
                pass

        # Build upstream headers
        out_headers = {}
        for h, v in request.headers.items():
            if h.lower() in ("host", "content-length", "accept-encoding", "connection"):
                continue
            out_headers[h] = v
        out_headers["Host"] = f"www.{self.amazon_page}"
        out_headers["User-Agent"] = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
        if self.cookies:
            out_headers["Cookie"] = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])

        try:
            async with aiohttp.ClientSession(auto_decompress=True) as session:
                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=out_headers,
                    data=body,
                    allow_redirects=False
                ) as upstream_resp:
                    
                    # Intercept cookies
                    for cookie_key, mox_cookie in upstream_resp.cookies.items():
                        self.cookies[cookie_key] = mox_cookie.value

                    # Check Location redirect
                    location = upstream_resp.headers.get("Location")
                    if location:
                        # Check if location contains code
                        parsed_loc = urlparse(location)
                        loc_params = parse_qs(parsed_loc.query)
                        if "openid.oa2.authorization_code" in loc_params:
                            code = loc_params["openid.oa2.authorization_code"][0]
                            return await self._handle_success(code)

                        # Rewrite Location
                        new_location = self._replace_hosts_forward(location)
                        resp = web.HTTPFound(location=new_location)
                        # Set cookies to client
                        for k, v in upstream_resp.cookies.items():
                            resp.set_cookie(k, v.value, path="/")
                        return resp

                    content_type = upstream_resp.headers.get("Content-Type", "")
                    resp_body = await upstream_resp.read()

                    # Rewrite HTML / text bodies
                    if "text/" in content_type or "json" in content_type:
                        try:
                            text_body = resp_body.decode(upstream_resp.charset or "utf-8", errors="replace")
                            text_body = self._replace_hosts_forward(text_body)
                            resp = web.Response(
                                text=text_body,
                                content_type=content_type.split(";")[0],
                                status=upstream_resp.status
                            )
                        except Exception:
                            resp = web.Response(
                                body=resp_body,
                                content_type=content_type.split(";")[0],
                                status=upstream_resp.status
                            )
                    else:
                        resp = web.Response(
                            body=resp_body,
                            content_type=content_type.split(";")[0],
                            status=upstream_resp.status
                        )

                    # Propagate cookies
                    for k, v in upstream_resp.cookies.items():
                        resp.set_cookie(k, v.value, path="/")

                    return resp
        except Exception as e:
            print(f"[AlexaProxy] Upstream error for {target_url}: {e}")
            return web.Response(text="Proxy error: Failed to communicate with upstream service", status=502)

    async def start(self):
        if self.is_running:
            return
        self.app = web.Application()
        self.app.router.add_route("*", "/{path:.*}", self.handle_proxy)
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
        await self.site.start()
        self.is_running = True
        print(f"[AlexaProxy] Python Alexa Auth Proxy started at http://{self.host_ip}:{self.port}")

    async def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        if self.site:
            await self.site.stop()
            self.site = None
        if self.runner:
            await self.runner.cleanup()
            self.runner = None
        print("[AlexaProxy] Python Alexa Auth Proxy stopped.")

# Singleton instance holder
alexa_proxy_instance: Optional[AlexaAuthProxy] = None
