"""SMS audit event helpers.

Thin wrappers around AuditService.log_action for SMS-specific events.

Validates: Requirement 41
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from grins_platform.log_config import get_logger
from grins_platform.services.audit_service import AuditService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

_audit = AuditService()


async def log_provider_switched(
    db: AsyncSession,
    *,
    provider_name: str,
) -> None:
    """Emit ``sms.provider.switched`` audit event."""
    _ = await _audit.log_action(
        db,
        action="sms.provider.switched",
        resource_type="sms_provider",
        details={"provider": provider_name},
    )


async def log_campaign_created(
    db: AsyncSession,
    *,
    campaign_id: UUID,
    actor_id: UUID | None = None,
    actor_role: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Emit ``sms.campaign.created`` audit event."""
    _ = await _audit.log_action(
        db,
        action="sms.campaign.created",
        resource_type="campaign",
        resource_id=campaign_id,
        actor_id=actor_id,
        actor_role=actor_role,
        details=details,
    )


async def log_campaign_sent_initiated(
    db: AsyncSession,
    *,
    campaign_id: UUID,
    actor_id: UUID | None = None,
    actor_role: str | None = None,
    recipient_count: int | None = None,
) -> None:
    """Emit ``sms.campaign.sent_initiated`` audit event."""
    details: dict[str, Any] = {}
    if recipient_count is not None:
        details["recipient_count"] = recipient_count
    _ = await _audit.log_action(
        db,
        action="sms.campaign.sent_initiated",
        resource_type="campaign",
        resource_id=campaign_id,
        actor_id=actor_id,
        actor_role=actor_role,
        details=details or None,
    )


async def log_campaign_cancelled(
    db: AsyncSession,
    *,
    campaign_id: UUID,
    actor_id: UUID | None = None,
    actor_role: str | None = None,
) -> None:
    """Emit ``sms.campaign.cancelled`` audit event."""
    _ = await _audit.log_action(
        db,
        action="sms.campaign.cancelled",
        resource_type="campaign",
        resource_id=campaign_id,
        actor_id=actor_id,
        actor_role=actor_role,
    )


async def log_csv_attestation_submitted(
    db: AsyncSession,
    *,
    upload_id: str | None = None,
    actor_id: UUID | None = None,
    actor_role: str | None = None,
    phone_count: int | None = None,
    attestation_version: str | None = None,
) -> None:
    """Emit ``sms.csv_attestation.submitted`` audit event."""
    details: dict[str, Any] = {}
    if upload_id is not None:
        details["upload_id"] = upload_id
    if phone_count is not None:
        details["phone_count"] = phone_count
    if attestation_version is not None:
        details["attestation_version"] = attestation_version
    _ = await _audit.log_action(
        db,
        action="sms.csv_attestation.submitted",
        resource_type="sms_consent",
        actor_id=actor_id,
        actor_role=actor_role,
        details=details or None,
    )


async def log_consent_hard_stop(
    db: AsyncSession,
    *,
    phone_masked: str,
) -> None:
    """Emit ``sms.consent.hard_stop_received`` audit event."""
    _ = await _audit.log_action(
        db,
        action="sms.consent.hard_stop_received",
        resource_type="sms_consent",
        details={"phone": phone_masked},
    )
