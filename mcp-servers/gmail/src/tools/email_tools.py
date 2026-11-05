from typing import Any
from ..gmail_client import GmailClient


def register_email_tools(mcp_server, get_client_fn):
    """Register all Gmail email tools onto the MCP server instance."""

    @mcp_server.tool()
    def send_email(
        to: str,
        subject: str,
        body: str,
        body_html: str = "",
        cc: str = "",
        bcc: str = "",
    ) -> dict[str, Any]:
        """
        Send an email via the authenticated Gmail account.

        Args:
            to: Recipient email address (or comma-separated list)
            subject: Email subject line
            body: Plain text email body
            body_html: Optional HTML version of the body
            cc: Optional CC recipients (comma-separated)
            bcc: Optional BCC recipients (comma-separated)
        """
        client: GmailClient = get_client_fn()
        return client.send_email(
            to=to,
            subject=subject,
            body=body,
            body_html=body_html or None,
            cc=cc or None,
            bcc=bcc or None,
        )

    @mcp_server.tool()
    def list_inbox(
        max_results: int = 10,
        unread_only: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List emails from the Gmail inbox.

        Args:
            max_results: Maximum number of emails to return (1-50)
            unread_only: If True, only return unread emails
        """
        client: GmailClient = get_client_fn()
        query = "is:unread" if unread_only else ""
        return client.list_messages(
            query=query,
            max_results=min(max_results, 50),
            label_ids=["INBOX"],
        )

    @mcp_server.tool()
    def search_emails(
        query: str,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search emails using Gmail search operators.

        Supports all Gmail search operators:
        - from:sender@example.com
        - to:recipient@example.com
        - subject:keyword
        - has:attachment
        - after:2024/01/01
        - before:2024/12/31
        - is:unread
        - label:inbox

        Args:
            query: Gmail search query string
            max_results: Maximum results to return (1-50)
        """
        client: GmailClient = get_client_fn()
        return client.search_emails(
            query=query,
            max_results=min(max_results, 50),
        )

    @mcp_server.tool()
    def read_email(message_id: str) -> dict[str, Any]:
        """
        Read the full content of a specific email by message ID.

        Args:
            message_id: The Gmail message ID (from list_inbox or search_emails)
        """
        client: GmailClient = get_client_fn()
        return client.read_message(message_id)

    @mcp_server.tool()
    def reply_email(
        message_id: str,
        body: str,
    ) -> dict[str, Any]:
        """
        Reply to an existing email thread.

        Args:
            message_id: The Gmail message ID to reply to
            body: The plain text reply body
        """
        client: GmailClient = get_client_fn()
        return client.reply_email(message_id=message_id, body=body)

    @mcp_server.tool()
    def list_labels() -> list[dict[str, Any]]:
        """List all Gmail labels in the authenticated account."""
        client: GmailClient = get_client_fn()
        return client.list_labels()

    @mcp_server.tool()
    def get_attachment_metadata(message_id: str) -> list[dict[str, Any]]:
        """
        Get metadata about attachments in an email (without downloading).

        Args:
            message_id: The Gmail message ID to inspect
        """
        client: GmailClient = get_client_fn()
        return client.get_attachment_metadata(message_id)
