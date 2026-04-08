"""Type-scoped SMS consent check with hard-STOP precedence.

Three consent types:
  - marketing: requires explicit opt-in (form, START keyword, CSV attestation)
  - transactional: allowed under EBR exemption, respects hard-STOP
  - operational: always allowed (STOP confirmations, legal notices)

Hard-STOP precedence: if any SmsConsentRecord row for a phone has
consent_method='text_stop' and consent_given=false, deny ALL except operational.

Validates: Requirements 25, 26
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from grins_platform.log_config import get_logger
from grins_platform.models.customer import Customer
from grins_platform.models.lead import Lead
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.services.sms.phone_normalizer import normalize_to_e164

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

ConsentType = Literal["marketing", "transactional", "operational"]


async def check_sms_consent(
    session: AsyncSession,
    phone: str,
    consent_type: ConsentType = "transactional",
) -> bool:
    """Check SMS consent for a phone number with type-scoped semantics.

    Args:
        session: DB session.
        phone: Phone number (any format, normalized internally).
        consent_type: One of marketing/transactional/operational.

    Returns:
        True if sending is allowed, False otherwise.
    """
    if consent_type == "operational":
        return True

    e164 = normalize_to_e164(phone)

    # Hard-STOP check: any text_stop revocation blocks all non-operational
    hard_stop = await _has_hard_stop(session, e164)
    if hard_stop:
        return False

    if consent_type == "transactional":
        # EBR exemption: allowed unless hard-STOP (already checked above)
        return True

    # Marketing: require explicit opt-in record
    return await _has_marketing_opt_in(session, e164)


def _phone_variants(e164: str) -> list[str]:
    """Return the set of phone-string forms we accept for DB lookups.

    Historical Customer/Lead rows store phones as bare 10-digit strings
    (e.g. ``6127385301``), while newer rows and ``SmsConsentRecord`` are
    stored in E.164 (``+16127385301``). Until the data is normalized we
    must compare against both forms so opt-in status isn't silently lost.
    """
    variants = [e164]
    if e164.startswith("+1") and len(e164) == 12:
        variants.append(e164[2:])  # "6127385301"
    return variants


async def _has_hard_stop(session: AsyncSession, e164: str) -> bool:
    """Check if phone has a text_stop revocation record."""
    stmt = (
        select(SmsConsentRecord.id)
        .where(
            and_(
                SmsConsentRecord.phone_number.in_(_phone_variants(e164)),
                SmsConsentRecord.consent_method == "text_stop",
                SmsConsentRecord.consent_given.is_(False),
            ),
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _has_marketing_opt_in(session: AsyncSession, e164: str) -> bool:
    """Check for explicit marketing opt-in via consent record.

    Looks for any SmsConsentRecord with consent_type='marketing' and
    consent_given=true. Falls back to Customer.sms_opt_in / Lead.sms_consent
    if no consent records exist.
    """
    variants = _phone_variants(e164)

    # Check for explicit marketing consent record
    stmt = (
        select(SmsConsentRecord.id)
        .where(
            and_(
                SmsConsentRecord.phone_number.in_(variants),
                SmsConsentRecord.consent_type == "marketing",
                SmsConsentRecord.consent_given.is_(True),
            ),
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    if result.scalar_one_or_none() is not None:
        return True

    # Fallback: check Customer.sms_opt_in
    cust_stmt = (
        select(Customer.sms_opt_in)
        .where(
            and_(Customer.phone.in_(variants), Customer.sms_opt_in.is_(True)),
        )
        .limit(1)
    )
    cust_result = await session.execute(cust_stmt)
    if cust_result.scalar_one_or_none() is not None:
        return True

    # Fallback: check Lead.sms_consent
    lead_stmt = (
        select(Lead.sms_consent)
        .where(and_(Lead.phone.in_(variants), Lead.sms_consent.is_(True)))
        .limit(1)
    )
    lead_result = await session.execute(lead_stmt)
    return lead_result.scalar_one_or_none() is not None


async def bulk_insert_attestation_consent(
    session: AsyncSession,
    staff_id: UUID,
    phones: list[str],
    attestation_version: str,
    attestation_text: str,
) -> int:
    """Bulk-insert SmsConsentRecord rows for CSV staff attestation.

    Args:
        session: DB session.
        staff_id: ID of the staff member who confirmed the attestation.
        phones: List of phone numbers (any format).
        attestation_version: Version string (e.g. 'CSV_ATTESTATION_V1').
        attestation_text: Verbatim attestation language shown to staff.

    Returns:
        Number of consent records inserted.
    """
    now = datetime.now(timezone.utc)
    rows: list[dict[str, object]] = []
    for phone in phones:
        e164 = normalize_to_e164(phone)
        rows.append(
            {
                "phone_number": e164,
                "consent_type": "marketing",
                "consent_given": True,
                "consent_method": "csv_upload_staff_attestation",
                "consent_language_shown": attestation_text,
                "consent_form_version": attestation_version,
                "consent_timestamp": now,
                "created_by_staff_id": staff_id,
            },
        )

    if not rows:
        return 0

    stmt = pg_insert(SmsConsentRecord).values(rows)
    _ = await session.execute(stmt)
    await session.flush()
    return len(rows)
