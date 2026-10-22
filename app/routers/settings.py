import asyncio
from typing import Dict, Any
from fastapi import APIRouter
from app.services.settings_service import settings_manager
from app.services.speech_service import speech_service
from app.services.event_service import event_service
from app.services.dnd_service import dnd_service

router = APIRouter()

CHIME_CATALOG = [
    {
        "category": "標準・日常",
        "chimes": [
            {"id": "dingdong", "name": "ピンポン", "desc": "定番・標準の案内音 (1.8s)", "icon": "🔔"},
            {"id": "chime_simple", "name": "シンプル2音", "desc": "爽やかで短めな日常チャイム (1.1s)", "icon": "🎵"},
            {"id": "classic_doorbell", "name": "ドアベル", "desc": "軽快な2打 (1.2s)", "icon": "🚪"},
            {"id": "classic_triangle", "name": "トライアングル", "desc": "澄んだ金属音 (1.5s)", "icon": "📐"},
            {"id": "classic_cuckoo", "name": "鳩時計", "desc": "温かな木彫り時計 (1.2s)", "icon": "🐦"},
            {"id": "classic_step", "name": "ステップ3音", "desc": "上行3音 (1.3s)", "icon": "🪜"},
            {"id": "classic_warm", "name": "ウォームベル", "desc": "まろやかな2音 (1.4s)", "icon": "☕"},
            {"id": "classic_bright", "name": "ブライトチャイム", "desc": "明るい2音 (1.1s)", "icon": "☀️"},
            {"id": "classic_soft", "name": "ソフトチャイム", "desc": "優しいアタック (1.5s)", "icon": "☁️"},
            {"id": "classic_clarity", "name": "クラリティ", "desc": "澄み渡る単音 (1.6s)", "icon": "✨"},
        ]
    },
    {
        "category": "ホテル・高級ラウンジ",
        "chimes": [
            {"id": "chime_hotel", "name": "ホテルチャイム", "desc": "優雅な4音ロビー風ベル (2.2s)", "icon": "🏨"},
            {"id": "chime_marimba", "name": "マリンバ", "desc": "あたたかい木琴3音ポロン (1.5s)", "icon": "🪵"},
            {"id": "hotel_glockenspiel", "name": "グロッケン", "desc": "澄んだ鉄琴4音 (2.0s)", "icon": "🎹"},
            {"id": "hotel_vibes", "name": "ビブラフォン", "desc": "豊かな余韻の和音 (2.3s)", "icon": "🎷"},
            {"id": "hotel_concierge", "name": "コンシェルジュ", "desc": "卓上呼び鈴 (1.6s)", "icon": "🛎️"},
            {"id": "hotel_celesta", "name": "チェレスタ", "desc": "幻想的な高音 (2.1s)", "icon": "🌟"},
            {"id": "hotel_harp", "name": "ハープ", "desc": "優美な分散和音 (2.2s)", "icon": "🪕"},
            {"id": "hotel_rhodes", "name": "エレピ・ローズ", "desc": "落ち着いたメロウ和音 (2.0s)", "icon": "🍷"},
            {"id": "hotel_acoustic", "name": "アコースティック", "desc": "アコースティックギター調 (1.8s)", "icon": "🎸"},
            {"id": "hotel_suite", "name": "スイートルーム", "desc": "ラグジュアリーな5音 (2.4s)", "icon": "🥂"},
        ]
    },
    {
        "category": "和風・癒やし",
        "chimes": [
            {"id": "chime_zen", "name": "水琴窟・おりん", "desc": "静寂に染み渡る澄んだ響き (2.3s)", "icon": "🎐"},
            {"id": "chime_koto", "name": "雅・琴", "desc": "日本の伝統的な都節2音 (1.6s)", "icon": "🍵"},
            {"id": "zen_rin", "name": "仏具・おりん", "desc": "深遠な倍音と長い減衰 (3.0s)", "icon": "🪔"},
            {"id": "zen_hyoshigi", "name": "拍子木", "desc": "乾いた清らかな響き (1.0s)", "icon": "🪵"},
            {"id": "zen_suikinkutsu", "name": "水滴・雫", "desc": "水琴窟の涼やかな滴 (2.0s)", "icon": "💧"},
            {"id": "zen_windchime", "name": "南部鉄風鈴", "desc": "透き通る高音 (2.5s)", "icon": "🎐"},
            {"id": "zen_bamboo", "name": "鹿威し・竹筒", "desc": "ししおどし風 (1.4s)", "icon": "🎋"},
            {"id": "zen_miyabi", "name": "雅楽・笙の音", "desc": "ゆったりとした和音 (2.4s)", "icon": "🎎"},
            {"id": "zen_shakuhachi", "name": "尺八風", "desc": "静寂を切り拓く気息 (2.0s)", "icon": "🎋"},
            {"id": "zen_taiko", "name": "締太鼓", "desc": "締まりのある低音ポン (1.2s)", "icon": "🥁"},
        ]
    },
    {
        "category": "スマートホーム・近未来",
        "chimes": [
            {"id": "chime_cyber", "name": "サイバー", "desc": "近未来ガジェット風ピロリン (1.1s)", "icon": "🚀"},
            {"id": "chime_digital", "name": "デジタル", "desc": "クリアな高音アクセント (0.9s)", "icon": "⚡"},
            {"id": "cyber_assist", "name": "AIアシスタント", "desc": "受諾・起動ピピッ (0.9s)", "icon": "🤖"},
            {"id": "cyber_pulse", "name": "パルストーン", "desc": "近未来電子パルス (1.0s)", "icon": "📡"},
            {"id": "cyber_warp", "name": "ワープ", "desc": "空間跳躍シンセスイープ (1.2s)", "icon": "🌌"},
            {"id": "cyber_synapse", "name": "シナプス", "desc": "軽快なFMアルペジオ (1.1s)", "icon": "🧬"},
            {"id": "cyber_hologram", "name": "ホログラム", "desc": "立体投影起動トーン (1.3s)", "icon": "🌐"},
            {"id": "cyber_quantum", "name": "クァンタム", "desc": "クリアな位相変調音 (1.0s)", "icon": "🔬"},
            {"id": "cyber_laser", "name": "シンセレーザー", "desc": "歯切れ良い電子アクセント (0.8s)", "icon": "💫"},
            {"id": "cyber_blip", "name": "ブリッツ", "desc": "軽快な2連通知ビープ (0.7s)", "icon": "💠"},
        ]
    },
    {
        "category": "オルゴール・リラックス",
        "chimes": [
            {"id": "chime_musicbox", "name": "オルゴール", "desc": "やさしいキラキラ3音 (1.9s)", "icon": "🎠"},
            {"id": "relax_kalimba", "name": "カリンバ", "desc": "親指ピアノの温かい音 (1.8s)", "icon": "🎹"},
            {"id": "relax_crystal", "name": "クリスタルボウル", "desc": "純粋な水晶の共鳴 (2.5s)", "icon": "🔮"},
            {"id": "relax_lullaby", "name": "子守唄", "desc": "やさしいゆりかご3音 (2.0s)", "icon": "🌙"},
            {"id": "relax_starlight", "name": "星屑", "desc": "きらめく高音分散和音 (2.1s)", "icon": "🌠"},
            {"id": "relax_chime", "name": "ウィンドチャイム", "desc": "微風に揺れる金属管 (2.4s)", "icon": "🎐"},
            {"id": "relax_dream", "name": "ドリームトーン", "desc": "柔らかな夢心地の響き (2.2s)", "icon": "💭"},
            {"id": "relax_meadow", "name": "草原の朝", "desc": "爽やかな木漏れ日ベル (1.8s)", "icon": "🌿"},
            {"id": "relax_twinkle", "name": "トゥインクル", "desc": "可憐なガラスベル (1.6s)", "icon": "✨"},
            {"id": "relax_calm", "name": "カーム", "desc": "穏やかなアコースティック響き (2.0s)", "icon": "🕊️"},
        ]
    },
    {
        "category": "案内・注意喚起",
        "chimes": [
            {"id": "chime_airport", "name": "空港・駅", "desc": "明瞭な館内放送風3音 (1.9s)", "icon": "✈️"},
            {"id": "announce", "name": "アナウンス", "desc": "明るい注意喚起 (1.7s)", "icon": "📢"},
            {"id": "bell", "name": "ベル", "desc": "やさしいお知らせ (1.4s)", "icon": "🎶"},
            {"id": "alert", "name": "アラート", "desc": "重要通知・警告 (0.8s)", "icon": "⚠️"},
            {"id": "notice_broadcast", "name": "公共放送4音", "desc": "ピンポンパンポン (2.2s)", "icon": "🏢"},
            {"id": "notice_train", "name": "発車メロディ風", "desc": "親しみやすい上昇3音 (1.5s)", "icon": "🚆"},
            {"id": "notice_school", "name": "学校チャイム風", "desc": "ウェストミンスター2音 (1.8s)", "icon": "🏫"},
            {"id": "notice_info", "name": "インフォメーション", "desc": "案内サイン2点 (1.2s)", "icon": "ℹ️"},
            {"id": "notice_chime3", "name": "チャイム3音", "desc": "歯切れのよい通知3点 (1.4s)", "icon": "🔔"},
            {"id": "notice_urgent", "name": "注意喚起ダブル", "desc": "二連アクセント (1.0s)", "icon": "🚨"},
        ]
    },
    {
        "category": "その他",
        "chimes": [
            {"id": "none", "name": "チャイムなし", "desc": "前置き音なしで直接発話", "icon": "🔇"},
        ]
    }
]

