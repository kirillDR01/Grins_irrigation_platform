"""SignWell API client — thin httpx wrapper for e-signature operations.

Validates: CRM Changes Update 2 Req 18.1, 18.3, 18.5, 18.6
"""

import hashlib
import hmac
from typing import Any

import httpx

from grins_platform.log_config import LoggerMixin
from grins_platform.services.signwell.config import SignWellSettings

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

_ERR_SECRET_MISSING = "Webhook secret not configured"
_ERR_SIGNATURE_INVALID = "Invalid webhook signature"


class SignWellError(Exception):
    """Base exception for SignWell API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


class SignWellDocumentNotFoundError(SignWellError):
    """Raised when a SignWell document is not found."""


class SignWellWebhookVerificationError(SignWellError):
    """Raised when webhook signature verification fails."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class SignWellClient(LoggerMixin):
    """Thin httpx wrapper for the SignWell REST API.

    Validates: CRM Changes Update 2 Req 18.5
    """

    DOMAIN = "signwell"

    def __init__(
        self,
        settings: SignWellSettings | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings or SignWellSettings()
        self._base_url = self.settings.signwell_api_base_url.rstrip("/")

    # -- helpers ----------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "X-Api-Key": self.settings.signwell_api_key,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated request to the SignWell API."""
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers(),
                **kwargs,
            )
        self._raise_for_status(response, path)
        return response.json()  # type: ignore[no-any-return]

    @staticmethod
    def _raise_for_status(
        response: httpx.Response,
        context: str,
    ) -> None:
        if response.status_code == 404:
            msg = f"Not found: {context}"
            raise SignWellDocumentNotFoundError(msg, status_code=404)
        if response.status_code >= 400:
            msg = f"API error {response.status_code}: {response.text}"
            raise SignWellError(msg, status_code=response.status_code)

    # -- public API -------------------------------------------------------

    async def create_document_for_email(
        self,
        pdf_url: str,
        email: str,
        name: str,
    ) -> dict[str, Any]:
        """Create a document and send for email signing.

        Validates: CRM Changes Update 2 Req 18.1
        """
        self.log_started("create_document_email", email=email)
        payload = {
            "test_mode": False,
            "files": [{"file_url": pdf_url}],
            "recipients": [{"email": email, "name": name}],
            "reminders": True,
        }
        result = await self._request("POST", "/documents", json=payload)
        self.log_completed(
            "create_document_email",
            document_id=result.get("id"),
        )
        return result

    async def create_document_for_embedded(
        self,
        pdf_url: str,
        signer_name: str,
    ) -> dict[str, Any]:
        """Create a document for embedded (on-site) signing.

        Validates: CRM Changes Update 2 Req 18.3
        """
        self.log_started(
            "create_document_embedded",
            signer_name=signer_name,
        )
        payload = {
            "test_mode": False,
            "embedded_signing": True,
            "files": [{"file_url": pdf_url}],
            "recipients": [
                {"name": signer_name, "placeholder_name": "Signer"},
            ],
        }
        result = await self._request("POST", "/documents", json=payload)
        self.log_completed(
            "create_document_embedded",
            document_id=result.get("id"),
        )
        return result

    async def get_embedded_url(self, document_id: str) -> str:
        """Get the embedded signing URL for a document.

        Validates: CRM Changes Update 2 Req 18.3
        """
        self.log_started("get_embedded_url", document_id=document_id)
        result = await self._request(
            "GET",
            f"/documents/{document_id}/embedded_signing_url",
        )
        url: str = result["embedded_signing_url"]
        self.log_completed("get_embedded_url", document_id=document_id)
        return url

    async def fetch_signed_pdf(self, document_id: str) -> bytes:
        """Download the completed signed PDF.

        Validates: CRM Changes Update 2 Req 18.4
        """
        self.log_started("fetch_signed_pdf", document_id=document_id)
        url = f"{self._base_url}/documents/{document_id}/completed_pdf"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=self._headers())
        self._raise_for_status(response, f"signed_pdf/{document_id}")
        self.log_completed("fetch_signed_pdf", document_id=document_id)
        return response.content

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify a SignWell webhook HMAC-SHA256 signature.

        Validates: CRM Changes Update 2 Req 18.6
        """
        if not self.settings.signwell_webhook_secret:
            self.log_rejected(
                "verify_webhook",
                reason=_ERR_SECRET_MISSING,
            )
            raise SignWellWebhookVerificationError(_ERR_SECRET_MISSING)
        expected = hmac.new(
            self.settings.signwell_webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            self.log_rejected(
                "verify_webhook",
                reason=_ERR_SIGNATURE_INVALID,
            )
            raise SignWellWebhookVerificationError(
                _ERR_SIGNATURE_INVALID,
            )
        return True
