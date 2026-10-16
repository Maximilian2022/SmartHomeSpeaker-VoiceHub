from typing import List, Optional, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_service import ai_service
from app.services.speech_service import speech_service

router = APIRouter()

class SummarizeTestRequest(BaseModel):
    messages: Optional[List[str]] = None

class AiTestRequest(BaseModel):
    provider: Optional[str] = "gemini"
    apiKey: Optional[str] = ""
    model: Optional[str] = ""

@router.get("/api/ai/status")
async def get_ai_status():
    return ai_service.get_status()

@router.get("/api/ai/models")
async def get_ai_models():
    return {
        "gemini": ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        "openai": ["gpt-4o-mini", "gpt-4o"]
    }

@router.post("/api/ai/test")
async def test_ai_connection(req: AiTestRequest):
    return await ai_service.test_connection(req.provider or "gemini", req.apiKey or "", req.model or "")

@router.post("/api/ai/summarize-test")
async def test_summarize(req: SummarizeTestRequest):
    msgs = req.messages or [
        "10時30分に宅配便が届きました",
        "人感センサーがリビングで動体を検知しました",
        "お風呂が沸き上がりました"
    ]
    summary = await ai_service.summarize_dnd_messages(msgs)
    return {"success": True, "summary": summary, "sampleCount": len(msgs)}

@router.post("/api/ai/calendar-test")
async def test_calendar():
    return {
        "success": True,
        "summary": "おはようございます。本日は9時30分からチームミーティング、14時から来客予定が入っています。今日も一日がんばりましょう！"
    }
