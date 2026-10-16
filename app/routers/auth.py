from fastapi import APIRouter, Response, Request, HTTPException
from pydantic import BaseModel
from app.config import settings
from app.core.security import generate_session_token, ACTIVE_SESSIONS

router = APIRouter()

class LoginRequest(BaseModel):
    password: str

@router.get("/api/auth/status")
async def auth_status(request: Request):
    admin_password = settings.effective_admin_password
    if not admin_password:
        return {"authRequired": False, "authenticated": True}

    cookie_token = request.cookies.get("auth_token")
    is_authed = bool(cookie_token and cookie_token in ACTIVE_SESSIONS)
    return {"authRequired": True, "authenticated": is_authed}

@router.post("/api/auth/login")
async def auth_login(req: LoginRequest, response: Response):
    admin_password = settings.effective_admin_password
    if not admin_password or req.password == admin_password:
        token = generate_session_token(req.password or "default")
        response.set_cookie(
            key="auth_token",
            value=token,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax"
        )
        return {"success": True}
    raise HTTPException(status_code=401, detail="Invalid password")

@router.post("/api/auth/logout")
async def auth_logout(request: Request, response: Response):
    cookie_token = request.cookies.get("auth_token")
    if cookie_token in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS.remove(cookie_token)
    response.delete_cookie("auth_token")
    return {"success": True}
