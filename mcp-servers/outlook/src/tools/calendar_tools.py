from typing import Any, Optional


def register_calendar_tools(mcp_server, get_client_fn):
    """Register Outlook Calendar tools onto the MCP server."""

    @mcp_server.tool()
    async def get_calendar_events(
        max_results: int = 10,
        start_datetime: str = "",
        end_datetime: str = "",
    ) -> list[dict[str, Any]]:
        """
        Get upcoming calendar events from Outlook Calendar.

        Args:
            max_results: Maximum number of events to return (1-50)
            start_datetime: ISO 8601 start datetime filter (e.g. 2024-01-15T00:00:00)
            end_datetime: ISO 8601 end datetime filter (e.g. 2024-01-31T23:59:59)
        """
        client = get_client_fn()
        return await client.list_calendar_events(
            max_results=min(max_results, 50),
            start_datetime=start_datetime or None,
            end_datetime=end_datetime or None,
        )
