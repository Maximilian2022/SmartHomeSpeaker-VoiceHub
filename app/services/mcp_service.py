import asyncio
import json
import uuid
import time
import hmac
from typing import Dict, Any, List, Optional
from app.services.speech_service import speech_service
from app.services.scheduled_speech_service import scheduled_speech_service
from app.services.devices_service import device_manager
from app.services.dnd_service import dnd_service
from app.services.calendar_service import calendar_service
from app.services.settings_service import settings_manager
from app.core.security import is_private_ip
from app.core.logger import get_logger

log = get_logger("MCP")

# MCP ツール定義
MCP_TOOLS = [
    {
        "name": "speak",
        "description": "自宅のスマートスピーカー（Google Cast, Alexa, HomePod, DLNA, ONVIF）から音声を読み上げます。個別スピーカーや全室一斉（ALL）の指定、未来日時の予約発声が可能です。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "読み上げるテキスト・メッセージ内容"
                },
                "target": {
                    "type": "string",
                    "description": "発声先スピーカー名、IPアドレス、またはマクロ（例: 'リビング', '寝室', '書斎', 'ALL', 'GH:ALL', 'AL:ALL', 'HP:ALL', 'DLNA:ALL'）。省略時はデフォルトスピーカー。"
                },
                "at": {
                    "type": "string",
                    "description": "発声希望日時 (ISO 8601形式 '2026-10-19T08:30:00'、時刻 '08:30'、または相対指定 '+10m', '+1h' など)。過去・現在なら即時発声、未来なら予約発声します。"
                },
                "volume": {
                    "type": "number",
                    "description": "音量（0.0〜1.0 または 0〜100）。省略時はシステム設定に従います。"
                },
                "voice": {
                    "type": "string",
                    "description": "TTS音声モデル（例: 'ja-JP-NanamiNeural', 'ja-JP-KeitaNeural' など）"
                },
                "urgent": {
                    "type": "boolean",
                    "description": "緊急モード（DND/おやすみモードを無視して強制発声するかどうか）。デフォルトは false。"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "list_scheduled_speeches",
        "description": "現在予約されている日時指定発声タスクの一覧を取得します。",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "cancel_scheduled_speech",
        "description": "予約されている日時指定発声タスクをキャンセルします。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "キャンセルする予約タスクの ID (例: 'speech_xxx')"
                }
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "list_speakers",
        "description": "宅内で利用可能なすべてのスマートスピーカー、防犯カメラ、登録済み部屋グループの一覧と現在の状態を取得します。",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_status",
        "description": "Voice Hub のシステム稼働状況、おやすみ・会議モード（DND）の有効状態、現在進行中のカレンダー会議予定を取得します。",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "set_dnd",
        "description": "おやすみ・会議モード（DND / 音声ミュート）を即時有効化または解除します。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "DND を有効にする場合は true、解除する場合は false"
                },
                "durationMinutes": {
                    "type": "number",
                    "description": "一時的な DND 持続時間（分）。省略時は手動解除まで持続。"
                },
                "reason": {
                    "type": "string",
                    "description": "DND を設定する理由（例: '集中作業中', '仮眠中' など）"
                }
            },
            "required": ["enabled"]
        }
    },
    {
        "name": "get_history",
        "description": "直近の音声読み上げ履歴ログを取得します。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "number",
                    "description": "取得する件数（1〜50、デフォルト: 10）"
                }
            }
        }
    }
]

class MCPSession:
    def __init__(self, session_id: str, client_ip: str, user_agent: str):
        self.session_id = session_id
        self.client_ip = client_ip
        self.user_agent = user_agent
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.created_at = time.time()
        self.last_active = time.time()

