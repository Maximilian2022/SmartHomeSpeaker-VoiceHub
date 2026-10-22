import hashlib
import hmac
import ipaddress
import secrets
from typing import Optional
import time
from typing import Optional, Dict, List, Tuple
from fastapi import Request, HTTPException, status
from app.config import settings

ACTIVE_SESSIONS = set()

class LoginRateLimiter:
    """ブルートフォース攻撃・辞書攻撃を防ぐIPベースのレートリミッター"""
    def __init__(self, max_attempts: int = 5, window_seconds: int = 60, lockout_seconds: int = 180):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self.attempts: Dict[str, List[float]] = {}
        self.lockouts: Dict[str, float] = {}

    def is_locked(self, ip: str) -> Tuple[bool, int]:
        now = time.time()
        until = self.lockouts.get(ip, 0.0)
        if now < until:
            remaining = int(until - now) + 1
            return True, remaining
        if ip in self.lockouts:
            del self.lockouts[ip]
        return False, 0

    def record_failure(self, ip: str) -> Tuple[bool, int]:
        now = time.time()
        is_locked, remaining = self.is_locked(ip)
        if is_locked:
            return True, remaining

        records = [t for t in self.attempts.get(ip, []) if now - t < self.window_seconds]
        records.append(now)
        self.attempts[ip] = records

        if len(records) >= self.max_attempts:
            self.lockouts[ip] = now + self.lockout_seconds
            self.attempts.pop(ip, None)
            return True, self.lockout_seconds
        return False, 0

    def record_success(self, ip: str):
        self.attempts.pop(ip, None)
        self.lockouts.pop(ip, None)

login_rate_limiter = LoginRateLimiter()

def get_effective_admin_password() -> str:
    """settings.json の設定を最優先し、未設定なら .my.env の値を返す"""
    from app.services.settings_service import settings_manager
    return settings_manager.get_admin_password()

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

def is_https_request(request: Request) -> bool:
    """リクエストが HTTPS または Cloudflare Tunnel (SSL終端) 経由であるかを判定"""
    if request.url.scheme == "https":
        return True
    if request.headers.get("x-forwarded-proto", "").lower() == "https":
        return True
    if is_tunnel_request(request):
        return True
    return False

def check_tunnel_access(request: Request):
    """
    Cloudflare Tunnel からのアクセス時：
    - 管理者パスワードが設定されている場合: Web GUI および全 API の通過を許可 (未認証時は check_admin_auth で 401 遮断)
    - 管理者パスワードが未設定の場合: 安全のため Webhook (/api/say, /api/webhook) および MCP (/mcp*) 以外は 403 で遮断
    """
    if is_tunnel_request(request):
        admin_pass = get_effective_admin_password()
        if admin_pass:
            # パスワード保護されているため Tunnel 経由でも GUI/API への進入を許可
            return

        path = request.url.path
        if not (path == "/api/say" or path == "/api/webhook" or path.startswith("/mcp")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Web GUI and management APIs are restricted to internal LAN when ADMIN_PASSWORD is not configured."
            )

def validate_webhook_token(request: Request, body_token: Optional[str] = None):
    from app.services.settings_service import settings_manager
    expected_token = settings_manager.get().get("webhookToken") or settings.webhook_token
    if not expected_token:
        return True

    # 1. 認証済み管理者セッション Cookie (auth_token) を持つ場合は Tunnel / LAN を問わず自動免除
    cookie_token = request.cookies.get("auth_token")
    if cookie_token and cookie_token in ACTIVE_SESSIONS:
        return True

    # 2. 宅内ブラウザGUIからの同一オリジンアクセスは自動免除 (※Cloudflare Tunnel 経由時は絶対に免除しない)
    if not is_tunnel_request(request):
        client_host = request.client.host if request.client else ""
        sec_fetch_site = request.headers.get("sec-fetch-site", "")
        referer = request.headers.get("referer", "")
        if is_private_ip(client_host) and (sec_fetch_site in ("same-origin", "same-site") or (referer and is_private_ip(referer.split("://")[-1].split(":")[0].split("/")[0]))):
            return True

    # 3. Authorization: Bearer <token>
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if hmac.compare_digest(token, expected_token):
            return True

    # 4. X-API-KEY / X-Webhook-Token
    api_key = request.headers.get("x-api-key")
    if api_key and hmac.compare_digest(api_key, expected_token):
        return True
    wh_token = request.headers.get("x-webhook-token")
    if wh_token and hmac.compare_digest(wh_token, expected_token):
        return True

    # 5. Query parameter ?token=
    q_token = request.query_params.get("token")
    if q_token and hmac.compare_digest(q_token, expected_token):
        return True

    # 6. JSON Body token
    if body_token and hmac.compare_digest(body_token, expected_token):
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Invalid or missing Webhook token."
    )

def generate_session_token(password: str = "") -> str:
    token = secrets.token_hex(32)
    ACTIVE_SESSIONS.add(token)
    return token

def check_admin_auth(request: Request):
    admin_password = get_effective_admin_password()
    if not admin_password:
        return True

    # 1. Cookie auth_token
    cookie_token = request.cookies.get("auth_token")
    if cookie_token and cookie_token in ACTIVE_SESSIONS:
        return True

    # 2. Direct Header auth (X-Admin-Password / Bearer) (タイミング攻撃対策のため hmac.compare_digest を使用)
    x_admin_pass = request.headers.get("x-admin-password")
    if x_admin_pass and hmac.compare_digest(x_admin_pass, admin_password):
        return True
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token in ACTIVE_SESSIONS or hmac.compare_digest(token, admin_password):
            return True

    # ログイン関連・静的アセット・公開WebHookは除外
    path = request.url.path
    if path in ("/api/auth/login", "/api/auth/status") or path in ("/api/say", "/api/webhook") or not path.startswith("/api/"):
        return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Admin password required"
    )


def derive_tapo_auth_token(token_or_secret: str) -> str:
    """
    TP-Link Tapo 独自通話プロトコル (ポート8800 / tapo://) の規格に準拠した認証トークンを導出。
    Tapo ファームウェア仕様: SHA256(secret).hexdigest().upper()
    ※ アプリケーション内部のパスワード保管用ハッシュではなく、外部ハードウェア機器との通信プロトコル規格トークンとして使用。
    """
    raw_val = str(token_or_secret or "").strip()
    if not raw_val:
        return ""
    if len(raw_val) == 64 and all(c in "0123456789abcdefABCDEF" for c in raw_val):
        return raw_val.upper()
    return hashlib.sha256(raw_val.encode("utf-8")).hexdigest().upper()

