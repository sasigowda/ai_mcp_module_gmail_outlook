import base64
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from typing import Optional, Any
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GmailClient:
    """Thin async-compatible wrapper around the Gmail REST API."""

    def __init__(self, credentials: Credentials):
        self._service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        body_html: Optional[str] = None,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
    ) -> dict:
        """Send an email via Gmail API."""
        if body_html:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(body_html, "html"))
        else:
            msg = MIMEText(body, "plain")

        msg["to"] = to
        msg["subject"] = subject
        if cc:
            msg["cc"] = cc
        if bcc:
            msg["bcc"] = bcc

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        result = self._service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

        return {"message_id": result["id"], "thread_id": result.get("threadId"), "status": "sent"}

    def list_messages(
        self,
        query: str = "",
        max_results: int = 10,
        label_ids: Optional[list[str]] = None,
    ) -> list[dict]:
        """List messages matching query (Gmail search syntax supported)."""
        params = {"userId": "me", "maxResults": max_results}
        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids

        result = self._service.users().messages().list(**params).execute()
        messages = result.get("messages", [])

        summaries = []
        for msg in messages:
            detail = self._service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"]
            ).execute()
            summaries.append(self._parse_message_summary(detail))

        return summaries

    def read_message(self, message_id: str) -> dict:
        """Read full message content by ID."""
        msg = self._service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        return self._parse_full_message(msg)

    def search_emails(self, query: str, max_results: int = 20) -> list[dict]:
        """Search emails using Gmail search operators."""
        return self.list_messages(query=query, max_results=max_results)

    def reply_email(self, message_id: str, body: str) -> dict:
        """Reply to an existing email thread."""
        original = self._service.users().messages().get(
            userId="me", id=message_id, format="metadata",
            metadataHeaders=["From", "To", "Subject", "Message-ID", "References"]
        ).execute()

        headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
        thread_id = original.get("threadId")

        reply_to = headers.get("From", "")
        subject = headers.get("Subject", "")
        if not subject.startswith("Re:"):
            subject = f"Re: {subject}"

        msg = MIMEText(body, "plain")
        msg["to"] = reply_to
        msg["subject"] = subject
        msg["In-Reply-To"] = headers.get("Message-ID", "")
        msg["References"] = headers.get("Message-ID", "")

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        result = self._service.users().messages().send(
            userId="me", body={"raw": raw, "threadId": thread_id}
        ).execute()

        return {"message_id": result["id"], "thread_id": result.get("threadId"), "status": "sent"}

    def list_labels(self) -> list[dict]:
        """List all Gmail labels."""
        result = self._service.users().labels().list(userId="me").execute()
        labels = result.get("labels", [])
        return [{"id": l["id"], "name": l["name"], "type": l.get("type", "user")} for l in labels]

    def get_attachment_metadata(self, message_id: str) -> list[dict]:
        """Get attachment metadata from a message without downloading."""
        msg = self._service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

        attachments = []
        for part in msg.get("payload", {}).get("parts", []):
            if part.get("filename"):
                attachments.append({
                    "filename": part["filename"],
                    "mime_type": part.get("mimeType"),
                    "size": part.get("body", {}).get("size", 0),
                    "attachment_id": part.get("body", {}).get("attachmentId"),
                })
        return attachments

    def _parse_message_summary(self, msg: dict) -> dict:
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        return {
            "id": msg["id"],
            "thread_id": msg.get("threadId"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "label_ids": msg.get("labelIds", []),
        }

    def _parse_full_message(self, msg: dict) -> dict:
        summary = self._parse_message_summary(msg)
        body = self._extract_body(msg.get("payload", {}))
        summary["body"] = body
        return summary

    def _extract_body(self, payload: dict) -> str:
        """Recursively extract plain text body from message payload."""
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

        for part in payload.get("parts", []):
            result = self._extract_body(part)
            if result:
                return result

        return ""
