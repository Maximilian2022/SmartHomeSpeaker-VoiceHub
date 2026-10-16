import os
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings
from app.services.settings_service import settings_manager

class AiService:
    def __init__(self):
        pass

    async def summarize_dnd_messages(self, messages: List[str]) -> str:
        if not messages:
            return ""
        if len(messages) == 1:
            return f"保留されていた通知です。{messages[0]}"

        ai_conf = settings_manager.get().get("ai", {})
        provider = ai_conf.get("provider", "gemini")
        gemini_key = ai_conf.get("geminiApiKey") or settings.effective_gemini_key
        openai_key = ai_conf.get("openaiApiKey") or settings.openai_api_key

        prompt = (
            "以下は留守または会議中に保留されていた複数のスマートホーム音声通知です。\n"
            "スピーカーから読み上げるために、要点を1〜2文で自然な日本語で簡潔に要約してください。\n"
            "通知一覧:\n" + "\n".join(f"- {m}" for m in messages)
        )

        if provider == "gemini" and gemini_key:
            return await self._call_gemini(gemini_key, ai_conf.get("geminiModel", "gemini-2.5-flash"), prompt)
        elif provider == "openai" and openai_key:
            return await self._call_openai(openai_key, ai_conf.get("openaiModel", "gpt-4o-mini"), prompt)

        # AI キー未設定時のシンプル連結フォールバック
        return f"保留されていた通知が{len(messages)}件あります。" + "。".join(messages[:3])

    async def _call_gemini(self, api_key: str, model: str, prompt: str) -> str:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0]["content"]["parts"][0]["text"]
                        return text.strip()
        except Exception as e:
            print(f"[AiService] Gemini error: {e}")
        return ""

    async def _call_openai(self, api_key: str, model: str, prompt: str) -> str:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[AiService] OpenAI error: {e}")
        return ""

ai_service = AiService()
