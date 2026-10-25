from typing import List, Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_service import ai_service, DEFAULT_GEMINI_MODELS, DEFAULT_OPENAI_MODELS
from app.services.settings_service import settings_manager

router = APIRouter()

class SummarizeTestRequest(BaseModel):
    messages: Optional[List[str]] = None
    promptHint: Optional[str] = None

class AiTestRequest(BaseModel):
    provider: Optional[str] = "gemini"
    apiKey: Optional[str] = ""
    model: Optional[str] = ""

GEMINI_MODELS = DEFAULT_GEMINI_MODELS
OPENAI_MODELS = DEFAULT_OPENAI_MODELS

MASK_STR = "********"

def _resolve_key(given_key: Optional[str], saved_key: str) -> str:
    cleaned = (given_key or "").strip()
    if not cleaned or cleaned == MASK_STR:
        return (saved_key or "").strip()
    return cleaned

@router.get("/api/ai/status")
async def get_ai_status():
    return ai_service.get_status()

@router.get("/api/ai/models")
async def get_ai_models(provider: str = "gemini", forceRefresh: bool = False, apiKey: Optional[str] = None):
    ai_conf = settings_manager.get().get("ai", {})
    from app.config import settings
    if provider == "openai":
        saved_key = ai_conf.get("openaiApiKey") or settings.openai_api_key or ""
        openai_key = _resolve_key(apiKey, saved_key)
        models = await ai_service.get_openai_models(openai_key, force_refresh=forceRefresh)
        cur = ai_conf.get("openaiModel", "gpt-4o-mini")
        valid_ids = [m["id"] for m in models]
        if cur not in valid_ids:
            cur = valid_ids[0] if valid_ids else "gpt-4o-mini"
    else:
        saved_key = ai_conf.get("geminiApiKey") or settings.effective_gemini_key or ""
        gemini_key = _resolve_key(apiKey, saved_key)
        models = await ai_service.get_gemini_models(gemini_key, force_refresh=forceRefresh)
        cur = ai_conf.get("geminiModel", "gemini-2.5-flash")
        valid_ids = [m["id"] for m in models]
        if cur not in valid_ids or any(p in cur for p in ["1.5", "1.0", "2.0"]):
            cur = valid_ids[0] if valid_ids else "gemini-2.5-flash"

    return {
        "success": True,
        "provider": provider,
        "models": models,
        "currentModel": cur,
        # 下位互換プロパティ
        "gemini": [m["id"] for m in models] if provider != "openai" else [m["id"] for m in GEMINI_MODELS],
        "openai": [m["id"] for m in models] if provider == "openai" else [m["id"] for m in OPENAI_MODELS]
    }

@router.post("/api/ai/test")
async def test_ai_connection(req: AiTestRequest):
    ai_conf = settings_manager.get().get("ai", {})
    from app.config import settings
    provider = req.provider or "gemini"
    if provider == "openai":
        saved_key = ai_conf.get("openaiApiKey") or settings.openai_api_key or ""
    else:
        saved_key = ai_conf.get("geminiApiKey") or settings.effective_gemini_key or ""
    resolved_key = _resolve_key(req.apiKey, saved_key)
    return await ai_service.test_connection(provider, resolved_key, req.model or "")

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

class CalendarTestRequest(BaseModel):
    promptHint: Optional[str] = None

@router.post("/api/ai/calendar-test")
async def test_calendar(req: CalendarTestRequest = CalendarTestRequest()):
    sample_events = [
        {"start": "09:30", "end": "10:00", "summary": "チーム朝会・定例ミーティング"},
        {"start": "13:00", "end": "14:00", "summary": "設計レビュー"},
        {"start": "16:30", "end": "17:30", "summary": "歯医者（定期検診）"},
    ]
    summary = await ai_service.summarize_calendar_events(sample_events, custom_prompt=req.promptHint)
    if not summary:
        return {"success": False, "error": "予定まとめのAI生成に失敗しました。APIキーやAI設定を確認してください。"}
    return {"success": True, "summary": summary}

