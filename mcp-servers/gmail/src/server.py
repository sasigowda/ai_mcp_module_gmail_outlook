"""
Gmail MCP Server
Implements the Model Context Protocol over HTTP/SSE with Gmail OAuth2.
"""

import asyncio
import json
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

from .auth.oauth import oauth_handler, token_encryption
from .config import settings
from .gmail_client import GmailClient
from .tools import register_email_tools

log = structlog.get_logger()

# ── MCP Server instance ────────────────────────────────────────────────────────
mcp = FastMCP(
    name="gmail-mcp",
    version="1.0.0",
    instructions="Gmail MCP server. Tools for sending, reading, searching, and replying to emails.",
)

# ── Token persistence ─────────────────────────────────────────────────────────
TOKENS_DIR = Path("/app/tokens")
TOKENS_DIR.mkdir(parents=True, exist_ok=True)


def _token_path(session_id: str) -> Path:
    # Sanitize session_id so it's safe as a filename
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return TOKENS_DIR / f"{safe}.json"


def _save_session(session_id: str, data: dict) -> None:
    try:
        _token_path(session_id).write_text(json.dumps(data))
    except Exception as e:
        log.warning("Failed to persist token", session_id=session_id, error=str(e))


def _delete_session_file(session_id: str) -> None:
    try:
        _token_path(session_id).unlink(missing_ok=True)
    except Exception:
        pass


def _load_all_sessions() -> dict[str, dict]:
    loaded = {}
    for f in TOKENS_DIR.glob("*.json"):
        try:
            loaded[f.stem] = json.loads(f.read_text())
        except Exception as e:
            log.warning("Failed to load token file", file=str(f), error=str(e))
    return loaded


# ── In-memory session store — pre-loaded from disk on startup ─────────────────
# Maps session_id -> encrypted token bundle
_sessions: dict[str, dict] = _load_all_sessions()


def _get_gmail_client() -> GmailClient:
    """Retrieve current session credentials and return a GmailClient."""
    # Session injection via request context (set by middleware below)
    session_data = _current_session.get()
    if not session_data:
        raise RuntimeError("No authenticated Gmail session found. Please connect via OAuth first.")

    credentials = oauth_handler.build_credentials(
        encrypted_access_token=session_data["access_token"],
        encrypted_refresh_token=session_data.get("refresh_token"),
    )

    if credentials.expired and credentials.refresh_token:
        credentials, updated = oauth_handler.refresh_credentials(credentials)
        session_data.update(updated)
        # Persist refreshed token so it survives restarts
        session_id = next(
            (k for k, v in _sessions.items() if v is session_data), None
        )
        if session_id:
            _save_session(session_id, session_data)

    return GmailClient(credentials)


# Register all Gmail tools
register_email_tools(mcp, _get_gmail_client)

# ── FastAPI app ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Gmail MCP Server starting", port=settings.port)
    yield
    log.info("Gmail MCP Server shutting down")


app = FastAPI(
    title="Gmail MCP Server",
    description="MCP-compliant Gmail integration server",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Context var for per-request session injection
import contextvars
_current_session: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar(
    "_current_session", default=None
)


# ── OAuth Endpoints ───────────────────────────────────────────────────────────
@app.get("/oauth/gmail/authorize")
async def oauth_authorize(user_session_id: str = "default"):
    """Initiate Gmail OAuth2 flow. Redirect user to this endpoint."""
    auth_url, state = oauth_handler.create_auth_url(user_session_id)
    return RedirectResponse(url=auth_url)


@app.get("/oauth/gmail/callback")
async def oauth_callback(code: str, state: str, request: Request):
    """OAuth2 callback — exchanges code for tokens and stores session."""
    session_id = oauth_handler.validate_state(state)
    if not session_id:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        token_bundle = await oauth_handler.exchange_code(code, state)
        _sessions[session_id] = token_bundle
        _save_session(session_id, token_bundle)
        log.info("Gmail OAuth completed", email=token_bundle.get("account_email"))
    except Exception as e:
        log.error("OAuth callback failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"OAuth exchange failed: {e}")

    return HTMLResponse(content="""
        <html><body>
        <h2>✅ Gmail Connected Successfully!</h2>
        <p>You can close this window and return to the app.</p>
        <script>
            if (window.opener) {
                window.opener.postMessage({type: 'GMAIL_AUTH_SUCCESS'}, '*');
                window.close();
            }
        </script>
        </body></html>
    """)


@app.get("/auth/status")
async def auth_status(session_id: str = "default"):
    """Check if a session has valid Gmail credentials."""
    session = _sessions.get(session_id)
    if not session:
        return {"connected": False, "email": None}
    return {
        "connected": True,
        "email": session.get("account_email"),
        "name": session.get("account_name"),
        "scope": session.get("scope"),
    }


@app.delete("/auth/disconnect")
async def disconnect(session_id: str = "default"):
    """Revoke and remove session credentials."""
    _sessions.pop(session_id, None)
    _delete_session_file(session_id)
    return {"status": "disconnected"}


# ── Direct tool execution endpoint (no SSE required) ─────────────────────────

@app.post("/tools/call")
async def call_tool_direct(request: Request, session_id: str = "default"):
    """Execute a tool directly over HTTP without needing an active SSE connection."""
    body = await request.json()
    tool_name = body.get("name")
    arguments = body.get("arguments", {})

    if not tool_name:
        raise HTTPException(status_code=400, detail="Missing 'name'")

    tool = mcp._tool_manager._tools.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    session_data = _sessions.get(session_id)
    ctx_token = _current_session.set(session_data)
    try:
        if tool.is_async:
            result = await tool.fn(**arguments)
        else:
            result = await asyncio.to_thread(tool.fn, **arguments)
        return {"result": result, "success": True}
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        log.error("Tool execution failed", tool=tool_name, error=str(e))
        return {"result": {"error": str(e)}, "success": False}
    finally:
        _current_session.reset(ctx_token)


# ── MCP SSE Transport Endpoints ───────────────────────────────────────────────
sse_transport = SseServerTransport("/mcp/messages/")


@app.get("/mcp/sse")
async def mcp_sse(request: Request, session_id: str = "default"):
    """SSE endpoint for MCP clients to connect."""
    session_data = _sessions.get(session_id)
    token = _current_session.set(session_data)

    try:
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp._mcp_server.run(
                streams[0], streams[1],
                mcp._mcp_server.create_initialization_options(),
            )
    finally:
        _current_session.reset(token)


@app.post("/mcp/messages/")
async def mcp_messages(request: Request, session_id: str = "default"):
    """Message endpoint for MCP SSE transport."""
    session_data = _sessions.get(session_id)
    token = _current_session.set(session_data)
    try:
        return await sse_transport.handle_post_message(
            request.scope, request.receive, request._send
        )
    finally:
        _current_session.reset(token)


# ── Health / Info Endpoints ───────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gmail-mcp", "version": "1.0.0"}


@app.get("/tools")
async def list_tools():
    """List all registered MCP tools with full input schemas."""
    try:
        tools_map = mcp._tool_manager._tools
        tool_list = [
            {
                "name": name,
                "description": tool.description or "",
                "input_schema": tool.parameters or {"type": "object", "properties": {}},
            }
            for name, tool in tools_map.items()
        ]
    except Exception:
        tool_list = []
    return {"tools": tool_list}


@app.get("/")
async def root():
    return {"service": "Gmail MCP Server", "version": "1.0.0", "docs": "/docs"}
