"""
MCP Client Service
Connects to MCP servers via HTTP/SSE and manages tool discovery + execution.
"""

import json
from typing import Any, AsyncGenerator

import httpx
import structlog

from ..core.config import settings

log = structlog.get_logger()


class MCPClientError(Exception):
    pass


class MCPClient:
    """HTTP-based MCP client that communicates with MCP servers."""

    def __init__(self, server_url: str, session_id: str = "default", timeout: float = 30.0):
        self.server_url = server_url.rstrip("/")
        self.session_id = session_id
        self._timeout = timeout

    async def health_check(self) -> dict:
        """Check MCP server health."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.server_url}/health")
            resp.raise_for_status()
            return resp.json()

    async def list_tools(self) -> list[dict]:
        """Discover all tools available on this MCP server."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{self.server_url}/tools",
                params={"session_id": self.session_id},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict:
        """Execute a tool via the direct HTTP endpoint (no SSE connection needed)."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.server_url}/tools/call",
                json={"name": tool_name, "arguments": arguments},
                params={"session_id": self.session_id},
            )
            resp.raise_for_status()
            data = resp.json()

        if not data.get("success", True):
            error_msg = data.get("result", {}).get("error", "Tool execution failed")
            raise MCPClientError(error_msg)

        return data.get("result", {})

    async def get_auth_status(self) -> dict:
        """Get OAuth connection status for this MCP server."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.server_url}/auth/status",
                params={"session_id": self.session_id},
            )
            resp.raise_for_status()
            return resp.json()

    def get_auth_url(self, provider: str) -> str:
        """Get the OAuth authorization URL for this MCP server."""
        if provider == "gmail":
            return f"{self.server_url}/oauth/gmail/authorize?user_session_id={self.session_id}"
        elif provider == "outlook":
            return f"{self.server_url}/oauth/outlook/authorize?user_session_id={self.session_id}"
        raise ValueError(f"Unknown provider: {provider}")

    async def disconnect(self) -> dict:
        """Disconnect / revoke credentials for this session."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(
                f"{self.server_url}/auth/disconnect",
                params={"session_id": self.session_id},
            )
            resp.raise_for_status()
            return resp.json()


class MCPManager:
    """Manages multiple MCP server connections for a user session."""

    # Pre-configured built-in server registry
    BUILTIN_SERVERS = {
        "gmail": {
            "name": "Gmail",
            "server_type": "gmail",
            "base_url": settings.gmail_mcp_url,
            "description": "Send and manage Gmail emails",
            "provider": "gmail",
        },
    }

    # Map server_type → internal Docker service URL for backend→MCP calls
    _INTERNAL_URLS: dict[str, str] = {
        "gmail": settings.gmail_mcp_url,  # "http://gmail-mcp:8001"
    }

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._clients: dict[str, MCPClient] = {}

    def _resolve_url(self, server_type: str, base_url: str) -> str:
        """Return the Docker-internal URL for a known server type, else base_url."""
        return self._INTERNAL_URLS.get(server_type, base_url)

    def get_client(self, server_type: str, base_url: str) -> MCPClient:
        """Get or create an MCP client using the internal Docker URL."""
        internal_url = self._resolve_url(server_type, base_url)
        key = f"{server_type}:{internal_url}"
        if key not in self._clients:
            self._clients[key] = MCPClient(
                server_url=internal_url,
                session_id=self.user_id,
            )
        return self._clients[key]

    async def discover_all_tools(self, servers: list[dict]) -> list[dict]:
        """Discover and aggregate tools from all connected MCP servers."""
        all_tools = []
        for server in servers:
            if not server.get("is_connected"):
                continue
            try:
                client = self.get_client(server["server_type"], server["base_url"])
                tools = await client.list_tools()
                for tool in tools:
                    tool["server_type"] = server["server_type"]
                    tool["server_id"] = str(server.get("id", ""))
                    tool["server_url"] = self._resolve_url(server["server_type"], server["base_url"])
                all_tools.extend(tools)
            except Exception as e:
                log.warning("Tool discovery failed", server=server["name"], error=str(e))

        return all_tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict,
        server_type: str,
        base_url: str,
    ) -> dict:
        """Execute a specific tool on the appropriate MCP server."""
        client = self.get_client(server_type, base_url)
        return await client.call_tool(tool_name, arguments)
