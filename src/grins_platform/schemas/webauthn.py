"""Pydantic schemas for the WebAuthn / Passkey API.

The ``credential`` and ``options`` fields are typed as ``dict`` because their
schemas are defined by the W3C and surfaced verbatim by the browser. The
``webauthn`` library accepts these dicts directly via its parse helpers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RegistrationBeginResponse(BaseModel):
    """Server response to ``POST /auth/webauthn/register/begin``."""

    handle: str = Field(
        ...,
        description="Opaque ceremony handle to return on /register/finish.",
    )
    options: dict[str, Any] = Field(
        ...,
        description="PublicKeyCredentialCreationOptions JSON for the browser.",
    )


class RegistrationFinishRequest(BaseModel):
    """Client payload for ``POST /auth/webauthn/register/finish``."""

    handle: str = Field(..., description="Ceremony handle from /register/begin.")
    device_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User-supplied label, e.g. 'Kirill's MacBook Pro'.",
    )
    credential: dict[str, Any] = Field(
        ...,
        description="Raw browser RegistrationResponseJSON.",
    )


class AuthenticationBeginRequest(BaseModel):
    """Client payload for ``POST /auth/webauthn/authenticate/begin``."""

    username: str | None = Field(
        default=None,
        max_length=50,
        description=(
            "Optional username hint. When omitted the server returns options "
            "for the discoverable-credential flow (autofill)."
        ),
    )


class AuthenticationBeginResponse(BaseModel):
    """Server response to ``POST /auth/webauthn/authenticate/begin``."""

    handle: str = Field(..., description="Ceremony handle to return on finish.")
    options: dict[str, Any] = Field(
        ...,
        description="PublicKeyCredentialRequestOptions JSON for the browser.",
    )


class AuthenticationFinishRequest(BaseModel):
    """Client payload for ``POST /auth/webauthn/authenticate/finish``."""

    handle: str = Field(..., description="Ceremony handle from /authenticate/begin.")
    credential: dict[str, Any] = Field(
        ...,
        description="Raw browser AuthenticationResponseJSON.",
    )


class PasskeyResponse(BaseModel):
    """Public-safe view of a registered passkey."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Internal credential row id.")
    device_name: str = Field(..., description="User-supplied device label.")
    credential_device_type: str = Field(
        ...,
        description="single_device or multi_device.",
    )
    backup_eligible: bool = Field(..., description="Eligible for cross-device sync.")
    created_at: datetime = Field(..., description="When the passkey was registered.")
    last_used_at: datetime | None = Field(
        default=None,
        description="Last successful authentication, if any.",
    )


class PasskeyListResponse(BaseModel):
    """Response wrapper for ``GET /auth/webauthn/credentials``."""

    passkeys: list[PasskeyResponse] = Field(default_factory=list)
