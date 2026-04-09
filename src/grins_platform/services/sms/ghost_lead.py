"""Ghost lead creation for ad-hoc CSV campaign recipients.

Unmatched phones from CSV uploads auto-create Lead rows with
lead_source='campaign_import', preserving the SentMessage check
constraint that every message traces to a CRM entity.

Validates: Requirements 5.1, 5.2, 5.3, 45
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from grins_platform.log_config import get_logger
from grins_platform.models.lead import Lead
from grins_platform.services.sms.phone_normalizer import normalize_to_e164

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


async def create_or_get(
    session: AsyncSession,
    phone: str,
    first_name: str | None = None,
    last_name: str | None = None,
) -> Lead:
    """Find existing Lead by E.164 phone, or create a ghost lead.

    Uses SELECT ... FOR UPDATE row-level lock to prevent race conditions
    on concurrent CSV uploads creating duplicate ghost leads.

    Ghost leads have lead_source='campaign_import', status='new',
    sms_consent=false, source_site='campaign_csv_import'.

    Args:
        session: Async DB session (must be inside a transaction).
        phone: Raw phone string (will be normalized to E.164).
        first_name: Optional first name from CSV.
        last_name: Optional last name from CSV.

    Returns:
        Existing or newly created Lead.

    Raises:
        PhoneNormalizationError: If phone cannot be normalized.
    """
    normalized = normalize_to_e164(phone)

    # Row-level lock prevents concurrent duplicate creation
    stmt = select(Lead).where(Lead.phone == normalized).with_for_update().limit(1)
    result = await session.execute(stmt)
    existing: Lead | None = result.scalar_one_or_none()

    if existing is not None:
        new_name = " ".join(filter(None, [first_name, last_name])) or None
        if new_name and existing.name != new_name:
            existing.name = new_name
            logger.debug("sms.ghost_lead.updated_name", lead_id=str(existing.id), new_name=new_name)
        logger.debug(
            "sms.ghost_lead.found_existing",
            lead_id=str(existing.id),
        )
        return existing

    name = " ".join(filter(None, [first_name, last_name])) or "Unknown"

    lead = Lead(
        name=name,
        phone=normalized,
        situation="exploring",
        lead_source="campaign_import",
        source_site="campaign_csv_import",
        status="new",
        sms_consent=False,
    )
    session.add(lead)
    await session.flush()

    logger.info(
        "sms.ghost_lead.created",
        lead_id=str(lead.id),
    )
    return lead
