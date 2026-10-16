import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import PUBLIC_DIR, VOICE_DIR, SOUND_DIR, settings
from app.core.security import check_tunnel_access, check_admin_auth
from app.services.disaster_service import disaster_service
from app.services.calendar_service import calendar_service
from app.services.speech_service import speech_service

# Routers
from app.routers import (
    speech,
    devices,
    onvif_dlna,
    settings as settings_router,
    history,
    calendar,
    dnd,
    disaster,
    ai,
    auth,
    homepod_alexa
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時処理
    print("[VoiceHub] Starting Python FastAPI Voice Hub Engine...")
    
    # 防災速報コールバックの設定
    async def on_disaster_alert(text: str, urgent: bool = True):
        await speech_service.speak(text=text, targets="ALL", urgent=urgent)

    disaster_service.set_alert_callback(on_disaster_alert)
    await disaster_service.start()

    # カレンダー同期のバックグラウンドタスク
    async def calendar_loop():
        while True:
            try:
                await calendar_service.sync_all()
            except Exception as e:
                print(f"[VoiceHub] Calendar sync error: {e}")
            await asyncio.sleep(15 * 60) # 15分ごと

    asyncio.create_task(calendar_loop())

    yield

    # 終了時処理
    print("[VoiceHub] Shutting down...")

app = FastAPI(
    title="Smart Home Speaker Voice Hub",
    version="2.0.0",
    lifespan=lifespan
)

# CORS (宅内WebGUIおよびローカル連携用)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# セキュリティミドルウェア (境界防御 & 管理者認証)
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Tunnel 境界チェック
    check_tunnel_access(request)
    # 管理者認証チェック
    check_admin_auth(request)
    response = await call_next(request)
    return response

# ルーター登録
app.include_router(speech.router)
app.include_router(devices.router)
app.include_router(onvif_dlna.router)
app.include_router(settings_router.router)
app.include_router(history.router)
app.include_router(calendar.router)
app.include_router(dnd.router)
app.include_router(disaster.router)
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(homepod_alexa.router)

# 静的ファイルの配信
app.mount("/voice", StaticFiles(directory=str(VOICE_DIR)), name="voice")
app.mount("/sound", StaticFiles(directory=str(SOUND_DIR)), name="sound")

@app.get("/")
async def serve_index():
    return FileResponse(str(PUBLIC_DIR / "index.html"))

# その他の静的ファイル (app.js, style.css, favicon 等)
app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="public")
