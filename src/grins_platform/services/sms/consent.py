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
from grins_platform.models.alert import Alert
from grins_platform.models.customer import Customer
from grins_platform.models.enums import AlertType
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
    *,
    require_no_pending_informal: bool = False,
) -> bool:
    """Check SMS consent for a phone number with type-scoped semantics.

    Args:
        session: DB session.
        phone: Phone number (any format, normalized internally).
        consent_type: One of marketing/transactional/operational.
        require_no_pending_informal: When True, an unacknowledged
            INFORMAL_OPT_OUT alert for the customer tied to ``phone``
            blocks the send. Used for marketing + non-urgent transactional
            (reminders, review requests, campaigns). Urgent transactional
            (confirmation, on-the-way, completion) leave this False.

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

    if require_no_pending_informal:
        customer_id = await _resolve_customer_id_by_phone(session, e164)
        if customer_id is not None and await _has_open_informal_opt_out_alert(
            session,
            customer_id,
        ):
            return False

    if consent_type == "transactional":
        # EBR exemption: allowed unless hard-STOP (already checked above)
        return True

    # Marketing: require explicit opt-in record
    return await _has_marketing_opt_in(session, e164)


def _phone_variants(phone: str) -> list[str]:
    """Return the set of phone-string forms we accept for DB lookups.

    Historical Customer/Lead rows store phones in assorted shapes:
    bare 10-digit ``6127385301``, E.164 ``+16127385301``, hyphenated
    ``612-738-5301``, dotted ``612.738.5301``, parenthesized
    ``(612) 738-5301``, and country-code-prefixed ``1-612-738-5301`` /
    ``16127385301``. ``SmsConsentRecord`` is always E.164. Until the
    backfill catches every row (bughunt M-5), consent lookups must
    compare against every plausible form so opt-in/opt-out isn't
    silently lost.

    Accepts any input that ``phone_normalizer`` can normalize; raw
    E.164 is still a valid input and the function is idempotent on it.
    """
    # Import inline to avoid a hard cycle between consent.py and the
    # phone_normalizer module during module init.
    from grins_platform.services.sms.phone_normalizer import (  # noqa: PLC0415
        PhoneNormalizationError,
        normalize_to_e164,
    )

    try:
        e164 = normalize_to_e164(phone)
    except PhoneNormalizationError:
        # Fall back to the original behaviour when the input is too
        # exotic to normalize — at least the raw form matches itself.
        return [phone]

    bare = e164[2:]  # 10-digit subscriber number, e.g. "6127385301"
    area, prefix, line = bare[:3], bare[3:6], bare[6:]
    return [
        e164,  # +16127385301
        bare,  # 6127385301
        f"1{bare}",  # 16127385301
        f"{area}-{prefix}-{line}",  # 612-738-5301
        f"{area}.{prefix}.{line}",  # 612.738.5301
        f"({area}) {prefix}-{line}",  # (612) 738-5301
        f"1-{area}-{prefix}-{line}",  # 1-612-738-5301
    ]


async def _resolve_customer_id_by_phone(
    session: AsyncSession,
    e164: str,
) -> UUID | None:
    """Return the first customer_id whose phone matches any variant of e164."""
    variants = _phone_variants(e164)
    stmt = select(Customer.id).where(Customer.phone.in_(variants)).limit(1)
    result = await session.execute(stmt)
    row: UUID | None = result.scalar_one_or_none()
    return row


async def _has_open_informal_opt_out_alert(
    session: AsyncSession,
    customer_id: UUID,
) -> bool:
    """Check for an unacknowledged INFORMAL_OPT_OUT alert for the customer."""
    stmt = (
        select(Alert.id)
        .where(
            and_(
                Alert.type == AlertType.INFORMAL_OPT_OUT.value,
                Alert.entity_type == "customer",
                Alert.entity_id == customer_id,
                Alert.acknowledged_at.is_(None),
            ),
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


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

    stmt = pg_insert(SmsConsentRecord).values(rows).on_conflict_do_nothing()
    _ = await session.execute(stmt)
    await session.flush()
    return len(rows)
