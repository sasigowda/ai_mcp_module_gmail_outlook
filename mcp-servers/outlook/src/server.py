"""
Outlook MCP Server
Implements the Model Context Protocol over HTTP/SSE with Microsoft OAuth2.
"""

import contextvars
from contextlib import asynccontextmanager
from typing import Optional

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

from .auth.oauth import oauth_handler, token_encryption
from .config import settings
from .outlook_client import OutlookClient
from .tools import register_email_tools, register_calendar_tools

log = structlog.get_logger()

mcp = FastMCP(
    name="outlook-mcp",
    version="1.0.0",
    instructions="Outlook MCP server. Tools for Outlook mail and Calendar via Microsoft Graph API.",
)

_sessions: dict[str, dict] = {}
_current_session: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar(
    "_current_session", default=None
)


def _get_outlook_client() -> OutlookClient:
    session_data = _current_session.get()
    if not session_data:
        raise RuntimeError("No authenticated Outlook session. Please connect via OAuth first.")

    access_token = token_encryption.decrypt(session_data["access_token"])

    # Refresh if needed (token_expiry stored as expires_in seconds after issue)
    # For production, track absolute expiry timestamp
    return OutlookClient(access_token=access_token)


register_email_tools(mcp, _get_outlook_client)
register_calendar_tools(mcp, _get_outlook_client)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Outlook MCP Server starting", port=settings.port)
    yield
    log.info("Outlook MCP Server shutting down")


app = FastAPI(
    title="Outlook MCP Server",
    description="MCP-compliant Outlook/Microsoft 365 integration server",
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

sse_transport = SseServerTransport("/mcp/messages/")


@app.get("/oauth/outlook/authorize")
async def oauth_authorize(user_session_id: str = "default"):
    auth_url, state = oauth_handler.create_auth_url(user_session_id)
    return RedirectResponse(url=auth_url)


@app.get("/oauth/outlook/callback")
async def oauth_callback(code: str, state: str, request: Request):
    session_id = oauth_handler.validate_state(state)
    if not session_id:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        token_bundle = await oauth_handler.exchange_code(code)
        _sessions[session_id] = token_bundle
        log.info("Outlook OAuth completed", email=token_bundle.get("account_email"))
    except Exception as e:
        log.error("Outlook OAuth callback failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"OAuth exchange failed: {e}")

    return HTMLResponse(content="""
        <html><body>
        <h2>✅ Outlook Connected Successfully!</h2>
        <p>You can close this window and return to the app.</p>
        <script>
            if (window.opener) {
                window.opener.postMessage({type: 'OUTLOOK_AUTH_SUCCESS'}, '*');
                window.close();
            }
        </script>
        </body></html>
    """)


@app.get("/auth/status")
async def auth_status(session_id: str = "default"):
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
    _sessions.pop(session_id, None)
    return {"status": "disconnected"}


@app.get("/mcp/sse")
async def mcp_sse(request: Request, session_id: str = "default"):
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
    session_data = _sessions.get(session_id)
    token = _current_session.set(session_data)
    try:
        return await sse_transport.handle_post_message(
            request.scope, request.receive, request._send
        )
    finally:
        _current_session.reset(token)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "outlook-mcp", "version": "1.0.0"}


@app.get("/tools")
async def list_tools():
    tools = await mcp._mcp_server.list_tools()
    return {"tools": [{"name": t.name, "description": t.description} for t in tools.tools]}


@app.get("/")
async def root():
    return {"service": "Outlook MCP Server", "version": "1.0.0", "docs": "/docs"}
