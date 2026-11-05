"""Chat routes with WebSocket streaming and MCP tool calling."""

import json
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...core.database import get_db, AsyncSessionLocal
from ...core.security import decode_token
from ...models.conversation import Conversation, Message
from ...models.mcp_server import MCPServer, MCPTool
from ...models.user import User
from ...schemas.chat import ChatRequest, ConversationCreate, ConversationOut, MessageOut
from ...middleware.auth_middleware import get_current_user
from ...services.mcp_client import MCPManager
from ...services.llm_service import LLMService
from ...services.web_search import web_search, TOOL_DEFINITION as WEB_SEARCH_TOOL
from ...core.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])
log = structlog.get_logger()


# ── Conversation CRUD ─────────────────────────────────────────────────────────

@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id, Conversation.is_archived == False)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
    )
    convs = result.scalars().all()
    return [_conv_to_out(c) for c in convs]


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    provider = payload.llm_provider or settings.default_llm_provider
    conv = Conversation(
        user_id=current_user.id,
        title=payload.title,
        llm_provider=provider,
        llm_model=payload.llm_model or _default_model(provider),
        mcp_server_ids=payload.mcp_server_ids,
    )
    db.add(conv)
    await db.flush()
    return _conv_to_out(conv)


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
async def get_messages(
    conv_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await _get_user_conv(conv_id, current_user.id, db)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    return [_msg_to_out(m) for m in result.scalars().all()]


@router.delete("/conversations/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv = await _get_user_conv(conv_id, current_user.id, db)
    await db.delete(conv)


# ── WebSocket streaming chat ──────────────────────────────────────────────────

@router.websocket("/ws/{conv_id}")
async def chat_websocket(websocket: WebSocket, conv_id: str, db: AsyncSession = Depends(get_db)):
    """
    WebSocket endpoint for streaming chat with MCP tool support.
    Client must send auth token as first message: {"token": "<access_token>"}
    """
    await websocket.accept()

    # Authenticate via first message
    try:
        auth_msg = await websocket.receive_json()
        token = auth_msg.get("token", "")
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.send_json({"type": "error", "message": "Invalid token"})
            await websocket.close()
            return
        user_id = payload["sub"]
    except Exception as e:
        await websocket.send_json({"type": "error", "message": "Authentication failed"})
        await websocket.close()
        return

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        await websocket.send_json({"type": "error", "message": "User not found"})
        await websocket.close()
        return

    conv = await _get_user_conv(conv_id, user.id, db)

    await websocket.send_json({"type": "connected", "conversation_id": conv_id})

    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "").strip()

            if not user_message:
                await websocket.send_json({"type": "error", "message": "Empty message"})
                continue

            # Persist user message
            user_msg = Message(
                conversation_id=conv.id,
                role="user",
                content=user_message,
            )
            db.add(user_msg)
            await db.flush()

            # Auto-title conversation from first message
            if conv.message_count == 0:
                conv.title = user_message[:80]

            conv.message_count += 1
            await websocket.send_json({"type": "user_message_saved", "id": str(user_msg.id)})

            # Load conversation history
            history_result = await db.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at)
                .limit(50)
            )
            history = history_result.scalars().all()
            llm_messages = [
                {"role": m.role, "content": m.content or ""}
                for m in history
                if m.role in ("user", "assistant") and m.content
            ]

            # Load available tools from connected MCP servers
            servers_result = await db.execute(
                select(MCPServer).where(
                    MCPServer.user_id == user.id,
                    MCPServer.is_connected == True,
                    MCPServer.is_active == True,
                )
            )
            servers = servers_result.scalars().all()

            mcp_manager = MCPManager(user_id=str(user.id))
            server_dicts = [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "server_type": s.server_type,
                    "base_url": s.base_url,
                    "is_connected": s.is_connected,
                }
                for s in servers
            ]

            available_tools = await mcp_manager.discover_all_tools(server_dicts)

            # Build tool metadata lookup
            tool_metadata = {t["name"]: t for t in available_tools}

            # Stream LLM response
            llm = LLMService(provider=conv.llm_provider, model=conv.llm_model)
            full_response = ""

            async for event in llm.chat_stream(
                messages=llm_messages,
                available_tools=available_tools,
                execute_tool_fn=mcp_manager.execute_tool,
                tool_metadata=tool_metadata,
            ):
                await websocket.send_json(event)
                if event["type"] == "text":
                    full_response += event["content"]

            # Persist assistant message
            assistant_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=full_response,
            )
            db.add(assistant_msg)
            conv.message_count += 1
            await db.commit()

            await websocket.send_json({"type": "message_complete", "id": str(assistant_msg.id)})

    except WebSocketDisconnect:
        log.info("WebSocket disconnected", conv_id=conv_id)
    except Exception as e:
        log.error("WebSocket error", error=str(e), conv_id=conv_id)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# ── REST streaming chat (SSE fallback) ───────────────────────────────────────

