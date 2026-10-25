import os
import time
import re
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings
from app.services.settings_service import settings_manager
from app.core.logger import get_logger

log = get_logger("AI")

DEFAULT_GEMINI_MODELS = [
    {"id": "gemini-2.5-flash", "name": "gemini-2.5-flash (最新主力・高速・推奨)"},
    {"id": "gemini-2.5-pro", "name": "gemini-2.5-pro (最高峰推論・高精度)"},
    {"id": "gemini-2.5-flash-lite", "name": "gemini-2.5-flash-lite (超軽量・即答)"}
]

DEFAULT_OPENAI_MODELS = [
    {"id": "gpt-4o-mini", "name": "gpt-4o-mini (高速・経済的・推奨)"},
    {"id": "gpt-4o", "name": "gpt-4o (最高性能フラグシップ)"},
    {"id": "o3-mini", "name": "o3-mini (高速推論特化)"},
    {"id": "o1", "name": "o1 (高度推論モデル)"},
    {"id": "gpt-4-turbo", "name": "gpt-4-turbo (GPT-4高性能版)"}
]

class AiService:
    def __init__(self):
        self._gemini_models_cache: Dict[str, Any] = {
            "api_key": "",
            "fetched_at": 0.0,
            "models": DEFAULT_GEMINI_MODELS
        }
        self._openai_models_cache: Dict[str, Any] = {
            "api_key": "",
            "fetched_at": 0.0,
            "models": DEFAULT_OPENAI_MODELS
        }

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

    async def get_gemini_models(self, api_key: str, force_refresh: bool = False) -> List[Dict[str, str]]:
        """
        Google Generative AI API から利用可能なモデル一覧を動的に取得。
        埋め込み、画像、実験用などの不要モデルを除外し、チャット・要約用モデルのみを厳選。
        キャッシュ (TTL: 1時間) を利用し、失敗時は安全なデフォルトリストにフォールバック。
        """
        now = time.time()
        if not force_refresh and self._gemini_models_cache.get("api_key") == api_key and (now - self._gemini_models_cache.get("fetched_at", 0)) < 3600:
            return self._gemini_models_cache.get("models", DEFAULT_GEMINI_MODELS)

        if not api_key or api_key.strip() == "********":
            return DEFAULT_GEMINI_MODELS

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    models_raw = data.get("models", [])
                    filtered_models = []
                    seen_ids = set()

                    for m in models_raw:
                        methods = m.get("supportedGenerationMethods", [])
                        if "generateContent" not in methods:
                            continue
                        m_id = m.get("name", "").replace("models/", "").strip()
                        if not m_id.startswith("gemini-"):
                            continue
                        
                        # 関係ない特殊・専用モデルの厳格な除外 (テキスト要約・発話生成に無関係なもの)
                        m_lower = m_id.lower()
                        if any(bad in m_lower for bad in ["embedding", "aqa", "image", "imagen", "learnlm", "robotics", "computer-use", "custom"]):
                            continue
                        # 日付スナップショット版（例: gemini-1.5-flash-001 等の固定版）は除外してメインエイリアスに絞る
                        if re.search(r"-\d{3}$", m_id) or re.search(r"-\d{8}$", m_id):
                            continue
                        
                        if m_id in seen_ids:
                            continue
                        seen_ids.add(m_id)

                        display_name = m.get("displayName") or m_id
                        # 推奨等のラベル付け
                        label = display_name
                        if "2.5-flash" in m_id:
                            label = f"{m_id} (最新主力・高速・推奨)"
                        elif "2.5-pro" in m_id:
                            label = f"{m_id} (最高峰推論・高精度)"
                        elif "flash-lite" in m_id:
                            label = f"{m_id} (超軽量・即答)"
                        elif display_name != m_id:
                            label = f"{m_id} ({display_name})"

                        filtered_models.append({"id": m_id, "name": label})

                    if filtered_models:
                        # 並び順を整理: flash系を先頭、pro系を次に
                        def model_sort_key(item):
                            mid = item["id"]
                            if "2.5-flash" in mid: return 0
                            if "2.5-pro" in mid: return 1
                            if "flash" in mid: return 2
                            if "pro" in mid: return 3
                            return 10
                        filtered_models.sort(key=model_sort_key)

                        self._gemini_models_cache = {
                            "api_key": api_key,
                            "fetched_at": now,
                            "models": filtered_models
                        }
                        log.info(f"[AiService] Gemini利用可能モデルを動的取得しました: {[m['id'] for m in filtered_models]}")
                        return filtered_models
                else:
                    log.warning(f"[AiService] Geminiモデル動的取得エラー (HTTP {res.status_code}): {res.text[:150]}")
        except Exception as e:
            log.warning(f"[AiService] Geminiモデル動的取得例外: {e}")

        return DEFAULT_GEMINI_MODELS

    async def get_openai_models(self, api_key: str, force_refresh: bool = False) -> List[Dict[str, str]]:
        """
        OpenAI API (GET https://api.openai.com/v1/models) から利用可能なモデル一覧を動的に取得。
        音声、画像、埋め込み、実験用・スナップショットを除外し、チャット・要約用主力モデルを厳選。
        キャッシュ (TTL: 1時間) を利用し、失敗時は安全なデフォルトリストにフォールバック。
        """
        now = time.time()
        if not force_refresh and self._openai_models_cache.get("api_key") == api_key and (now - self._openai_models_cache.get("fetched_at", 0)) < 3600:
            return self._openai_models_cache.get("models", DEFAULT_OPENAI_MODELS)

        if not api_key or api_key.strip() == "********":
            return DEFAULT_OPENAI_MODELS

        try:
            url = "https://api.openai.com/v1/models"
            headers = {
                "Authorization": f"Bearer {api_key.strip()}"
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    models_raw = data.get("data", [])
                    filtered_models = []
                    seen_ids = set()

                    for m in models_raw:
                        m_id = (m.get("id") or "").strip()
                        if not m_id:
                            continue

                        # チャット・要約向けモデル（gpt-* または o1*, o3*, o4* 等）のみ対象
                        is_chat_model = m_id.startswith("gpt-") or bool(re.match(r"^o[1-9]", m_id))
                        if not is_chat_model:
                            continue

                        m_lower = m_id.lower()
                        # 不要モデルの除外 (音声・画像・リアルタイム・検索・微調整・旧式・内部用)
                        if any(bad in m_lower for bad in [
                            "realtime", "audio", "search", "transcribe", "tts", "whisper",
                            "embedding", "dall-e", "babbage", "davinci", "moderation",
                            "instruct", "chatgpt-", "ft:"
                        ]):
                            continue

                        # 日付スナップショット版（例: gpt-4o-2024-08-06, gpt-4-0613, gpt-3.5-turbo-0125 等）を除外してメインエイリアスに絞る
                        if re.search(r"-\d{4}-\d{2}-\d{2}$", m_id) or re.search(r"-\d{4}$", m_id):
                            continue

                        if m_id in seen_ids:
                            continue
                        seen_ids.add(m_id)

                        # ラベル付け
                        label = m_id
                        if m_id == "gpt-4o-mini":
                            label = f"{m_id} (高速・経済的・推奨)"
                        elif m_id == "gpt-4o":
                            label = f"{m_id} (最高性能フラグシップ)"
                        elif m_id == "o3-mini":
                            label = f"{m_id} (高速推論特化)"
                        elif m_id == "o1":
                            label = f"{m_id} (高度推論モデル)"
                        elif m_id == "o1-mini":
                            label = f"{m_id} (軽量推論モデル)"
                        elif m_id == "gpt-4-turbo":
                            label = f"{m_id} (GPT-4高性能版)"
                        elif m_id == "gpt-3.5-turbo":
                            label = f"{m_id} (旧世代標準)"

                        filtered_models.append({"id": m_id, "name": label})

                    if filtered_models:
                        # 並び順を整理: gpt-4o-mini を先頭、次に gpt-4o、o3-mini、o1、その他
                        def openai_sort_key(item):
                            mid = item["id"].lower()
                            if mid == "gpt-4o-mini": return 0
                            if mid == "gpt-4o": return 1
                            if mid == "o3-mini": return 2
                            if mid == "o1": return 3
                            if mid == "o1-mini": return 4
                            if "gpt-4-turbo" in mid: return 5
                            if "gpt-4" in mid: return 6
                            if "o" in mid: return 7
                            if "gpt-3.5" in mid: return 20
                            return 10

                        filtered_models.sort(key=openai_sort_key)

                        self._openai_models_cache = {
                            "api_key": api_key,
                            "fetched_at": now,
                            "models": filtered_models
                        }
                        log.info(f"[AiService] OpenAI利用可能モデルを動的取得しました: {[m['id'] for m in filtered_models]}")
                        return filtered_models
                else:
                    log.warning(f"[AiService] OpenAIモデル動的取得エラー (HTTP {res.status_code}): {res.text[:150]}")
        except Exception as e:
            log.warning(f"[AiService] OpenAIモデル動的取得例外: {e}")

        return DEFAULT_OPENAI_MODELS

    async def _call_gemini(self, api_key: str, model: str, prompt: str) -> str:
        text, _ = await self._call_gemini_with_err(api_key, model, prompt)
        return text

    async def _call_gemini_with_err(self, api_key: str, model: str, prompt: str) -> tuple[str, Optional[str]]:
        if not api_key or api_key.strip() == "********":
            return "", "Gemini API キーが未設定か無効なマスク値です"

        # 動的に利用可能モデル一覧を取得して検証
        available_models = await self.get_gemini_models(api_key)
        available_ids = [m["id"] for m in available_models]

        valid_model = model.strip() if model else ""
        # 指定モデルが旧世代または未指定・利用不可の場合は最新の推奨モデルに補正
        if not valid_model or valid_model not in available_ids or any(p in valid_model for p in ["1.5", "1.0", "2.0"]):
            valid_model = available_ids[0] if available_ids else "gemini-2.5-flash"
            if model and model != valid_model:
                log.info(f"[AiService] モデル '{model}' を利用可能推奨モデル '{valid_model}' に自動補正しました")

        # フォールバック候補モデル（動的モデルリストからメイン以外を順次試行）
        fallback_candidates = [m_id for m_id in available_ids if m_id != valid_model]
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
        if not api_key or api_key.strip() == "********":
            return "", "OpenAI API キーが未設定か無効なマスク値です"

        available_models = await self.get_openai_models(api_key)
        available_ids = [m["id"] for m in available_models]
        valid_model = model.strip() if model else ""
        if not valid_model or valid_model not in available_ids:
            valid_model = available_ids[0] if available_ids else "gpt-4o-mini"
            if model and model != valid_model:
                log.info(f"[AiService] OpenAIモデル '{model}' を利用可能推奨モデル '{valid_model}' に自動補正しました")
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

            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
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
