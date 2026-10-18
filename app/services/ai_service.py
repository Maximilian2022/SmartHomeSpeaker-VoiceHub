import os
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings
from app.services.settings_service import settings_manager
from app.core.logger import get_logger

log = get_logger("AI")

class AiService:
    def __init__(self):
        pass

    def mask_key(self, key: str) -> str:
        if not key:
            return ""
        trimmed = key.strip()
        if len(trimmed) <= 8:
            return "****"
        return f"{trimmed[:4]}...{trimmed[-4:]}"

    def get_status(self) -> Dict[str, Any]:
        ai_conf = settings_manager.get().get("ai", {})
        dnd_conf = settings_manager.get().get("dnd", {})
        gemini_key = ai_conf.get("geminiApiKey") or settings.effective_gemini_key
        openai_key = ai_conf.get("openaiApiKey") or settings.openai_api_key

        model = ai_conf.get("geminiModel", "gemini-2.5-flash")
        if any(p in model for p in ["3.8", "3.5", "argon"]):
            model = "gemini-2.5-flash"

        return {
            "enabled": ai_conf.get("enabled", True),
            "provider": ai_conf.get("provider", "gemini"),
            "gemini": {
                "hasKey": bool(gemini_key),
                "keyMasked": self.mask_key(gemini_key),
                "source": "settings" if ai_conf.get("geminiApiKey") else ("env" if gemini_key else "none"),
                "model": model
            },
            "openai": {
                "hasKey": bool(openai_key),
                "keyMasked": self.mask_key(openai_key),
                "source": "settings" if ai_conf.get("openaiApiKey") else ("env" if openai_key else "none"),
                "model": ai_conf.get("openaiModel", "gpt-4o-mini")
            },
            "dndSummary": {
                "enabled": dnd_conf.get("aiSummaryEnabled", True),
                "threshold": int(dnd_conf.get("aiSummaryThreshold", 2)),
                "customPrompt": dnd_conf.get("aiSummaryCustomPrompt", "")
            },
            "calendarSummary": {
                "enabled": ai_conf.get("summarizeDailyCalendar", True)
            }
        }

    async def test_connection(self, provider: str, api_key: str, model: str) -> Dict[str, Any]:
        prompt = "接続テストです。日本語で一言返答してください。"
        if provider == "gemini":
            target_model = model or "gemini-2.5-flash"
            res, err = await self._call_gemini_with_err(api_key, target_model, prompt)
            return {"success": bool(res), "reply": res, "error": err if not res else None}
        elif provider == "openai":
            target_model = model or "gpt-4o-mini"
            res, err = await self._call_openai_with_err(api_key, target_model, prompt)
            return {"success": bool(res), "reply": res, "error": err if not res else None}
        return {"success": False, "error": f"Unknown provider {provider}"}

    async def summarize_dnd_messages(self, messages: List[str], custom_prompt: Optional[str] = None) -> str:
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
        )
        if custom_prompt:
            prompt += f"追加指示: {custom_prompt}\n"
        prompt += "通知一覧:\n" + "\n".join(f"- {m}" for m in messages)

        summary = ""
        if provider == "gemini" and gemini_key:
            model = ai_conf.get("geminiModel", "gemini-2.5-flash")
            summary = await self._call_gemini(gemini_key, model, prompt)
        elif provider == "openai" and openai_key:
            model = ai_conf.get("openaiModel", "gpt-4o-mini")
            summary = await self._call_openai(openai_key, model, prompt)

        if summary:
            return summary

        # AI 呼び出しが失敗した場合の自動フォールバック文章
        log.warning("[AiService] AI要約が空または失敗したため、テキスト連結フォールバックを適用します")
        return f"保留されていた通知が{len(messages)}件あります。" + "。".join(messages[:3])

    async def _call_gemini(self, api_key: str, model: str, prompt: str) -> str:
        text, _ = await self._call_gemini_with_err(api_key, model, prompt)
        return text

    async def _call_gemini_with_err(self, api_key: str, model: str, prompt: str) -> tuple[str, Optional[str]]:
        # 廃止済みモデル（Gemini 1.5/2.0等）の自動補正
        valid_model = model or "gemini-2.5-flash"
        if any(p in valid_model for p in ["1.5", "1.0", "2.0"]):
            log.warning(f"[AiService] 廃止済みモデル '{valid_model}' が指定されたため、最新推奨モデル 'gemini-2.5-flash' に自動補正します")
            valid_model = "gemini-2.5-flash"


        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{valid_model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return text.strip(), None
                else:
                    err_msg = f"Gemini API エラー (HTTP {res.status_code}): {res.text}"
                    log.warning(f"[AiService] {err_msg}")
                    # モデル未検出等で失敗した場合、gemini-2.5-flash で自動フォールバック試行
                    if valid_model != "gemini-2.5-flash":
                        log.info(f"[AiService] フォールバックモデル 'gemini-2.5-flash' で再試行します...")
                        fb_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
                        res2 = await client.post(fb_url, json=payload)
                        if res2.status_code == 200:
                            data2 = res2.json()
                            candidates2 = data2.get("candidates", [])
                            if candidates2:
                                text2 = candidates2[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                                return text2.strip(), None
                    return "", err_msg
        except Exception as e:
            log.error(f"[AiService] Gemini 例外: {e}", exc_info=True)
            return "", str(e)
        return "", "要約の生成に失敗しました (空の応答)"

    async def _call_openai(self, api_key: str, model: str, prompt: str) -> str:
        text, _ = await self._call_openai_with_err(api_key, model, prompt)
        return text

    async def _call_openai_with_err(self, api_key: str, model: str, prompt: str) -> tuple[str, Optional[str]]:
        valid_model = model or "gpt-4o-mini"
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": valid_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"].strip(), None
                else:
                    err_msg = f"OpenAI API エラー (HTTP {res.status_code}): {res.text}"
                    log.warning(f"[AiService] {err_msg}")
                    return "", err_msg
        except Exception as e:
            log.error(f"[AiService] OpenAI 例外: {e}", exc_info=True)
            return "", str(e)

ai_service = AiService()