@router.post("/send")
async def send_message(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and stream response via Server-Sent Events."""

    # ── All DB work happens HERE, before StreamingResponse is returned ──────────
    # FastAPI closes the injected `db` session when this coroutine returns, so
    # any DB access inside the generator below would use a dead session and raise
    # MissingGreenlet / "connection not checked in" errors.

    is_new_conv = not payload.conversation_id
    if payload.conversation_id:
        conv = await _get_user_conv(payload.conversation_id, current_user.id, db)
    else:
        provider = payload.llm_provider or settings.default_llm_provider
        conv = Conversation(
            user_id=current_user.id,
            title=payload.message[:80],
            llm_provider=provider,
            llm_model=payload.llm_model or _default_model(provider),
            mcp_server_ids=payload.mcp_server_ids,
        )
        db.add(conv)
        await db.flush()

    conv_id = str(conv.id)
    # Always use the currently configured provider — never the stale value stored
    # in the conversation row, which may reference a provider/model that no longer
    # applies (e.g. user changed from ollama → groq in .env).
    conv_provider = settings.default_llm_provider
    conv_model = _default_model(conv_provider)

    # Save user message
    user_msg = Message(conversation_id=conv.id, role="user", content=payload.message)
    db.add(user_msg)
    conv.message_count += 1
    await db.flush()

    # Load conversation history for the LLM
    history_result = await db.execute(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at).limit(10)
    )
    llm_messages = [
        {"role": m.role, "content": m.content or ""}
        for m in history_result.scalars().all()
        if m.role in ("user", "assistant") and m.content
    ]

    # Discover connected MCP tools
    servers_result = await db.execute(
        select(MCPServer).where(
            MCPServer.user_id == current_user.id,
            MCPServer.is_connected == True,
            MCPServer.is_active == True,
        )
    )
    servers = [
        {"id": str(s.id), "name": s.name, "server_type": s.server_type,
         "base_url": s.base_url, "is_connected": s.is_connected}
        for s in servers_result.scalars().all()
    ]

    mcp_manager = MCPManager(user_id=str(current_user.id))
    available_tools = await mcp_manager.discover_all_tools(servers)
    # Always add built-in tools (web_search is always available)
    available_tools.append(WEB_SEARCH_TOOL)
    tool_metadata = {t["name"]: t for t in available_tools}

    # Commit user message and conversation to DB before streaming starts
    await db.commit()

    llm = LLMService(provider=conv_provider, model=conv_model)

    async def execute_tool(tool_name: str, arguments: dict, server_type: str, base_url: str):
        """Route tool calls — built-ins run locally, MCP tools go to their server."""
        if server_type == "_builtin":
            if tool_name == "web_search":
                return await web_search(**arguments)
            raise ValueError(f"Unknown built-in tool: {tool_name}")
        return await mcp_manager.execute_tool(tool_name, arguments, server_type, base_url)

    # ── Generator only does LLM streaming — no DB session from outer scope ──────
    async def event_stream() -> AsyncGenerator[str, None]:
        if is_new_conv:
            yield f"data: {json.dumps({'type': 'conversation_id', 'id': conv_id})}\n\n"

        full_response = ""

        async for event in llm.chat_stream(
            messages=llm_messages,
            available_tools=available_tools,
            execute_tool_fn=execute_tool,
            tool_metadata=tool_metadata,
        ):
            yield f"data: {json.dumps(event)}\n\n"
            if event["type"] == "text":
                full_response += event["content"]

        # Save assistant response in a fresh session (outer session is already closed)
        async with AsyncSessionLocal() as save_db:
            assistant_msg = Message(
                conversation_id=conv_id,
                role="assistant",
                content=full_response,
            )
            save_db.add(assistant_msg)
            result = await save_db.execute(select(Conversation).where(Conversation.id == conv_id))
            conv_record = result.scalar_one_or_none()
            if conv_record:
                conv_record.message_count += 1
            await save_db.commit()
            msg_id = str(assistant_msg.id)

        yield f"data: {json.dumps({'type': 'done', 'message_id': msg_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_user_conv(conv_id: str, user_id, db: AsyncSession) -> Conversation:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


def _conv_to_out(c: Conversation) -> ConversationOut:
    return ConversationOut(
        id=str(c.id),
        title=c.title,
        llm_provider=c.llm_provider,
        llm_model=c.llm_model,
        message_count=c.message_count,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


def _msg_to_out(m: Message) -> MessageOut:
    return MessageOut(
        id=str(m.id),
        role=m.role,
        content=m.content,
        tool_calls=m.tool_calls,
        tool_results=m.tool_results,
        created_at=m.created_at.isoformat(),
    )


def _default_model(provider: str) -> str:
    if provider == "groq":
        return settings.groq_model
    if provider == "ollama":
        return settings.ollama_model
    if provider == "openai":
        return "gpt-4o"
    return settings.default_model
