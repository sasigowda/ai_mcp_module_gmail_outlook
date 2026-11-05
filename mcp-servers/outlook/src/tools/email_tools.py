from typing import Any


def register_email_tools(mcp_server, get_client_fn):
    """Register Outlook email tools onto the MCP server."""

    @mcp_server.tool()
    async def send_email(
        to: str,
        subject: str,
        body: str,
        body_html: str = "",
        cc: str = "",
        bcc: str = "",
    ) -> dict[str, Any]:
        """
        Send an email via the authenticated Outlook/Microsoft 365 account.

        Args:
            to: Recipient email address (or comma-separated list)
            subject: Email subject line
            body: Plain text email body
            body_html: Optional HTML version of the body
            cc: Optional CC recipients (comma-separated)
            bcc: Optional BCC recipients (comma-separated)
        """
        client = get_client_fn()
        return await client.send_email(
            to=to, subject=subject, body=body,
            body_html=body_html or None,
            cc=cc or None, bcc=bcc or None,
        )

    @mcp_server.tool()
    async def list_inbox(
        max_results: int = 10,
        unread_only: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List emails from the Outlook inbox.

        Args:
            max_results: Maximum number of emails to return (1-50)
            unread_only: If True, only return unread emails
        """
        client = get_client_fn()
        return await client.list_inbox(max_results=min(max_results, 50), unread_only=unread_only)

    @mcp_server.tool()
    async def search_emails(
        query: str,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search Outlook emails by keyword or phrase.

        Args:
            query: Search query string
            max_results: Maximum results to return (1-50)
        """
        client = get_client_fn()
        return await client.search_emails(query=query, max_results=min(max_results, 50))

    @mcp_server.tool()
    async def read_email(message_id: str) -> dict[str, Any]:
        """
        Read the full content of a specific Outlook email.

        Args:
            message_id: The Outlook message ID (from list_inbox or search_emails)
        """
        client = get_client_fn()
        return await client.read_email(message_id)

    @mcp_server.tool()
    async def reply_email(
        message_id: str,
        body: str,
    ) -> dict[str, Any]:
        """
        Reply to an existing Outlook email.

        Args:
            message_id: The Outlook message ID to reply to
            body: The plain text reply body
        """
        client = get_client_fn()
        return await client.reply_email(message_id=message_id, body=body)

    @mcp_server.tool()
    async def get_attachment_metadata(message_id: str) -> list[dict[str, Any]]:
        """
        Get attachment metadata for an Outlook email (without downloading).

        Args:
            message_id: The Outlook message ID to inspect
        """
        client = get_client_fn()
        return await client.get_attachment_metadata(message_id)
