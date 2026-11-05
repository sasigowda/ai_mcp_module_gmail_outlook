import base64
import hashlib
import secrets
from typing import Optional

import httpx
import msal
from cryptography.fernet import Fernet

from ..config import settings


class TokenEncryption:
    def __init__(self, key: str):
        key_bytes = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        self._fernet = Fernet(key_bytes)

    def encrypt(self, data: str) -> str:
        return self._fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()


token_encryption = TokenEncryption(settings.encryption_key)


class OutlookOAuthHandler:
    """Manages Microsoft OAuth2 authorization code flow via MSAL."""

    def __init__(self):
        self._pending_states: dict[str, str] = {}
        self._app = msal.ConfidentialClientApplication(
            client_id=settings.azure_client_id,
            client_credential=settings.azure_client_secret,
            authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
        )

    def create_auth_url(self, user_session_id: str) -> tuple[str, str]:
        """Generate Microsoft OAuth authorization URL."""
        state = secrets.token_urlsafe(32)
        self._pending_states[state] = user_session_id

        auth_url = self._app.get_authorization_request_url(
            scopes=settings.outlook_scopes,
            redirect_uri=settings.azure_redirect_uri,
            state=state,
            prompt="consent",
        )
        return auth_url, state

    def validate_state(self, state: str) -> Optional[str]:
        return self._pending_states.pop(state, None)

    async def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for tokens using MSAL."""
        result = self._app.acquire_token_by_authorization_code(
            code=code,
            scopes=settings.outlook_scopes,
            redirect_uri=settings.azure_redirect_uri,
        )

        if "error" in result:
            raise RuntimeError(f"Token exchange failed: {result.get('error_description')}")

        user_info = await self._get_user_info(result["access_token"])

        return {
            "access_token": token_encryption.encrypt(result["access_token"]),
            "refresh_token": token_encryption.encrypt(result["refresh_token"]) if result.get("refresh_token") else None,
            "token_expiry": str(result.get("expires_in")),
            "scope": " ".join(result.get("scope", [])),
            "account_email": user_info.get("mail") or user_info.get("userPrincipalName"),
            "account_name": user_info.get("displayName"),
            "id_token": result.get("id_token"),
        }

    async def _get_user_info(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.graph_base_url}/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()

    def refresh_access_token(self, encrypted_refresh_token: str) -> dict:
        """Use refresh token to get a new access token via MSAL."""
        refresh_token = token_encryption.decrypt(encrypted_refresh_token)

        result = self._app.acquire_token_by_refresh_token(
            refresh_token=refresh_token,
            scopes=settings.outlook_scopes,
        )

        if "error" in result:
            raise RuntimeError(f"Token refresh failed: {result.get('error_description')}")

        return {
            "access_token": token_encryption.encrypt(result["access_token"]),
            "refresh_token": token_encryption.encrypt(result.get("refresh_token", refresh_token)),
        }


oauth_handler = OutlookOAuthHandler()
