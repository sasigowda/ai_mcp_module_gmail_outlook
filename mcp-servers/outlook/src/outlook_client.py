"""Microsoft Graph API wrapper for Outlook Mail + Calendar."""

import httpx
from typing import Optional, Any
from .config import settings


class OutlookClient:
    """Async Microsoft Graph API client for Outlook mail and calendar."""

    def __init__(self, access_token: str):
        self._token = access_token
        self._base = settings.graph_base_url
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        body_html: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
    ) -> dict:
        """Send email via Microsoft Graph /me/sendMail."""
        content_type = "html" if body_html else "text"
        content = body_html if body_html else body

        recipients = [{"emailAddress": {"address": addr.strip()}} for addr in to.split(",")]
        payload: dict[str, Any] = {
            "message": {
                "subject": subject,
                "body": {"contentType": content_type, "content": content},
                "toRecipients": recipients,
            },
            "saveToSentItems": True,
        }

        if cc:
            payload["message"]["ccRecipients"] = [
                {"emailAddress": {"address": a.strip()}} for a in cc.split(",")
            ]
        if bcc:
            payload["message"]["bccRecipients"] = [
                {"emailAddress": {"address": a.strip()}} for a in bcc.split(",")
            ]

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base}/me/sendMail",
                json=payload,
                headers=self._headers,
            )
            resp.raise_for_status()

        return {"status": "sent", "subject": subject, "to": to}

    async def list_inbox(self, max_results: int = 10, unread_only: bool = False) -> list[dict]:
        """List messages from the Outlook inbox."""
        params: dict = {"$top": min(max_results, 50), "$orderby": "receivedDateTime desc"}
        if unread_only:
            params["$filter"] = "isRead eq false"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/me/mailFolders/inbox/messages",
                params=params,
                headers=self._headers,
            )
            resp.raise_for_status()
            messages = resp.json().get("value", [])

        return [self._format_message(m) for m in messages]

    async def search_emails(self, query: str, max_results: int = 20) -> list[dict]:
        """Search emails using Microsoft Graph $search."""
        params = {
            "$search": f'"{query}"',
            "$top": min(max_results, 50),
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/me/messages",
                params=params,
                headers={**self._headers, "ConsistencyLevel": "eventual"},
            )
            resp.raise_for_status()
            messages = resp.json().get("value", [])

        return [self._format_message(m) for m in messages]

    async def read_email(self, message_id: str) -> dict:
        """Read a specific email by ID."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/me/messages/{message_id}",
                headers=self._headers,
            )
            resp.raise_for_status()
            msg = resp.json()

        result = self._format_message(msg)
        result["body"] = msg.get("body", {}).get("content", "")
        return result

    async def reply_email(self, message_id: str, body: str) -> dict:
        """Reply to a specific email."""
        payload = {"comment": body}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base}/me/messages/{message_id}/reply",
                json=payload,
                headers=self._headers,
            )
            resp.raise_for_status()

        return {"status": "replied", "message_id": message_id}

    async def list_calendar_events(
        self,
        max_results: int = 10,
        start_datetime: Optional[str] = None,
        end_datetime: Optional[str] = None,
    ) -> list[dict]:
        """List upcoming calendar events."""
        params: dict = {"$top": min(max_results, 50), "$orderby": "start/dateTime"}

        if start_datetime and end_datetime:
            params["$filter"] = (
                f"start/dateTime ge '{start_datetime}' and end/dateTime le '{end_datetime}'"
            )

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/me/events",
                params=params,
                headers={**self._headers, "Prefer": 'outlook.timezone="UTC"'},
            )
            resp.raise_for_status()
            events = resp.json().get("value", [])

        return [self._format_event(e) for e in events]

    async def get_attachment_metadata(self, message_id: str) -> list[dict]:
        """Get attachment metadata for a message."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/me/messages/{message_id}/attachments",
                params={"$select": "id,name,contentType,size"},
                headers=self._headers,
            )
            resp.raise_for_status()
            attachments = resp.json().get("value", [])

        return [
            {
                "attachment_id": a["id"],
                "filename": a["name"],
                "mime_type": a.get("contentType"),
                "size": a.get("size", 0),
            }
            for a in attachments
        ]

    def _format_message(self, msg: dict) -> dict:
        return {
            "id": msg.get("id"),
            "subject": msg.get("subject", ""),
            "from": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
            "to": ", ".join(
                r.get("emailAddress", {}).get("address", "")
                for r in msg.get("toRecipients", [])
            ),
            "date": msg.get("receivedDateTime", ""),
            "is_read": msg.get("isRead", True),
            "has_attachments": msg.get("hasAttachments", False),
            "snippet": msg.get("bodyPreview", ""),
            "web_link": msg.get("webLink", ""),
        }

    def _format_event(self, event: dict) -> dict:
        return {
            "id": event.get("id"),
            "subject": event.get("subject", ""),
            "start": event.get("start", {}).get("dateTime", ""),
            "end": event.get("end", {}).get("dateTime", ""),
            "organizer": event.get("organizer", {}).get("emailAddress", {}).get("address", ""),
            "attendees": [
                a.get("emailAddress", {}).get("address", "")
                for a in event.get("attendees", [])
            ],
            "location": event.get("location", {}).get("displayName", ""),
            "is_online": event.get("isOnlineMeeting", False),
            "online_link": event.get("onlineMeeting", {}).get("joinUrl", ""),
            "body_preview": event.get("bodyPreview", ""),
        }
