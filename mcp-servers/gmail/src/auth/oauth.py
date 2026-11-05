import json
import base64
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow

from ..config import settings


class TokenEncryption:
    """Handles Fernet symmetric encryption for OAuth tokens."""

    def __init__(self, key: str):
        key_bytes = base64.urlsafe_b64encode(
            hashlib.sha256(key.encode()).digest()
        )
        self._fernet = Fernet(key_bytes)

    def encrypt(self, data: str) -> str:
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()


token_encryption = TokenEncryption(settings.encryption_key)


class GmailOAuthHandler:
    """Manages Gmail OAuth2 PKCE flow and token lifecycle."""

    def __init__(self):
        self._pending_states: dict[str, str] = {}  # state -> user_session_id

    def create_auth_url(self, user_session_id: str) -> tuple[str, str]:
        """Generate OAuth authorization URL with PKCE state."""
        state = secrets.token_urlsafe(32)
        self._pending_states[state] = user_session_id

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uris": [settings.google_redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=settings.gmail_scopes,
        )
        flow.redirect_uri = settings.google_redirect_uri

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="consent",
        )

        return auth_url, state

    def validate_state(self, state: str) -> Optional[str]:
        """Validate OAuth state and return associated session ID."""
        return self._pending_states.pop(state, None)

    async def exchange_code(self, code: str, state: str) -> dict:
        """Exchange authorization code for tokens."""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uris": [settings.google_redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=settings.gmail_scopes,
            state=state,
        )
        flow.redirect_uri = settings.google_redirect_uri
        flow.fetch_token(code=code)

        credentials = flow.credentials
        user_info = await self._get_user_info(credentials.token)

        return {
            "access_token": token_encryption.encrypt(credentials.token),
            "refresh_token": token_encryption.encrypt(credentials.refresh_token) if credentials.refresh_token else None,
            "token_expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            "scope": " ".join(credentials.scopes or []),
            "account_email": user_info.get("email"),
            "account_name": user_info.get("name"),
        }

    async def _get_user_info(self, access_token: str) -> dict:
        """Fetch Google user profile."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()

    def build_credentials(self, encrypted_access_token: str, encrypted_refresh_token: Optional[str]) -> Credentials:
        """Reconstruct Google Credentials from encrypted storage."""
        access_token = token_encryption.decrypt(encrypted_access_token)
        refresh_token = token_encryption.decrypt(encrypted_refresh_token) if encrypted_refresh_token else None

        return Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=settings.gmail_scopes,
        )

    def refresh_credentials(self, credentials: Credentials) -> tuple[Credentials, dict]:
        """Refresh expired credentials and return updated encrypted tokens."""
        request = Request()
        credentials.refresh(request)

        updated = {
            "access_token": token_encryption.encrypt(credentials.token),
            "token_expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        }
        return credentials, updated


oauth_handler = GmailOAuthHandler()
