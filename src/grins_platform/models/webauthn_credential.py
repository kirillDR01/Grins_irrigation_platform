"""WebAuthn / Passkey credential models.

Two tables: ``webauthn_user_handles`` (one row per staff, holds the opaque
W3C user handle) and ``webauthn_credentials`` (one row per registered passkey
device, can be many per staff).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
)
from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.staff import Staff


class WebAuthnUserHandle(Base):
    """Opaque per-staff WebAuthn user handle.

    Created lazily on first registration; one row per staff. Kept separate
    from the staff table so reverting WebAuthn doesn't touch staff schema.
    """

    __tablename__ = "webauthn_user_handles"

    staff_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_handle: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<WebAuthnUserHandle(staff_id={self.staff_id})>"


class WebAuthnCredential(Base):
    """One registered passkey for a staff member."""

    __tablename__ = "webauthn_credentials"

    __table_args__ = (
        CheckConstraint(
            "credential_device_type IN ('single_device', 'multi_device')",
            name="ck_webauthn_credentials_device_type",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    staff_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credential_id: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
        unique=True,
        index=True,
    )
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default="0",
    )
    transports: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    aaguid: Mapped[str | None] = mapped_column(String(36), nullable=True)
    credential_device_type: Mapped[str] = mapped_column(String(20), nullable=False)
    backup_eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    backup_state: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    staff: Mapped[Staff] = relationship("Staff", lazy="selectin")

    def __repr__(self) -> str:
        return (
            f"<WebAuthnCredential(id={self.id}, staff_id={self.staff_id}, "
            f"device_name={self.device_name!r})>"
        )
