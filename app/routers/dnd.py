import asyncio
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Response, Query
from pydantic import BaseModel
from app.config import settings
from app.services.dnd_service import dnd_service
from app.services.calendar_service import calendar_service
from app.services.settings_service import settings_manager
from app.services.speech_service import speech_service
from app.services.ai_service import ai_service
from app.services.mqtt_service import mqtt_service
from app.core.logger import get_logger

log = get_logger("DndRouter")
router = APIRouter()

DND_SCRIPT_ACTIONS = {
    "toggle": {
        "title": "Toggle Mute (ON/OFF)",
        "endpoint": "/api/dnd/toggle",
        "method": "POST",
        "body_json": None,
    },
    "30m": {
        "title": "30min Meeting Mute",
        "endpoint": "/api/dnd/quick",
        "method": "POST",
        "body_json": '{"minutes": 30, "reason": "Quick DND (30m)"}',
    },
    "60m": {
        "title": "60min Meeting Mute",
        "endpoint": "/api/dnd/quick",
        "method": "POST",
        "body_json": '{"minutes": 60, "reason": "Quick DND (60m)"}',
    },
    "unmute": {
        "title": "Unmute / Release",
        "endpoint": "/api/dnd/unmute",
        "method": "POST",
        "body_json": None,
    },
}

def build_dnd_script(action: str, fmt: str, host: str, password: str = "") -> tuple[str, str, str]:
    """
    Returns (filename, script_content, mime_type)
    """
    cfg = DND_SCRIPT_ACTIONS.get(action, DND_SCRIPT_ACTIONS["toggle"])
    clean_host = (host or "http://localhost:8080").strip().rstrip("/")
    if not (clean_host.startswith("http://") or clean_host.startswith("https://")):
        clean_host = "http://" + clean_host

    clean_fmt = fmt.lower().strip()
    if clean_fmt not in ("vbs", "bat", "sh"):
        clean_fmt = "vbs"

    title = cfg["title"]
    endpoint = cfg["endpoint"]
    body_json = cfg["body_json"]

    if clean_fmt == "vbs":
        filename = f"voicehub_dnd_{action}.vbs"
        mime_type = "text/plain; charset=utf-8"
        vbs_post_data = body_json.replace('"', '""') if body_json else ""
        content = (
            f"' VoiceHub DND - {title} (Silent Execution)\r\n"
            f"' Suitable for Logitech G HUB, Elgato Stream Deck, Windows Shortcuts\r\n"
            f"Option Explicit\r\n"
            f"Dim url, http, adminPassword, postData\r\n\r\n"
            f'url = "{clean_host}{endpoint}"\r\n'
            f'adminPassword = "{password}"\r\n'
            f'postData = "{vbs_post_data}"\r\n\r\n'
            f"On Error Resume Next\r\n"
            f'Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")\r\n'
            f"If http Is Nothing Then\r\n"
            f'    Set http = CreateObject("MSXML2.ServerXMLHTTP")\r\n'
            f"End If\r\n"
            f"If http Is Nothing Then\r\n"
            f'    Set http = CreateObject("MSXML2.XMLHTTP")\r\n'
            f"End If\r\n\r\n"
            f'http.Open "POST", url, False\r\n'
            f'http.setRequestHeader "Content-Type", "application/json"\r\n'
            f'If adminPassword <> "" Then\r\n'
            f'    http.setRequestHeader "x-admin-password", adminPassword\r\n'
            f"End If\r\n\r\n"
            f"http.Send postData\r\n"
            f"Set http = Nothing\r\n"
        )
    elif clean_fmt == "bat":
        filename = f"voicehub_dnd_{action}.bat"
        mime_type = "application/x-bat; charset=utf-8"
        if body_json:
            escaped_body = body_json.replace('"', '\\"')
            data_arg = f'-H "Content-Type: application/json" -d "{escaped_body}"'
        else:
            data_arg = ""

        cmd_no_pwd = f'curl -s -X POST "%VOICEHUB_HOST%{endpoint}" {data_arg}'.strip() + " >nul"
        cmd_with_pwd = f'curl -s -X POST "%VOICEHUB_HOST%{endpoint}" -H "x-admin-password: %ADMIN_PASSWORD%" {data_arg}'.strip() + " >nul"

        content = (
            f"@echo off\r\n"
            f"chcp 65001 >nul\r\n"
            f":: VoiceHub DND - {title}\r\n"
            f":: Suitable for Logitech G HUB, Elgato Stream Deck, Command Line\r\n\r\n"
            f'set "VOICEHUB_HOST={clean_host}"\r\n'
            f'set "ADMIN_PASSWORD={password}"\r\n\r\n'
            f'if "%ADMIN_PASSWORD%"=="" (\r\n'
            f"    {cmd_no_pwd}\r\n"
            f") else (\r\n"
            f"    {cmd_with_pwd}\r\n"
            f")\r\n"
        )
    else:  # sh
        filename = f"voicehub_dnd_{action}.sh"
        mime_type = "text/x-shellscript; charset=utf-8"
        data_arg = f"-H 'Content-Type: application/json' -d '{body_json}'" if body_json else ""
        cmd_no_pwd = f'curl -s -X POST "$VOICEHUB_HOST{endpoint}" {data_arg}'.strip() + " >/dev/null"
        cmd_with_pwd = f'curl -s -X POST "$VOICEHUB_HOST{endpoint}" -H "x-admin-password: $ADMIN_PASSWORD" {data_arg}'.strip() + " >/dev/null"

        content = (
            f"#!/usr/bin/env bash\n"
            f"# VoiceHub DND - {title}\n"
            f"# Suitable for Stream Deck (macOS/Linux), Shortcuts, Terminal\n\n"
            f'VOICEHUB_HOST="{clean_host}"\n'
            f'ADMIN_PASSWORD="{password}"\n\n'
            f'if [ -z "$ADMIN_PASSWORD" ]; then\n'
            f"    {cmd_no_pwd}\n"
            f"else\n"
            f"    {cmd_with_pwd}\n"
            f"fi\n"
        )

    return filename, content, mime_type

