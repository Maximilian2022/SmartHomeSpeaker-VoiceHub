from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.ai_service import ai_service
from app.services.speech_service import speech_service

router = APIRouter()

class SummarizeTestRequest(BaseModel):
    messages: Optional[List[str]] = None

@router.get("/api/ai/models")
async def get_ai_models():
    return {
        "gemini": ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        "openai": ["gpt-4o-mini", "gpt-4o"]
    }

@router.post("/api/ai/summarize-test")
async def test_summarize(req: SummarizeTestRequest):
    msgs = req.messages or [
        "10時30分に宅配便が届きました",
        "人感センサーがリビングで動体を検知しました",
        "お風呂が沸き上がりました"
    ]
    summary = await ai_service.summarize_dnd_messages(msgs)
    return {"summary": summary}
