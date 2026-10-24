import asyncio
import json
from typing import Optional, Dict, Any, List, Union
from fastapi import APIRouter, Request, HTTPException, Query, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from app.services.mcp_service import mcp_service, MCPSession
from app.core.security import is_tunnel_request
from app.routers.speech import extract_client_ip
from app.core.logger import get_logger

router = APIRouter()
log = get_logger("MCP.Router")

def get_token_from_request(request: Request) -> Optional[str]:
    # 1. クエリパラメータ ?token=...
    token = request.query_params.get("token")
    if token:
        return token
    # 2. ヘッダー x-webhook-token
    token = request.headers.get("x-webhook-token")
    if token:
        return token
    # 3. Authorization: Bearer <token>
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None

def resolve_or_create_session(request: Request, explicit_id: Optional[str] = None) -> MCPSession:
    """リクエストまたは引数からセッションを特定、無ければ自動生成"""
    sid = explicit_id or request.query_params.get("sessionId") or request.headers.get("mcp-session-id") or request.headers.get("x-session-id")
    if sid:
        session = mcp_service.get_session(sid)
        if session:
            return session

    client_ip = extract_client_ip(request)
    user_agent = request.headers.get("user-agent", "Unknown MCP Client")
    return mcp_service.create_session(client_ip, user_agent)

async def handle_jsonrpc_post(request: Request, explicit_id: Optional[str] = None) -> Response:
    """Streamable HTTP および messages エンドポイント共通の JSON-RPC POST ハンドラ"""
    token = get_token_from_request(request)
    client_ip = extract_client_ip(request)
    is_tunnel = is_tunnel_request(request)
    if not mcp_service.verify_auth(token, client_ip, is_tunnel=is_tunnel):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing MCP token")

    session = resolve_or_create_session(request, explicit_id)

    try:
        body = await request.json()
    except Exception as e:
        log.warning(f"[MCP] Invalid JSON body from {client_ip}: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # バッチ処理 (JSON-RPC 2.0 list) or 単一処理
    if isinstance(body, list):
        results = []
        for item in body:
            res = await mcp_service.handle_jsonrpc(item, session)
            if res is not None:
                results.append(res)
        response_data = results if results else None
    elif isinstance(body, dict):
        response_data = await mcp_service.handle_jsonrpc(body, session)
    else:
        raise HTTPException(status_code=400, detail="Payload must be a JSON object or array")

    resp_headers = {
        "Mcp-Session-Id": session.session_id,
        "Access-Control-Expose-Headers": "Mcp-Session-Id"
    }

    if response_data is None:
        # 通知 (Notification) の場合は 202 Accepted
        return Response(status_code=202, headers=resp_headers)

    # SSE クライアントが存在する場合、キューにも送信して同期
    try:
        await session.queue.put(json.dumps(response_data, ensure_ascii=False))
    except Exception:
        pass

    return JSONResponse(status_code=200, content=response_data, headers=resp_headers)

def create_sse_response(request: Request, session: MCPSession, token: Optional[str]) -> StreamingResponse:
    """SSE ストリーミングレスポンスを生成"""
    async def event_generator():
        try:
            # 1. 初期 endpoint イベントを発行 (相対パスおよび token 伝播)
            endpoint_url = f"/mcp/messages?sessionId={session.session_id}"
            if token:
                endpoint_url += f"&token={token}"
            yield f"event: endpoint\ndata: {endpoint_url}\n\n"

            # 2. メッセージキュー監視 & keep-alive
            while True:
                try:
                    msg_text = await asyncio.wait_for(session.queue.get(), timeout=15.0)
                    yield f"event: message\ndata: {msg_text}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                except asyncio.CancelledError:
                    break
        finally:
            mcp_service.remove_session(session.session_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Mcp-Session-Id": session.session_id,
            "Access-Control-Expose-Headers": "Mcp-Session-Id"
        }
    )

# --- SSE トランスポート GET エンドポイント ---