class MCPService:
    def __init__(self):
        self.sessions: Dict[str, MCPSession] = {}
        self.call_count = 0
        self.last_call_at: Optional[str] = None

    def create_session(self, client_ip: str, user_agent: str) -> MCPSession:
        session_id = uuid.uuid4().hex
        session = MCPSession(session_id, client_ip, user_agent)
        self.sessions[session_id] = session
        log.info(f"[MCP] New session connected: {session_id} (Client: {client_ip})")
        return session

    def get_session(self, session_id: str) -> Optional[MCPSession]:
        session = self.sessions.get(session_id)
        if session:
            session.last_active = time.time()
        return session

    def remove_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
            log.info(f"[MCP] Session removed: {session_id}")

    def verify_auth(self, token_candidate: Optional[str], client_ip: Optional[str] = None, is_tunnel: bool = False) -> bool:
        """
        MCP認証の検証:
        1. Webhookトークン または 管理者パスワード または 有効セッションとの照合
        2. 管理者パスワード設定時: 認証トークン/パスワード必須 (無認証アクセスは不可)
        3. 未設定時: トンネル経由時はトークン必須、宅内LAN直接アクセスのみ免除
        """
        from app.config import settings
        from app.core.security import ACTIVE_SESSIONS
        configured_token = settings_manager.get_webhook_token()
        admin_pass = settings_manager.get_admin_password()

        if token_candidate:
            tok = token_candidate.strip()
            if configured_token and hmac.compare_digest(tok, configured_token):
                return True
            if admin_pass and hmac.compare_digest(tok, admin_pass):
                return True
            if tok in ACTIVE_SESSIONS:
                return True

        # 管理者パスワードが設定されている場合は認証必須
        if admin_pass:
            return False

        # Webhookトークンが設定されている場合はトークン必須
        if configured_token:
            return False

        # どちらも未設定の場合: トンネル経由は遮断、宅内LAN直接のみ免除
        if is_tunnel:
            return False
        if client_ip and is_private_ip(client_ip):
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "activeSessions": len(self.sessions),
            "totalCalls": self.call_count,
            "lastCallAt": self.last_call_at,
            "tools": [t["name"] for t in MCP_TOOLS]
        }

    async def execute_tool(self, name: str, args: Dict[str, Any], client_name: str = "MCP Client", client_ip: str = "unknown") -> Dict[str, Any]:
        self.call_count += 1
        self.last_call_at = time.strftime("%Y-%m-%d %H:%M:%S")

        log.info(f"[MCP Tool Call] {name} args={args} (from {client_name})")

        try:
            if name == "speak":
                text = args.get("text", "").strip()
                if not text:
                    return {"isError": True, "content": [{"type": "text", "text": "エラー: text が指定されていません"}]}
                
                target = args.get("target") or ""
                volume = args.get("volume")
                voice = args.get("voice")
                urgent = bool(args.get("urgent", False))
                time_spec = args.get("at") or args.get("time") or args.get("scheduled_at")

                if time_spec:
                    res = await scheduled_speech_service.schedule_or_speak(
                        text=text,
                        time_spec=time_spec,
                        targets=[target] if target else [],
                        voice=voice,
                        volume_level=volume,
                        client_name=f"MCP ({client_name})",
                        client_ip=client_ip,
                        source="mcp",
                        source_label="MCP (Claude/Cursor)",
                        urgent=urgent
                    )
                    if res.get("status") == "scheduled":
                        return {
                            "isError": False,
                            "content": [{
                                "type": "text",
                                "text": f"発声予約を受け付けました。\n予定時刻: {res.get('scheduled_at')}\nタスクID: {res.get('task_id')}\nメッセージ: {text}\n対象: {target or 'デフォルト'}"
                            }]
                        }
                    else:
                        return {
                            "isError": False,
                            "content": [{
                                "type": "text",
                                "text": f"指定時刻（過去）のため即時発話しました。\n対象: {target or 'デフォルト'}\nメッセージ: {text}\nステータス: {res.get('status', 'ok')}"
                            }]
                        }

                res = await speech_service.speak(
                    text=text,
                    targets=[target] if target else [],
                    voice=voice,
                    volume_level=volume,
                    client_name=f"MCP ({client_name})",
                    client_ip=client_ip,
                    source="mcp",
                    source_label="MCP (Claude/Cursor)",
                    urgent=urgent
                )
                return {
                    "isError": False,
                    "content": [{
                        "type": "text",
                        "text": f"発話リクエストを正常に処理しました。\n対象: {target or 'デフォルト'}\nメッセージ: {text}\nステータス: {res.get('status', 'ok')}"
                    }]
                }

            elif name == "list_scheduled_speeches":
                tasks = scheduled_speech_service.get_pending_tasks()
                if not tasks:
                    return {"isError": False, "content": [{"type": "text", "text": "現在待機中の予約発声タスクはありません。"}]}
                lines = [f"■ 予約中の発声タスク ({len(tasks)}件):"]
                for t in tasks:
                    lines.append(f"- [{t.get('id')}] 予定: {t.get('scheduled_at')} (残り約{t.get('remaining_seconds', 0)}秒) | 宛先: {', '.join(t.get('targets', []))} | 文言: {t.get('text')}")
                return {"isError": False, "content": [{"type": "text", "text": "\n".join(lines)}]}

            elif name == "cancel_scheduled_speech":
                task_id = args.get("task_id", "").strip()
                if not task_id:
                    return {"isError": True, "content": [{"type": "text", "text": "エラー: task_id が指定されていません"}]}
                success = await scheduled_speech_service.cancel_task(task_id)
                if success:
                    return {"isError": False, "content": [{"type": "text", "text": f"予約タスク '{task_id}' を正常にキャンセルしました。"}]}
                else:
                    return {"isError": True, "content": [{"type": "text", "text": f"エラー: タスク '{task_id}' は見つからないか、既に実行/キャンセル済みです。"}]}

            elif name == "list_speakers":
                devs = await device_manager.get_devices()
                groups = settings_manager.get().get("deviceGroups", {})
                def_ip = device_manager.get_default_device_ip()

                speakers_info = []
                for d in devs:
                    speakers_info.append({
                        "name": d.get("name"),
                        "type": d.get("type"),
                        "ip": d.get("ip"),
                        "model": d.get("model", ""),
                        "isDefault": d.get("isDefault", False)
                    })

                summary = {
                    "defaultDeviceId": def_ip,
                    "totalDevices": len(speakers_info),
                    "devices": speakers_info,
                    "groups": groups,
                    "macros": ["ALL", "GH:ALL", "AL:ALL", "HP:ALL", "DLNA:ALL"]
                }
                return {
                    "isError": False,
                    "content": [{"type": "text", "text": json.dumps(summary, ensure_ascii=False, indent=2)}]
                }

            elif name == "get_status":
                mtg = calendar_service.get_current_meeting_title()
                dnd_status = dnd_service.get_global_status()
                status_data = {
                    "system": "running",
                    "currentTime": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "dnd": {
                        "active": dnd_status.get("active", False) or dnd_status.get("isActive", False),
                        "reason": dnd_status.get("reason") or "",
                        "action": dnd_status.get("action", "skip"),
                        "queuedCount": dnd_status.get("queuedCount", 0),
                        "until": dnd_status.get("until")
                    },
                    "currentCalendarMeeting": mtg
                }
                return {
                    "isError": False,
                    "content": [{"type": "text", "text": json.dumps(status_data, ensure_ascii=False, indent=2)}]
                }

            elif name == "set_dnd":
                enabled = bool(args.get("enabled", True))
                duration = args.get("durationMinutes")
                reason = args.get("reason", "MCP からの手動設定")

                dnd_conf = settings_manager.get().get("dnd", {})
                if enabled:
                    now_ts = time.time()
                    until_ts = (now_ts + (float(duration) * 60)) if duration else (now_ts + (365 * 24 * 3600))
                    settings_manager.update({
                        "dnd": {
                            **dnd_conf,
                            "manualUntil": until_ts,
                            "manualReason": reason
                        }
                    })
                    msg = f"DND (おやすみ・会議モード) を有効にしました。({reason}{f', {duration}分間' if duration else ''})"
                else:
                    settings_manager.update({
                        "dnd": {
                            **dnd_conf,
                            "manualUntil": None,
                            "manualReason": ""
                        }
                    })
                    await dnd_service.check_and_flush_queue()
                    msg = "DND (おやすみ・会議モード) を解除しました。"

                return {
                    "isError": False,
                    "content": [{"type": "text", "text": msg}]
                }

            elif name == "get_history":
                limit = min(int(args.get("limit", 10)), 50)
                history = speech_service.get_history()[:limit]
                items = []
                for h in history:
                    items.append({
                        "timestamp": h.get("timestamp"),
                        "text": h.get("text"),
                        "targets": h.get("targets"),
                        "source": h.get("sourceLabel") or h.get("source"),
                        "status": h.get("status")
                    })
                return {
                    "isError": False,
                    "content": [{"type": "text", "text": json.dumps(items, ensure_ascii=False, indent=2)}]
                }

            else:
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": f"不明なツール名です: {name}"}]
                }

        except Exception as e:
            log.error(f"[MCP Tool Error] {name}: {e}", exc_info=True)
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"ツール実行エラー: {str(e)}"}]
            }

    async def handle_jsonrpc(self, payload: Dict[str, Any], session: Optional[MCPSession]) -> Optional[Dict[str, Any]]:
        """JSON-RPC 2.0 リクエストの処理"""
        req_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params", {})

        if not method:
            return None

        # 1. initialize
        if method == "initialize":
            client_version = params.get("protocolVersion", "2024-11-05")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": client_version,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"listChanged": False},
                        "prompts": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": "smart-speaker-voice-hub",
                        "version": "2.0.0"
                    }
                }
            }

        # 2. notifications/initialized
        if method == "notifications/initialized":
            return None  # 通知には返信不要

        # 3. ping
        if method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {}
            }

        # 4. tools/list
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": MCP_TOOLS
                }
            }

        # 5. tools/call
        if method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            client_name = session.user_agent if session else "HTTP Client"
            client_ip = session.client_ip if session else "unknown"

            res = await self.execute_tool(tool_name, tool_args, client_name, client_ip)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": res
            }

        # 6. resources/list
        if method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "resources": []
                }
            }

        # 7. resources/templates/list
        if method == "resources/templates/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "resourceTemplates": []
                }
            }

        # 8. prompts/list
        if method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "prompts": []
                }
            }

        # 9. logging/setLevel
        if method == "logging/setLevel":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {}
            }

        # 未知のメソッド
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

mcp_service = MCPService()
