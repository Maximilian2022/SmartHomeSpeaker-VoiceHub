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

    def is_available(self) -> bool:
        """AI機能が有効であり、選択プロバイダーのAPIキーが設定されているか判定"""
        ai_conf = settings_manager.get().get("ai", {})
        if not ai_conf.get("enabled", True):
            return False
        provider = ai_conf.get("provider", "gemini")
        if provider == "openai":
            key = ai_conf.get("openaiApiKey") or settings.openai_api_key
            return bool(key and key.strip())
        else:
            key = ai_conf.get("geminiApiKey") or settings.effective_gemini_key
            return bool(key and key.strip())

    def get_status(self) -> Dict[str, Any]:
        ai_conf = settings_manager.get().get("ai", {})
        dnd_conf = settings_manager.get().get("dnd", {})
        gemini_key = ai_conf.get("geminiApiKey") or settings.effective_gemini_key
        openai_key = ai_conf.get("openaiApiKey") or settings.openai_api_key

        model = ai_conf.get("geminiModel", "gemini-2.5-flash")
        if any(p in model for p in ["1.5", "1.0", "2.0"]):
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

    async def summarize_calendar_events(
        self,
        events: List[Dict[str, Any]],
        weather_info: Optional[Dict[str, Any]] = None,
        custom_prompt: Optional[str] = None
    ) -> str:
        """朝の予定と天気予報を統合し、スマートスピーカー読み上げ用の明るく簡潔なサマリーを生成"""
        ai_conf = settings_manager.get().get("ai", {})
        provider = ai_conf.get("provider", "gemini")
        gemini_key = ai_conf.get("geminiApiKey") or settings.effective_gemini_key
        openai_key = ai_conf.get("openaiApiKey") or settings.openai_api_key

        # 予定情報のテキスト化
        event_lines = []
        for ev in events:
            if isinstance(ev, dict):
                title = ev.get("summary") or ev.get("title") or "予定"
                if ev.get("isAllDay"):
                    event_lines.append(f"- 終日: {title}")
                else:
                    st = ev.get("start")
                    time_str = f"{st.hour}:{st.minute:02d}" if hasattr(st, "hour") else (str(st) if st else "時刻未定")
                    event_lines.append(f"- {time_str}〜: {title}")
            elif isinstance(ev, str):
                event_lines.append(f"- {ev}")

        events_text = "\n".join(event_lines) if event_lines else "本日の登録予定はありません。"

        weather_text = ""
        if isinstance(weather_info, dict):
            weather_text = f"天気: {weather_info.get('weather', '')} (降水確率 {weather_info.get('pop', '')}"
            if weather_info.get("tempMax"):
                weather_text += f", 最高気温 {weather_info.get('tempMax')}"
            weather_text += ")"
            if weather_info.get("advice"):
                weather_text += f"、アドバイス: {weather_info.get('advice')}"
        elif isinstance(weather_info, str):
            weather_text = weather_info

        prompt = (
            "あなたはスマートホームの親切な音声アシスタントです。\n"
            "朝、スマートスピーカーから家族へ読み上げる「本日の天気と予定のまとめ」を作成してください。\n"
            "【要件】\n"
            "- 自然で親しみやすく明るい日本語で、2〜4文（150字程度）で簡潔に話してください。\n"
            "- 「おはようございます」から始め、天気の要点、予定のハイライト、最後に励ましの一言を添えてください。\n"
            "- 箇条書きやマークダウン記号（*や#）、カッコなどは読み上げに邪魔になるため一切使わず、プレーンテキストのみで出力してください。\n"
        )
        if custom_prompt:
            prompt += f"追加指示: {custom_prompt}\n"
        if weather_text:
            prompt += f"\n【本日の気象情報】\n{weather_text}\n"
        prompt += f"\n【本日の予定】\n{events_text}\n"

        summary = ""
        if provider == "gemini" and gemini_key:
            model = ai_conf.get("geminiModel", "gemini-2.5-flash")
            summary = await self._call_gemini(gemini_key, model, prompt)
        elif provider == "openai" and openai_key:
            model = ai_conf.get("openaiModel", "gpt-4o-mini")
            summary = await self._call_openai(openai_key, model, prompt)

        if summary:
            # 余分な改行や記号を除去
            cleaned = summary.replace("*", "").replace("#", "").replace("\n", " ").strip()
            return cleaned

        log.warning("[AiService] カレンダーAI要約が失敗したためフォールバックします")
        return ""

    async def _call_gemini(self, api_key: str, model: str, prompt: str) -> str:
        text, _ = await self._call_gemini_with_err(api_key, model, prompt)
        return text

    async def _call_gemini_with_err(self, api_key: str, model: str, prompt: str) -> tuple[str, Optional[str]]:
        # 廃止済みモデル（Gemini 1.5/2.0等）の自動補正
        valid_model = model or "gemini-3.5-flash"
        if any(p in valid_model for p in ["1.5", "1.0", "2.0"]):
            log.warning(f"[AiService] 廃止済みモデル '{valid_model}' が指定されたため、最新推奨モデル 'gemini-3.5-flash' に自動補正します")
            valid_model = "gemini-3.5-flash"

        # フォールバック候補モデル（メインモデル以外を順次試行）
        fallback_candidates = [m for m in ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-latest"] if m != valid_model]
        models_to_try = [valid_model] + fallback_candidates[:2]

        last_error = "要約の生成に失敗しました"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            for idx, target_m in enumerate(models_to_try):
                try:
                    if idx > 0:
                        log.info(f"[AiService] フォールバックモデル '{target_m}' で再試行します...")
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_m}:generateContent?key={api_key}"
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if text.strip():
                                return text.strip(), None
                    else:
                        last_error = f"Gemini API エラー ({target_m}, HTTP {res.status_code}): {res.text[:200]}"
                        log.warning(f"[AiService] {last_error}")
                except httpx.TimeoutException as te:
                    last_error = f"Gemini API タイムアウト ({target_m}): {te}"
                    log.warning(f"[AiService] {last_error}")
                except Exception as e:
                    last_error = f"Gemini API 例外 ({target_m}): {e}"
                    log.error(f"[AiService] {last_error}")

        return "", last_error

    async def _call_openai(self, api_key: str, model: str, prompt: str) -> str:
        text, _ = await self._call_openai_with_err(api_key, model, prompt)
        return text

    async def _call_openai_with_err(self, api_key: str, model: str, prompt: str) -> tuple[str, Optional[str]]:
        valid_model = model or "gpt-4o-mini"
        try:
            is_reasoning_model = any(valid_model.startswith(prefix) for prefix in ["o1", "o3", "o4"])
            payload: Dict[str, Any] = {
                "model": valid_model,
                "messages": [{"role": "user", "content": prompt}]
            }
            if is_reasoning_model:
                payload["max_completion_tokens"] = 150
            else:
                payload["max_tokens"] = 150

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