class MuteRequest(BaseModel):
    durationMinutes: Optional[int] = None
    until: Optional[float] = None
    reason: Optional[str] = "手動ミュート"

@router.get("/api/dnd/status")
async def get_dnd_status():
    status = dnd_service.get_global_status()
    return status

@router.post("/api/dnd/mute")
async def mute_dnd(req: MuteRequest = MuteRequest()):
    now_ts = time.time()
    if req.until:
        until_ts = req.until
    elif req.durationMinutes:
        until_ts = now_ts + (req.durationMinutes * 60)
    else:
        until_ts = now_ts + (365 * 24 * 3600)  # 時間省略時は無期限手動ミュート

    dnd_conf = settings_manager.get().get("dnd", {})
    settings_manager.update({
        "dnd": {
            **dnd_conf,
            "manualUntil": until_ts,
            "manualReason": req.reason or "手動ミュート"
        }
    })
    log.info(f"DND muted until {until_ts} (reason: {req.reason})")
    asyncio.create_task(mqtt_service.publish_dnd_state())
    return {"success": True, "manualUntil": until_ts}

@router.post("/api/dnd/unmute")
async def unmute_dnd():
    dnd_conf = settings_manager.get().get("dnd", {})
    settings_manager.update({
        "dnd": {
            **dnd_conf,
            "manualUntil": None,
            "manualReason": ""
        }
    })
    log.info("DND unmuted.")
    # キューがあれば消化
    asyncio.create_task(dnd_service.check_and_flush_queue())
    asyncio.create_task(mqtt_service.publish_dnd_state())
    return {"success": True}

@router.post("/api/dnd/toggle")
async def toggle_dnd():
    status = dnd_service.get_global_status()
    if status.get("isActive", False):
        return await unmute_dnd()
    else:
        return await mute_dnd()


@router.post("/api/dnd/quick")
async def quick_dnd(req: Dict[str, Any]):
    raw_minutes = req.get("minutes", 60)
    reason = req.get("reason", "手動サイレント (即時)")
    now_ts = time.time()

    if raw_minutes in ("indefinite", -1, "-1"):
        until_ts = now_ts + (365 * 24 * 3600) # 実質無期限
    else:
        try:
            m = int(raw_minutes)
        except (ValueError, TypeError):
            m = 60
        if m == 0:
            # 0分指定は解除
            return await unmute_dnd()
        until_ts = now_ts + (m * 60)

    dnd_conf = settings_manager.get().get("dnd", {})
    settings_manager.update({
        "dnd": {
            **dnd_conf,
            "manualUntil": until_ts,
            "manualReason": reason
        }
    })
    log.info(f"Quick DND enabled: minutes={raw_minutes}, until={until_ts}, reason={reason}")
    asyncio.create_task(mqtt_service.publish_dnd_state())
    return {"success": True, "manualUntil": until_ts, "reason": reason}

@router.get("/api/dnd/history")
async def get_dnd_history():
    return dnd_service.get_history()

@router.delete("/api/dnd/history")
async def clear_dnd_history():
    dnd_service.clear_history()
    log.info("DND history cleared.")
    return {"success": True}

@router.get("/api/dnd/queue")
async def get_dnd_queue():
    return dnd_service.get_queue()

@router.get("/api/queue")
async def get_general_queue():
    """旧Node版互換: 永続化キュー状態確認 API"""
    q = dnd_service.get_queue()
    return {
        "dndQueue": q,
        "webhookQueue": []
    }

@router.post("/api/dnd/queue/release")
async def release_dnd_queue():
    released = await dnd_service.check_and_flush_queue()
    return {"success": True, "released": released or 0}

@router.get("/api/dnd/script/preview")
async def preview_dnd_script(
    request: Request,
    action: str = Query("toggle", description="Script action: toggle, 30m, 60m, unmute"),
    format: str = Query("vbs", description="Script format: vbs, bat, sh"),
    host: Optional[str] = Query(None, description="Custom VoiceHub host URL"),
    password: Optional[str] = Query(None, description="Custom admin password")
):
    req_host = host or f"{request.url.scheme}://{request.url.netloc}"
    pwd = password if password is not None else settings.effective_admin_password
    filename, content, mime_type = build_dnd_script(action, format, req_host, pwd)
    return {
        "filename": filename,
        "content": content,
        "format": format,
        "action": action,
        "mimeType": mime_type
    }

@router.get("/api/dnd/script/download")
async def download_dnd_script(
    request: Request,
    action: str = Query("toggle", description="Script action: toggle, 30m, 60m, unmute"),
    format: str = Query("vbs", description="Script format: vbs, bat, sh"),
    host: Optional[str] = Query(None, description="Custom VoiceHub host URL"),
    password: Optional[str] = Query(None, description="Custom admin password")
):
    req_host = host or f"{request.url.scheme}://{request.url.netloc}"
    pwd = password if password is not None else settings.effective_admin_password
    filename, content, mime_type = build_dnd_script(action, format, req_host, pwd)
    return Response(
        content=content.encode("utf-8"),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


