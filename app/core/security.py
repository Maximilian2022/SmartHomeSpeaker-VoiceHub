import hashlib
import hmac
import ipaddress
from typing import Optional
from fastapi import Request, HTTPException, status
from app.config import settings

ACTIVE_SESSIONS = set()

def is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback
    except ValueError:
        return False

def is_tunnel_request(request: Request) -> bool:
    headers = request.headers
    if "cf-ray" in headers or "cf-connecting-ip" in headers or "cf-ipcountry" in headers:
        return True
    host = headers.get("host", "").split(":")[0]
    if settings.tunnel_domain and host.lower() == settings.tunnel_domain.lower():
        return True
    return False

def check_tunnel_access(request: Request):
    """
    Cloudflare Tunnel からのアクセス時、Webhook エンドポイント (/api/say, /api/webhook) 以外は 403 で遮断
    """
    if is_tunnel_request(request):
        path = request.url.path
        if not (path == "/api/say" or path == "/api/webhook"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Web GUI and management APIs are restricted to internal LAN."
            )

def validate_webhook_token(request: Request, body_token: Optional[str] = None):
    expected_token = settings.webhook_token
    if not expected_token:
        return True

    # 1. 宅内ブラウザGUIからの同一オリジンアクセスは自動免除
    client_host = request.client.host if request.client else ""
    sec_fetch_site = request.headers.get("sec-fetch-site", "")
    referer = request.headers.get("referer", "")
    if is_private_ip(client_host) and (sec_fetch_site in ("same-origin", "same-site") or referer):
        return True

    # 2. Authorization: Bearer <token>
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if hmac.compare_digest(token, expected_token):
            return True

    # 3. X-API-KEY / X-Webhook-Token
    api_key = request.headers.get("x-api-key")
    if api_key and hmac.compare_digest(api_key, expected_token):
        return True
    wh_token = request.headers.get("x-webhook-token")
    if wh_token and hmac.compare_digest(wh_token, expected_token):
        return True

    # 4. Query parameter ?token=
    q_token = request.query_params.get("token")
    if q_token and hmac.compare_digest(q_token, expected_token):
        return True

    # 5. JSON Body token
    if body_token and hmac.compare_digest(body_token, expected_token):
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Invalid or missing Webhook token."
    )

def generate_session_token(password: str) -> str:
    salt = "voicehub_secure_session_salt"
    token = hashlib.sha256(f"{password}_{salt}".encode()).hexdigest()
    ACTIVE_SESSIONS.add(token)
    return token

def check_admin_auth(request: Request):
    admin_password = settings.effective_admin_password
    if not admin_password:
        return True

    # 1. Cookie auth_token
    cookie_token = request.cookies.get("auth_token")
    if cookie_token and cookie_token in ACTIVE_SESSIONS:
        return True

    # 2. Direct Header auth (X-Admin-Password / Bearer)
    if request.headers.get("x-admin-password") == admin_password:
        return True
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token == admin_password or token in ACTIVE_SESSIONS:
            return True

    # ログイン関連・静的アセット・公開WebHookは除外
    path = request.url.path
    if path in ("/api/auth/login", "/api/auth/status") or path in ("/api/say", "/api/webhook") or not path.startswith("/api/"):
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin password required"
    )