@router.get("/api/chimes")
async def get_chimes():
    return {
        "currentChime": settings_manager.get().get("chime", "dingdong"),
        "catalog": CHIME_CATALOG
    }

MASK_STR = "********"

def mask_sensitive_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    """秘密情報 (APIキー、トークン、パスワード) をマスク処理"""
    from copy import deepcopy
    res = deepcopy(data)
    
    # 1. 管理者パスワード
    effective_pass = settings_manager.get_admin_password()
    res["hasAdminPassword"] = bool(effective_pass)
    res["adminPassword"] = MASK_STR if effective_pass else ""
    
    # 2. Webhook トークン
    effective_token = settings_manager.get_webhook_token()
    res["hasWebhookToken"] = bool(effective_token)
    if res.get("webhookToken"):
        res["webhookToken"] = MASK_STR

    # 3. AI サービス API キー
    if "ai" in res and isinstance(res["ai"], dict):
        if res["ai"].get("geminiApiKey"):
            res["ai"]["hasGeminiKey"] = True
            res["ai"]["geminiApiKey"] = MASK_STR
        else:
            res["ai"]["hasGeminiKey"] = False
        if res["ai"].get("openaiApiKey"):
            res["ai"]["hasOpenaiKey"] = True
            res["ai"]["openaiApiKey"] = MASK_STR
        else:
            res["ai"]["hasOpenaiKey"] = False

    # 4. MQTT パスワード
    if "mqtt" in res and isinstance(res["mqtt"], dict):
        if res["mqtt"].get("password"):
            res["mqtt"]["hasPassword"] = True
            res["mqtt"]["password"] = MASK_STR

    # 5. ONVIF パスワード
    if "onvif" in res and isinstance(res["onvif"], dict):
        if res["onvif"].get("defaultPassword"):
            res["onvif"]["hasPassword"] = True
            res["onvif"]["defaultPassword"] = MASK_STR

    # 6. TTS プロバイダー API キー
    if "ttsProviders" in res and isinstance(res["ttsProviders"], dict):
        for p_name, p_conf in res["ttsProviders"].items():
            if isinstance(p_conf, dict) and p_conf.get("apiKey"):
                p_conf["apiKey"] = MASK_STR

    return res

