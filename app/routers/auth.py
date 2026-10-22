import hmac
from typing import Optional
from fastapi import APIRouter, Response, Request, HTTPException, status
from pydantic import BaseModel
from app.config import settings
from app.services.settings_service import settings_manager
from app.core.security import (
    generate_session_token,
    ACTIVE_SESSIONS,
    get_effective_admin_password,
    is_https_request,
    login_rate_limiter,
    extract_client_ip as get_client_ip,
)

router = APIRouter()

class LoginRequest(BaseModel):
    password: str

class PasswordChangeRequest(BaseModel):
    currentPassword: Optional[str] = ""
    newPassword: str

@router.get("/api/auth/status")
async def auth_status(request: Request):
    admin_password = get_effective_admin_password()
    client_ip = get_client_ip(request)
    is_locked, remaining = login_rate_limiter.is_locked(client_ip)

    if not admin_password:
        return {
            "authRequired": False,
            "authenticated": True,
            "isLocked": is_locked,
            "remainingSeconds": remaining
        }

    cookie_token = request.cookies.get("auth_token")
    is_authed = bool(cookie_token and cookie_token in ACTIVE_SESSIONS)
    return {
        "authRequired": True,
        "authenticated": is_authed,
        "isLocked": is_locked,
        "remainingSeconds": remaining
    }

@router.post("/api/auth/login")
async def auth_login(req: LoginRequest, request: Request, response: Response):
    client_ip = get_client_ip(request)
    is_locked, remaining = login_rate_limiter.is_locked(client_ip)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"ログイン試行回数が上限を超えました。あと {remaining} 秒お待ちください。"
        )

    admin_password = get_effective_admin_password()
    is_valid = False
    if not admin_password:
        is_valid = True
    elif hmac.compare_digest(req.password, admin_password):
        is_valid = True

    if is_valid:
        login_rate_limiter.record_success(client_ip)
        token = generate_session_token(req.password or "default")
        is_secure = is_https_request(request)
        response.set_cookie(
            key="auth_token",
            value=token,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax",
            secure=is_secure
        )
        return {"success": True}

    # 失敗時はレートリミッターに記録
    now_locked, lock_sec = login_rate_limiter.record_failure(client_ip)
    if now_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"連続してログインに失敗したため、アカウントを一時ロックしました。あと {lock_sec} 秒お待ちください。"
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="パスワードが正しくありません")

@router.post("/api/auth/logout")
async def auth_logout(request: Request, response: Response):
    cookie_token = request.cookies.get("auth_token")
    if cookie_token and cookie_token in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS.remove(cookie_token)
    response.delete_cookie("auth_token")
    return {"success": True}

@router.post("/api/auth/password")
async def set_password(req: PasswordChangeRequest, request: Request, response: Response):
    """
    管理者パスワードの設定・変更・削除API
    - すでにパスワードがある場合: 認証済み管理者セッション または currentPassword の一致が必要
    - パスワード未設定の場合: 初回設定としてそのまま受付
    """
    current_admin_pass = get_effective_admin_password()
    cookie_token = request.cookies.get("auth_token")
    is_authenticated = bool(cookie_token and cookie_token in ACTIVE_SESSIONS)

    if current_admin_pass:
        # パスワードが既に設定されている場合は、不正変更防止のため現在のパスワードの再確認を必須とする
        cur_req = req.currentPassword or ""
        if not hmac.compare_digest(cur_req, current_admin_pass):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="現在のパスワードが正しくありません"
            )


    new_pass = req.newPassword.strip()
    settings_manager.set_admin_password(new_pass)

    # パスワード変更または解除時は、既存の全セッションを一括失効 (セキュリティ堅牢化)
    ACTIVE_SESSIONS.clear()

    if new_pass:
        # 新しいパスワードで新セッショントークンを発行
        token = generate_session_token(new_pass)
        is_secure = is_https_request(request)
        response.set_cookie(
            key="auth_token",
            value=token,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax",
            secure=is_secure
        )
    else:
        # パスワード解除時はCookie削除
        response.delete_cookie("auth_token")

    return {
        "success": True,
        "authRequired": bool(new_pass),
        "hasAdminPassword": bool(new_pass)
    }

