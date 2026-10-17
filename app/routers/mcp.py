import asyncio
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Query, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from app.services.mcp_service import mcp_service
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

@router.get("/mcp/sse")
async def mcp_sse(request: Request):
    """MCP SSE (Server-Sent Events) トランスポート接続エンドポイント"""
    token = get_token_from_request(request)
    if not mcp_service.verify_auth(token):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid MCP token")

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "Unknown AI Client")
    session = mcp_service.create_session(client_ip, user_agent)

    async def event_generator():
        try:
            # 1. 初期 endpoint イベントを発行
            endpoint_url = f"/mcp/messages?sessionId={session.session_id}"
            if token:
                endpoint_url += f"&token={token}"
            yield f"event: endpoint\ndata: {endpoint_url}\n\n"

            # 2. メッセージキュー監視 & keep-alive
            while True:
                try:
                    # 15秒タイムアウトでキュー待機
                    msg_text = await asyncio.wait_for(session.queue.get(), timeout=15.0)
                    yield f"event: message\ndata: {msg_text}\n\n"
                except asyncio.TimeoutError:
                    # クライアント切断防止のための keep-alive コメント
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
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/mcp/messages")
async def mcp_messages(request: Request, sessionId: str = Query(...)):
    """MCP JSON-RPC メッセージ処理エンドポイント"""
    token = get_token_from_request(request)
    if not mcp_service.verify_auth(token):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid MCP token")

    session = mcp_service.get_session(sessionId)
    if not session:
        raise HTTPException(status_code=404, detail=f"MCP Session '{sessionId}' not found or expired")

    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # JSON-RPC を処理
    response_rpc = await mcp_service.handle_jsonrpc(body, session)

    if response_rpc:
        # SSE キューに送信
        await session.queue.put(json.dumps(response_rpc, ensure_ascii=False))
        # HTTP レスポンスとしても直接返却 (クライアントの互換性を最大化)
        return JSONResponse(status_code=200, content=response_rpc)
    else:
        return Response(status_code=202)

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
