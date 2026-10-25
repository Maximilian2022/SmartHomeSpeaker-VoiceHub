import asyncio
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException
from app.services.update_service import update_service
from app.services.settings_service import settings_manager
from app.core.security import is_admin_session, get_effective_admin_password, validate_webhook_token

router = APIRouter(prefix="/api/system", tags=["System"])

@router.get("/version")
async def get_system_version() -> Dict[str, Any]:
    """現在のバージョンと更新ステータス、Watchtower 状態を取得"""
    update_info = await update_service.check_for_updates(force_refresh=False)
    wt_health = await update_service.check_watchtower_health()
    conf = settings_manager.get().get("systemUpdate", {})

    return {
        **update_info,
        "watchtower": wt_health,
        "autoUpdate": bool(conf.get("autoUpdate", False)),
        "autoUpdateTime": str(conf.get("autoUpdateTime") or "04:00")
    }

@router.post("/check-update")
async def force_check_update() -> Dict[str, Any]:
    """GitHub Releases API を強制リフレッシュして最新バージョンを再確認"""
    update_info = await update_service.check_for_updates(force_refresh=True)
    wt_health = await update_service.check_watchtower_health()
    conf = settings_manager.get().get("systemUpdate", {})

    return {
        **update_info,
        "watchtower": wt_health,
        "autoUpdate": bool(conf.get("autoUpdate", False)),
        "autoUpdateTime": str(conf.get("autoUpdateTime") or "04:00")
    }

@router.post("/update")
async def trigger_system_update(request: Request) -> Dict[str, Any]:
    """Watchtower を通じてコンテナの即時アップデートを実行 (管理者認証またはWebhook連携必須)"""
    admin_pw = get_effective_admin_password()
    cookie_token = request.cookies.get("auth_token")
    
    # 管理者パスワード設定時は管理者ログインまたはトークン認証を要求
    if admin_pw:
        import hmac
        from app.core.security import ACTIVE_SESSIONS
        cookie_token = request.cookies.get("auth_token")
        x_admin_pass = request.headers.get("x-admin-password")
        auth_header = request.headers.get("authorization", "")
        bearer_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""

        is_admin = is_admin_session(cookie_token) or \
                   (x_admin_pass and hmac.compare_digest(x_admin_pass, admin_pw)) or \
                   (bearer_token and (bearer_token in ACTIVE_SESSIONS or hmac.compare_digest(bearer_token, admin_pw)))

        if not is_admin:
            # Webhook トークンでの認証も許容
            header_token = request.headers.get("x-webhook-token") or request.headers.get("x-api-key")
            query_token = request.query_params.get("token")
            effective_wh = settings_manager.get_webhook_token()
            token_candidate = header_token or query_token
            if not (effective_wh and token_candidate and hmac.compare_digest(token_candidate, effective_wh)):
                raise HTTPException(status_code=401, detail="管理者ログインまたは有効な認証トークンが必要です")

    result = await update_service.trigger_update()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "アップデートのトリガーに失敗しました"))
    return result
