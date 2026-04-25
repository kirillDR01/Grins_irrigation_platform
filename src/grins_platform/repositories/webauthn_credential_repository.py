"""Repositories for WebAuthn / Passkey storage.

Two repos:
* :class:`WebAuthnUserHandleRepository` — gets-or-creates the opaque
  per-staff user handle bytes used in W3C ceremonies.
* :class:`WebAuthnCredentialRepository` — CRUD over registered passkeys.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, update

from grins_platform.log_config import LoggerMixin
from grins_platform.models.webauthn_credential import (
    WebAuthnCredential,
    WebAuthnUserHandle,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

# Per W3C, the user handle is up to 64 bytes of opaque randomness.
USER_HANDLE_BYTES = 64


class WebAuthnUserHandleRepository(LoggerMixin):
    """Persists the opaque per-staff WebAuthn user handle."""

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session = session

    async def get_or_create_for_staff(self, staff_id: UUID) -> bytes:
        """Return the staff member's user handle, creating it on first call.

        The handle is generated once with :func:`secrets.token_bytes` and
        stored permanently. Re-using the staff UUID would leak identity into
        WebAuthn ceremonies, which the W3C spec explicitly warns against.
        """
        self.log_started("get_or_create_for_staff", staff_id=str(staff_id))
        existing = await self.session.execute(
            select(WebAuthnUserHandle).where(
                WebAuthnUserHandle.staff_id == staff_id,
            ),
        )
        row = existing.scalar_one_or_none()
        if row is not None:
            self.log_completed(
                "get_or_create_for_staff",
                staff_id=str(staff_id),
                created=False,
            )
            return row.user_handle

        handle_bytes = secrets.token_bytes(USER_HANDLE_BYTES)
        new_row = WebAuthnUserHandle(
            staff_id=staff_id,
            user_handle=handle_bytes,
        )
        self.session.add(new_row)
        await self.session.flush()
        self.log_completed(
            "get_or_create_for_staff",
            staff_id=str(staff_id),
            created=True,
        )
        return handle_bytes


class WebAuthnCredentialRepository(LoggerMixin):
    """CRUD operations for registered passkeys."""

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session = session

    async def create(
        self,
        *,
        staff_id: UUID,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
        transports: list[str] | None,
        aaguid: str | None,
        credential_device_type: str,
        backup_eligible: bool,
        backup_state: bool,
        device_name: str,
    ) -> WebAuthnCredential:
        """Persist a freshly registered passkey."""
        self.log_started("create", staff_id=str(staff_id))
        cred = WebAuthnCredential(
            staff_id=staff_id,
            credential_id=credential_id,
            public_key=public_key,
            sign_count=sign_count,
            transports=transports,
            aaguid=aaguid,
            credential_device_type=credential_device_type,
            backup_eligible=backup_eligible,
            backup_state=backup_state,
            device_name=device_name,
        )
        self.session.add(cred)
        await self.session.flush()
        await self.session.refresh(cred)
        self.log_completed(
            "create",
            staff_id=str(staff_id),
            credential_row_id=str(cred.id),
        )
        return cred

    async def find_by_credential_id(
        self,
        credential_id: bytes,
    ) -> WebAuthnCredential | None:
        """Look up a non-revoked credential by its raw credential id."""
        stmt = select(WebAuthnCredential).where(
            WebAuthnCredential.credential_id == credential_id,
            WebAuthnCredential.revoked_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_staff(
        self,
        staff_id: UUID,
        *,
        include_revoked: bool = False,
    ) -> list[WebAuthnCredential]:
        """Return all credentials for a staff member."""
        stmt = select(WebAuthnCredential).where(
            WebAuthnCredential.staff_id == staff_id,
        )
        if not include_revoked:
            stmt = stmt.where(WebAuthnCredential.revoked_at.is_(None))
        stmt = stmt.order_by(WebAuthnCredential.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_sign_count(
        self,
        credential_id: bytes,
        new_sign_count: int,
    ) -> None:
        """Atomically bump sign_count and last_used_at for a credential."""
        stmt = (
            update(WebAuthnCredential)
            .where(WebAuthnCredential.credential_id == credential_id)
            .values(sign_count=new_sign_count, last_used_at=func.now())
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def revoke(
        self,
        credential_row_id: UUID,
        staff_id: UUID,
    ) -> bool:
        """Revoke a credential the user owns. Returns True if a row was updated.

        Filters by ``staff_id`` to prevent IDOR — a user can only revoke
        their own passkeys.
        """
        self.log_started(
            "revoke",
            credential_row_id=str(credential_row_id),
            staff_id=str(staff_id),
        )
        stmt = (
            update(WebAuthnCredential)
            .where(
                WebAuthnCredential.id == credential_row_id,
                WebAuthnCredential.staff_id == staff_id,
                WebAuthnCredential.revoked_at.is_(None),
            )
            .values(revoked_at=func.now())
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        revoked: bool = (result.rowcount or 0) > 0
        self.log_completed(
            "revoke",
            credential_row_id=str(credential_row_id),
            staff_id=str(staff_id),
            revoked=revoked,
        )
        return revoked

    async def revoke_by_credential_id(
        self,
        credential_id: bytes,
    ) -> None:
        """Revoke by raw credential id — used by sign-count regression defense."""
        stmt = (
            update(WebAuthnCredential)
            .where(
                WebAuthnCredential.credential_id == credential_id,
                WebAuthnCredential.revoked_at.is_(None),
            )
            .values(revoked_at=func.now())
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def list_credential_ids_for_staff(
        self,
        staff_id: UUID,
    ) -> list[tuple[bytes, list[str] | None]]:
        """Return ``(credential_id, transports)`` tuples for non-revoked rows.

        Used to populate ``exclude_credentials`` on registration so the user
        cannot re-enroll the same authenticator twice.
        """
        stmt = select(
            WebAuthnCredential.credential_id,
            WebAuthnCredential.transports,
        ).where(
            WebAuthnCredential.staff_id == staff_id,
            WebAuthnCredential.revoked_at.is_(None),
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [(row[0], row[1]) for row in rows]

    @staticmethod
    def to_response_dict(cred: WebAuthnCredential) -> dict[str, Any]:
        """Serialize a credential row for API responses (no public_key bytes)."""
        return {
            "id": str(cred.id),
            "device_name": cred.device_name,
            "credential_device_type": cred.credential_device_type,
            "backup_eligible": cred.backup_eligible,
            "created_at": cred.created_at,
            "last_used_at": cred.last_used_at,
        }
