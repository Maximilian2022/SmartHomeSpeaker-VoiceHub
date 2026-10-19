from typing import List, Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_service import ai_service
from app.services.settings_service import settings_manager

router = APIRouter()

class SummarizeTestRequest(BaseModel):
    messages: Optional[List[str]] = None
    promptHint: Optional[str] = None

class AiTestRequest(BaseModel):
    provider: Optional[str] = "gemini"
    apiKey: Optional[str] = ""
    model: Optional[str] = ""

GEMINI_MODELS = [
    {"id": "gemini-2.5-flash", "name": "gemini-2.5-flash (最新主力・高速・推奨)"},
    {"id": "gemini-2.5-pro", "name": "gemini-2.5-pro (最高峰推論・高精度)"},
    {"id": "gemini-2.5-flash-lite", "name": "gemini-2.5-flash-lite (超軽量・即答)"}
]


OPENAI_MODELS = [
    {"id": "gpt-4o-mini", "name": "gpt-4o-mini (高速・経済的・推奨)"},
    {"id": "gpt-4o", "name": "gpt-4o (最高性能フラグシップ)"},
    {"id": "o3-mini", "name": "o3-mini (高速推論特化)"},
    {"id": "o1", "name": "o1 (高度推論モデル)"}
]

@router.get("/api/ai/status")
async def get_ai_status():
    return ai_service.get_status()

@router.get("/api/ai/models")
async def get_ai_models(provider: str = "gemini"):
    ai_conf = settings_manager.get().get("ai", {})
    if provider == "openai":
        models = OPENAI_MODELS
        cur = ai_conf.get("openaiModel", "gpt-4o-mini")
    else:
        models = GEMINI_MODELS
        cur = ai_conf.get("geminiModel", "gemini-2.5-flash")
        if any(p in cur for p in ["1.5", "1.0", "2.0"]):
            cur = "gemini-2.5-flash"

    return {
        "success": True,
        "provider": provider,
        "models": models,
        "currentModel": cur,
        # 下位互換プロパティ
        "gemini": [m["id"] for m in GEMINI_MODELS],
        "openai": [m["id"] for m in OPENAI_MODELS]
    }

@router.post("/api/ai/test")
async def test_ai_connection(req: AiTestRequest):
    return await ai_service.test_connection(req.provider or "gemini", req.apiKey or "", req.model or "")

@router.post("/api/ai/summarize-test")
async def test_summarize(req: SummarizeTestRequest = SummarizeTestRequest()):
    msgs = req.messages or [
        "10時30分に宅配便が届きました",
        "人感センサーがリビングで動体を検知しました",
        "お風呂が沸き上がりました"
    ]
    summary = await ai_service.summarize_dnd_messages(msgs, custom_prompt=req.promptHint)
    if not summary:
        summary = f"留守中に {len(msgs)} 件の通知を受信しました。" + "、".join(msgs)
    return {"success": True, "summary": summary, "sampleCount": len(msgs)}

@router.post("/api/ai/calendar-test")
async def test_calendar():
    return {
        "success": True,
        "summary": "おはようございます。本日は9時30分からチームミーティング、14時から来客予定が入っています。今日も一日がんばりましょう！"
    }