@router.get("/mcp/sse")
async def mcp_sse_get(request: Request):
    """Classic MCP SSE トランスポート接続 (GET)"""
    token = get_token_from_request(request)
    client_ip = extract_client_ip(request)
    is_tunnel = is_tunnel_request(request)
    if not mcp_service.verify_auth(token, client_ip, is_tunnel=is_tunnel):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing MCP token")

    session = resolve_or_create_session(request)
    return create_sse_response(request, session, token)

@router.get("/mcp")
async def mcp_root_get(request: Request):
    """/mcp へのアクセス: SSE ヘッダーがあれば SSE 接続、それ以外はステータス JSON"""
    token = get_token_from_request(request)
    client_ip = extract_client_ip(request)
    is_tunnel = is_tunnel_request(request)
    if not mcp_service.verify_auth(token, client_ip, is_tunnel=is_tunnel):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing MCP token")

    accept = request.headers.get("accept", "").lower()
    if "text/event-stream" in accept:
        session = resolve_or_create_session(request)
        return create_sse_response(request, session, token)
    return mcp_service.get_status()

# --- Streamable HTTP / JSON-RPC POST エンドポイント ---

@router.post("/mcp/sse")
async def mcp_sse_post(request: Request):
    """Streamable HTTP トランスポート: POST /mcp/sse (Gemini CLI / Antigravity / Cursor 対応)"""
    return await handle_jsonrpc_post(request)

@router.post("/mcp")
async def mcp_root_post(request: Request):
    """Streamable HTTP トランスポート: POST /mcp"""
    return await handle_jsonrpc_post(request)

@router.post("/mcp/messages")
async def mcp_messages_post(request: Request, sessionId: Optional[str] = Query(None)):
    """MCP JSON-RPC メッセージ処理: POST /mcp/messages (SSE セッション向け POST)"""
    return await handle_jsonrpc_post(request, explicit_id=sessionId)

# --- セッション終了 DELETE エンドポイント ---

@router.delete("/mcp/sse")
@router.delete("/mcp")
@router.delete("/mcp/messages")
async def mcp_delete(request: Request, sessionId: Optional[str] = Query(None)):
    """MCP セッション終了"""
    token = get_token_from_request(request)
    client_ip = extract_client_ip(request)
    is_tunnel = is_tunnel_request(request)
    if not mcp_service.verify_auth(token, client_ip, is_tunnel=is_tunnel):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing MCP token")

    sid = sessionId or request.headers.get("mcp-session-id") or request.headers.get("x-session-id")
    if sid:
        mcp_service.remove_session(sid)
    return Response(status_code=204)

# --- Web GUI 管理用エンドポイント ---

@router.get("/api/mcp/status")
async def get_mcp_status():
    """Web GUI 向け MCP ステータス情報"""
    return mcp_service.get_status()

class McpTestRequest(BaseModel):
    tool: str = "speak"
    arguments: Dict[str, Any] = {}

@router.post("/api/mcp/test")
async def test_mcp_tool(req: McpTestRequest):
    """Web GUI からの MCP ツール直接シミュレーション"""
    res = await mcp_service.execute_tool(req.tool, req.arguments, client_name="WebGUI Simulator", client_ip="127.0.0.1")
    return res

# --- RFC 8414 / RFC 9728 OAuth 2.0 Protected Resource Metadata (MCP クライアント自動検出用) ---

@router.get("/.well-known/oauth-protected-resource")
@router.get("/.well-known/oauth-protected-resource/mcp/sse")
@router.get("/.well-known/oauth-protected-resource/mcp")
async def oauth_protected_resource_metadata(request: Request):
    """Claude Desktop / Cursor 等の MCP クライアントからの RFC 8414 / RFC 9728 認可プローブ応答 (404 WARNING 抑止)"""
    base_url = str(request.base_url).rstrip("/")
    return {
        "resource": f"{base_url}/mcp/sse",
        "authorization_servers": [],
        "scopes_supported": ["speak", "status", "history"],
        "bearer_methods_supported": ["header", "query"],
        "resource_documentation": f"{base_url}/"
    }