def unmask_sensitive_payload(payload: Dict[str, Any], current_settings: Dict[str, Any]) -> Dict[str, Any]:
    """マスク値 (********) が送られてきた場合は既存の設定値を維持"""
    cleaned = dict(payload)
    
    # 管理者パスワードの直接更新はセキュリティのため完全禁止 (/api/auth/password を利用)
    cleaned.pop("adminPassword", None)

    # Webhook トークン
    if cleaned.get("webhookToken") == MASK_STR:
        cleaned["webhookToken"] = current_settings.get("webhookToken")

    # AI API キー
    if "ai" in cleaned and isinstance(cleaned["ai"], dict):
        cur_ai = current_settings.get("ai", {})
        if cleaned["ai"].get("geminiApiKey") == MASK_STR:
            cleaned["ai"]["geminiApiKey"] = cur_ai.get("geminiApiKey")
        if cleaned["ai"].get("openaiApiKey") == MASK_STR:
            cleaned["ai"]["openaiApiKey"] = cur_ai.get("openaiApiKey")

    # MQTT パスワード
    if "mqtt" in cleaned and isinstance(cleaned["mqtt"], dict):
        cur_mqtt = current_settings.get("mqtt", {})
        if cleaned["mqtt"].get("password") == MASK_STR:
            cleaned["mqtt"]["password"] = cur_mqtt.get("password")

    # ONVIF パスワード
    if "onvif" in cleaned and isinstance(cleaned["onvif"], dict):
        cur_onvif = current_settings.get("onvif", {})
        if cleaned["onvif"].get("defaultPassword") == MASK_STR:
            cleaned["onvif"]["defaultPassword"] = cur_onvif.get("defaultPassword")

    # TTS プロバイダー API キー
    if "ttsProviders" in cleaned and isinstance(cleaned["ttsProviders"], dict):
        cur_providers = current_settings.get("ttsProviders", {})
        for p_name, p_conf in cleaned["ttsProviders"].items():
            if isinstance(p_conf, dict) and p_conf.get("apiKey") == MASK_STR:
                p_conf["apiKey"] = cur_providers.get(p_name, {}).get("apiKey")

    return cleaned

@router.get("/api/settings")
async def get_settings():
    raw = dict(settings_manager.get())
    return mask_sensitive_settings(raw)

@router.put("/api/settings")
@router.post("/api/settings")
async def update_settings(payload: Dict[str, Any]):
    current_settings = settings_manager.get()
    cleaned_payload = unmask_sensitive_payload(payload, current_settings)
    res = dict(settings_manager.update(cleaned_payload))
    if "dnd" in cleaned_payload:
        asyncio.create_task(event_service.broadcast("dnd_status", dnd_service.get_global_status()))
    return mask_sensitive_settings(res)

@router.post("/api/settings/sync-test")
async def sync_test():
    # 同期テスト音（「ポン、ピン、パン」）を発声
    return await speech_service.speak(
        text="ポン、ピン、パン。同期テストです。",
        targets="ALL",
        urgent=True
    )
