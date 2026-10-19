import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import PUBLIC_DIR, VOICE_DIR, SOUND_DIR, settings
from app.core.security import check_tunnel_access, check_admin_auth
from app.services.disaster_service import disaster_service
from app.services.calendar_service import calendar_service
from app.services.speech_service import speech_service
from app.services.scheduler_service import scheduler_service
from app.services.scheduled_speech_service import scheduled_speech_service

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
    homepod_alexa,
    status,
    schedules,
    mqtt,
    mcp,
    logs
)
from app.core.logger import init_system_logging, get_logger
from app.services.mqtt_service import mqtt_service

# システムロギングの初期化 (Uvicorn / stdout キャプチャ統合)
init_system_logging()
sys_log = get_logger("System")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時処理 (明示的なシステム起動/再起動バナーログ)
    sys_log.info("================================================================================")
    sys_log.info("🚀 [VoiceHub] システム起動 / 再起動 (VoiceHub Engine Started)")
    sys_log.info(f"   PID: {os.getpid()} | 環境: Python FastAPI | ポート: 8080")
    sys_log.info("================================================================================")
    
    # スケジューラー定期実行タスク開始
    await scheduler_service.start()
    # 予約発声ワーカータスク開始 (日時指定発声)
    await scheduled_speech_service.start()

    # 防災速報コールバックの設定
    async def on_disaster_speech(text: str, targets=None, urgent: bool = True, volume_level: int = None):
        await speech_service.speak(text=text, targets=targets or "ALL", urgent=urgent, volume_level=volume_level)

    disaster_service.set_speech_executor(on_disaster_speech)
    await disaster_service.start()

    # DND サービスのバックグラウンドタスク開始
    from app.services.dnd_service import dnd_service
    dnd_service.set_speaker_executor(speech_service.speak)
    dnd_service.start_background_tasks()

    # カレンダーサービスの初期化とバックグラウンドスケジューラー開始
    calendar_service.set_speech_executor(speech_service.speak)
    calendar_service.start_background_scheduler()

    # カレンダー定期同期タスク (15分ごと)
    async def calendar_loop():
        while True:
            try:
                await calendar_service.sync_all()
            except Exception as e:
                log.warning(f"Calendar sync error: {e}")
            await asyncio.sleep(15 * 60)

    asyncio.create_task(calendar_loop())

    # MQTT サービスのバックグラウンドワーカー開始
    mqtt_service.start()

    # 外部 TTS エンジン (VOICEVOX等) の事前初期化・ウォームアップ
    from app.services.tts_service import tts_service
    asyncio.create_task(tts_service.warmup_enabled_speakers())

    yield

    # 終了時処理 (明示的なシステム終了/シャットダウンバナーログ)
    sys_log.info("🛑 [VoiceHub] システム終了 / シャットダウン処理開始 (Shutting down...)")
    await mqtt_service.stop()
    sys_log.info("✅ [VoiceHub] シャットダウン完了")


app = FastAPI(
    title="Smart Home Speaker Voice Hub",
    version="2.0.0",
    lifespan=lifespan
)

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.logger import get_logger
import traceback

log = get_logger("API")

# CORS (宅内WebGUIおよびローカル連携用: RFC 1918 プライベートIP、localhost、設定されたトンネルドメインを許可)
cors_regex = r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$"
if settings.tunnel_domain:
    import re
    escaped_domain = re.escape(settings.tunnel_domain)
    cors_regex = rf"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|{escaped_domain})(:\d+)?$"

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# アクセス＆エラー監視ミドルウェア
@app.middleware("http")
async def logging_and_security_middleware(request: Request, call_next):
    path = request.url.path

    # Tunnel 境界チェック ＆ 管理者認証チェック (ミドルウェア内の HTTPException 500 化を防止)
    try:
        check_tunnel_access(request)
        check_admin_auth(request)
    except HTTPException as exc:
        log.warning(f"[{request.method}] {path} -> HTTP {exc.status_code} ({exc.detail}) (Client: {request.client.host if request.client else 'unknown'})")
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "detail": exc.detail}
        )

    # 頻繁なステータスポーリング (/api/dnd/status, /api/logs 等) は DEBUG レベル相当にする (ログ肥大化防止)
    is_frequent_poll = path in ("/api/dnd/status", "/api/status", "/api/logs", "/favicon.ico")

    try:
        response = await call_next(request)
        if response.status_code >= 400:
            log.warning(f"[{request.method}] {path} -> HTTP {response.status_code} (Client: {request.client.host if request.client else 'unknown'})")
        elif not is_frequent_poll:
            log.info(f"[{request.method}] {path} -> HTTP {response.status_code}")
        return response
    except HTTPException as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "detail": exc.detail}
        )
    except Exception as exc:
        tb = traceback.format_exc()
        log.error(f"Unhandled Exception on [{request.method}] {path}:\n{tb}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An internal server error occurred.",
                "detail": "An internal server error occurred.",
                "path": path
            }
        )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    log.warning(f"Validation Error on [{request.method}] {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "リクエストパラメータの形式が正しくありません",
            "detail": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    log.error(f"Global Exception on [{request.method}] {request.url.path}: {exc}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "detail": str(exc)
        }
    )

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
app.include_router(status.router)
app.include_router(schedules.router)
app.include_router(mqtt.router)
app.include_router(mcp.router)
app.include_router(logs.router)



# 音声キャッシュファイルの配信 (Google Cast 等の 304 Not Modified 再生停止バグを完全に防止)
@app.api_route("/voice/{filename}", methods=["GET", "HEAD"])
async def serve_voice_file(filename: str):
    safe_filename = Path(filename).name
    base_resolved = VOICE_DIR.resolve()
    filepath = (VOICE_DIR / safe_filename).resolve()
    if not filepath.is_relative_to(base_resolved) or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Voice file not found")
    return FileResponse(
        path=str(filepath),
        media_type="audio/mp3",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Accept-Ranges": "bytes"
        }
    )

app.mount("/sound", StaticFiles(directory=str(SOUND_DIR)), name="sound")

@app.get("/")
async def serve_index():
    return FileResponse(str(PUBLIC_DIR / "index.html"))

# その他の静的ファイル (app.js, style.css, favicon 等)
app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="public")
