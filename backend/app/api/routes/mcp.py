"""MCP server management routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from ...core.database import get_db
from ...core.config import settings
from ...models.mcp_server import MCPServer, MCPTool
from ...models.user import User
from ...schemas.mcp import (
    MCPServerCreate, MCPServerOut, MCPServerUpdate,
    MCPToolOut, ToolExecuteRequest, AuthStatusOut, MCPHealthOut,
)
from ...middleware.auth_middleware import get_current_user
from ...services.mcp_client import MCPClient, MCPManager

router = APIRouter(prefix="/mcp", tags=["mcp"])
log = structlog.get_logger()


# ── Server CRUD ───────────────────────────────────────────────────────────────

@router.get("/servers", response_model=list[MCPServerOut])
async def list_servers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MCPServer).where(MCPServer.user_id == current_user.id)
    )
    servers = result.scalars().all()
    return [_server_to_out(s) for s in servers]


@router.post("/servers", response_model=MCPServerOut, status_code=status.HTTP_201_CREATED)
async def create_server(
    payload: MCPServerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check for duplicate server type per user
    existing = await db.execute(
        select(MCPServer).where(
            MCPServer.user_id == current_user.id,
            MCPServer.server_type == payload.server_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Server of type '{payload.server_type}' already exists")

    server = MCPServer(
        user_id=current_user.id,
        name=payload.name,
        server_type=payload.server_type,
        base_url=payload.base_url,
        description=payload.description,
    )
    db.add(server)
    await db.flush()
    return _server_to_out(server)


@router.get("/servers/{server_id}", response_model=MCPServerOut)
async def get_server(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await _get_user_server(server_id, current_user.id, db)
    return _server_to_out(server)


@router.patch("/servers/{server_id}", response_model=MCPServerOut)
async def update_server(
    server_id: str,
    payload: MCPServerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await _get_user_server(server_id, current_user.id, db)
    if payload.name is not None:
        server.name = payload.name
    if payload.description is not None:
        server.description = payload.description
    if payload.is_active is not None:
        server.is_active = payload.is_active
    return _server_to_out(server)


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await _get_user_server(server_id, current_user.id, db)
    await db.delete(server)


# ── Tool Discovery ────────────────────────────────────────────────────────────

@router.get("/servers/{server_id}/tools", response_model=list[MCPToolOut])
async def get_server_tools(
    server_id: str,
    refresh: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await _get_user_server(server_id, current_user.id, db)

    if refresh or not server.tools:
        # Live discovery from MCP server
        client = MCPClient(server_url=_internal_url(server), session_id=str(current_user.id))
        try:
            tools = await client.list_tools()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Cannot reach MCP server: {e}")

        # Upsert tools in DB
        existing_names = {t.name for t in server.tools}
        for tool_data in tools:
            if tool_data["name"] not in existing_names:
                tool = MCPTool(
                    mcp_server_id=server.id,
                    name=tool_data["name"],
                    description=tool_data.get("description"),
                    input_schema=tool_data.get("inputSchema"),
                )
                db.add(tool)
        await db.flush()

        result = await db.execute(select(MCPTool).where(MCPTool.mcp_server_id == server.id))
        return [_tool_to_out(t) for t in result.scalars().all()]

    return [_tool_to_out(t) for t in server.tools]


@router.patch("/servers/{server_id}/tools/{tool_id}")
async def toggle_tool(
    server_id: str,
    tool_id: str,
    is_enabled: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_server(server_id, current_user.id, db)
    result = await db.execute(
        select(MCPTool).where(MCPTool.id == tool_id, MCPTool.mcp_server_id == server_id)
    )
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    tool.is_enabled = is_enabled
    return {"id": str(tool.id), "is_enabled": is_enabled}


# ── Auth / OAuth ──────────────────────────────────────────────────────────────

@router.get("/servers/{server_id}/auth/status", response_model=AuthStatusOut)
async def auth_status(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await _get_user_server(server_id, current_user.id, db)
    client = MCPClient(server_url=_internal_url(server), session_id=str(current_user.id))
    try:
        status_data = await client.get_auth_status()
        connected = status_data.get("connected", False)
        server.is_connected = connected
        if connected:
            server.health_status = "healthy"
        return AuthStatusOut(
            connected=connected,
            email=status_data.get("email"),
            name=status_data.get("name"),
        )
    except Exception as e:
        server.is_connected = False
        server.health_status = "unhealthy"
        return AuthStatusOut(connected=False, email=None, name=None)


@router.get("/servers/{server_id}/auth/url")
async def get_auth_url(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await _get_user_server(server_id, current_user.id, db)
    client = MCPClient(server_url=server.base_url, session_id=str(current_user.id))
    auth_url = client.get_auth_url(server.server_type)
    return {"auth_url": auth_url, "server_type": server.server_type}


@router.delete("/servers/{server_id}/auth")
async def disconnect_auth(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await _get_user_server(server_id, current_user.id, db)
    client = MCPClient(server_url=_internal_url(server), session_id=str(current_user.id))
    try:
        result = await client.disconnect()
        server.is_connected = False
        return result
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


# ── Health Check ──────────────────────────────────────────────────────────────

@router.get("/servers/{server_id}/health", response_model=MCPHealthOut)
async def server_health(
    server_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await _get_user_server(server_id, current_user.id, db)
    client = MCPClient(server_url=_internal_url(server), session_id=str(current_user.id))
    try:
        await client.health_check()
        server.health_status = "healthy"
        server.last_health_check = datetime.now(timezone.utc)
        return MCPHealthOut(server_id=server_id, status="ok", health_status="healthy")
    except Exception as e:
        server.health_status = "unhealthy"
        server.last_health_check = datetime.now(timezone.utc)
        return MCPHealthOut(server_id=server_id, status="error", health_status="unhealthy")


# ── Tool Execution ────────────────────────────────────────────────────────────

@router.post("/tools/execute")
async def execute_tool(
    payload: ToolExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await _get_user_server(payload.server_id, current_user.id, db)
    client = MCPClient(server_url=_internal_url(server), session_id=str(current_user.id))
    try:
        result = await client.call_tool(payload.tool_name, payload.arguments)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Built-in server registry ──────────────────────────────────────────────────

@router.get("/registry")
async def get_registry():
    """Get list of pre-configured MCP server types."""
    return {"servers": list(MCPManager.BUILTIN_SERVERS.values())}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _internal_url(server: MCPServer) -> str:
    """Return the Docker-internal URL for backend→MCP calls.

    The base_url stored in the DB is the browser-facing URL (e.g. http://localhost:8001).
    From inside Docker the backend must use the service name instead.
    """
    _map = {
        "gmail": settings.gmail_mcp_url,  # "http://gmail-mcp:8001"
    }
    return _map.get(server.server_type, server.base_url)


async def _get_user_server(server_id: str, user_id, db: AsyncSession) -> MCPServer:
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id, MCPServer.user_id == user_id)
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server


def _server_to_out(s: MCPServer) -> MCPServerOut:
    return MCPServerOut(
        id=str(s.id),
        name=s.name,
        server_type=s.server_type,
        base_url=s.base_url,
        description=s.description,
        is_active=s.is_active,
        is_connected=s.is_connected,
        health_status=s.health_status,
        created_at=s.created_at.isoformat(),
    )


def _tool_to_out(t: MCPTool) -> MCPToolOut:
    return MCPToolOut(
        id=str(t.id),
        name=t.name,
        description=t.description,
        input_schema=t.input_schema,
        is_enabled=t.is_enabled,
    )
