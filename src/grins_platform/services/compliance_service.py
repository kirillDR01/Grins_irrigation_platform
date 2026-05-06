"""Compliance service for MN auto-renewal disclosures and TCPA SMS consent.

Manages immutable disclosure records and SMS consent records.
INSERT-ONLY enforcement — records are never updated or deleted.

Validates: Requirements 29.1, 29.2, 30.2, 30.3, 33.1, 33.2, 33.3, 33.4,
34.1, 34.2, 34.3, 35.1, 35.2, 36.1, 36.2, 37.1, 37.2, 37.3, 38.1, 38.2, 38.3
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import extract, select
from sqlalchemy.orm import selectinload

from grins_platform.exceptions import ConsentValidationError
from grins_platform.log_config import LoggerMixin
from grins_platform.models.consent_language_version import ConsentLanguageVersion
from grins_platform.models.disclosure_record import DisclosureRecord
from grins_platform.models.enums import AgreementStatus, DisclosureType
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.models.sms_consent_record import SmsConsentRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _resolve_consent_timestamp(value: datetime | None) -> datetime:
    """Resolve a (possibly naive) consent timestamp to a tz-aware UTC datetime.

    Returns ``datetime.now(timezone.utc)`` when no value is provided.
    Defensive — the schema validator already coerces naive→UTC, but a
    future internal caller might bypass the schema layer.
    """
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class ComplianceStatus:
    """Status of compliance disclosures for an agreement."""

    def __init__(
        self,
        agreement_id: UUID,
        recorded: list[str],
        missing: list[str],
    ) -> None:
        """Initialize compliance status."""
        self.agreement_id = agreement_id
        self.recorded = recorded
        self.missing = missing


class ComplianceService(LoggerMixin):
    """Service for compliance disclosure and SMS consent management.

    Validates: Requirements 29.1, 29.2, 30.2, 30.3, 33.1, 33.2, 33.3, 33.4,
    34.1, 34.2, 34.3, 35.1, 35.2, 36.1, 36.2, 37.1, 37.2, 37.3, 38.1, 38.2, 38.3
    """

    DOMAIN = "compliance"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__()
        self.session = session

    async def create_disclosure(
        self,
        disclosure_type: DisclosureType,
        agreement_id: UUID | None,
        customer_id: UUID | None,
        content: str,
        sent_via: str,
        *,
        recipient_email: str | None = None,
        recipient_phone: str | None = None,
        consent_token: UUID | None = None,
        delivery_confirmed: bool = False,
    ) -> DisclosureRecord:
        """Create an immutable disclosure record with content hash.

        Validates: Requirements 33.1, 33.2, 33.3, 33.4
        """
        self.log_started(
            "create_disclosure",
            disclosure_type=disclosure_type.value,
            agreement_id=str(agreement_id) if agreement_id else None,
        )

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        record = DisclosureRecord(
            agreement_id=agreement_id,
            customer_id=customer_id,
            disclosure_type=disclosure_type.value,
            sent_at=datetime.now(timezone.utc),
            sent_via=sent_via,
            recipient_email=recipient_email,
            recipient_phone=recipient_phone,
            content_hash=content_hash,
            content_snapshot=content,
            consent_token=consent_token,
            delivery_confirmed=delivery_confirmed,
        )
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)

        self.log_completed(
            "create_disclosure",
            record_id=str(record.id),
            disclosure_type=disclosure_type.value,
        )
        return record

    async def create_sms_consent(
        self,
        phone: str,
        consent_given: bool,
        method: str,
        language_shown: str,
        token: UUID | None = None,
        *,
        customer_id: UUID | None = None,
        lead_id: UUID | None = None,
        consent_type: str = "marketing",
        ip_address: str | None = None,
        user_agent: str | None = None,
        consent_timestamp_override: datetime | None = None,
    ) -> SmsConsentRecord:
        """Create an immutable SMS consent record.

        Validates: Requirements 29.1, 29.2, 29.3, 29.4
        """
        self.log_started(
            "create_sms_consent",
            phone=phone,
            consent_given=consent_given,
        )

        record = SmsConsentRecord(
            customer_id=customer_id,
            lead_id=lead_id,
            phone_number=phone,
            consent_type=consent_type,
            consent_given=consent_given,
            consent_timestamp=_resolve_consent_timestamp(consent_timestamp_override),
            consent_method=method,
            consent_language_shown=language_shown,
            consent_token=token,
            consent_ip_address=ip_address,
            consent_user_agent=user_agent,
        )
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)

        self.log_completed(
            "create_sms_consent",
            record_id=str(record.id),
            consent_given=consent_given,
        )
        return record

    async def link_orphaned_records(
        self,
        consent_token: UUID,
        customer_id: UUID,
        agreement_id: UUID,
    ) -> dict[str, Any]:
        """Link pre-checkout consent/disclosure records to post-purchase entities.

        Bridges orphaned records (customer_id IS NULL) created during
        pre-checkout consent to the Customer and ServiceAgreement created
        after Stripe payment.

        Validates: Requirements 8.7, 30.2, 30.3
        """
        self.log_started(
            "link_orphaned_records",
            consent_token=str(consent_token),
            customer_id=str(customer_id),
            agreement_id=str(agreement_id),
        )

        # Link orphaned disclosure records
        disclosure_stmt = select(DisclosureRecord).where(
            DisclosureRecord.consent_token == consent_token,
            DisclosureRecord.customer_id.is_(None),
        )
        disclosure_result = await self.session.execute(disclosure_stmt)
        disclosure_records = list(disclosure_result.scalars().all())

        for record in disclosure_records:
            record.customer_id = customer_id  # type: ignore[assignment]
            record.agreement_id = agreement_id  # type: ignore[assignment]

        # Link orphaned SMS consent records
        consent_stmt = select(SmsConsentRecord).where(
            SmsConsentRecord.consent_token == consent_token,
            SmsConsentRecord.customer_id.is_(None),
        )
        consent_result = await self.session.execute(consent_stmt)
        consent_records = list(consent_result.scalars().all())

        for record in consent_records:
            record.customer_id = customer_id  # type: ignore[assignment]

        await self.session.flush()

        linked = {
            "disclosures_linked": len(disclosure_records),
            "consents_linked": len(consent_records),
        }

        self.log_completed(
            "link_orphaned_records",
            consent_token=str(consent_token),
            **linked,
        )
        return linked

    async def get_compliance_status(
        self,
        agreement_id: UUID,
    ) -> ComplianceStatus:
        """Return which disclosures are recorded/missing for an agreement.

        Validates: Requirements 34.1, 34.2, 34.3, 35.1, 35.2, 36.1, 36.2
        """
        self.log_started(
            "get_compliance_status",
            agreement_id=str(agreement_id),
        )

        # Get agreement to determine required disclosures
        agr_stmt = (
            select(ServiceAgreement)
            .options(selectinload(ServiceAgreement.status_logs))
            .where(ServiceAgreement.id == agreement_id)
        )
        agr_result = await self.session.execute(agr_stmt)
        agreement = agr_result.scalar_one_or_none()

        # Get existing disclosures
        stmt = select(DisclosureRecord.disclosure_type).where(
            DisclosureRecord.agreement_id == agreement_id,
        )
        result = await self.session.execute(stmt)
        recorded_types = {row[0] for row in result.all()}

        # Determine required disclosures based on agreement status
        required: list[str] = [
            DisclosureType.PRE_SALE.value,
            DisclosureType.CONFIRMATION.value,
        ]

        if agreement:
            status = agreement.status
            # Check if agreement has ever been in PENDING_RENEWAL
            log_statuses = {log.new_status for log in (agreement.status_logs or [])}
            if (
                status == AgreementStatus.PENDING_RENEWAL.value
                or AgreementStatus.PENDING_RENEWAL.value in log_statuses
            ):
                required.append(DisclosureType.RENEWAL_NOTICE.value)

            if status == AgreementStatus.CANCELLED.value:
                required.append(DisclosureType.CANCELLATION_CONF.value)

        recorded = [t for t in required if t in recorded_types]
        missing = [t for t in required if t not in recorded_types]

        self.log_completed(
            "get_compliance_status",
            agreement_id=str(agreement_id),
            recorded_count=len(recorded),
            missing_count=len(missing),
        )
        return ComplianceStatus(
            agreement_id=agreement_id,
            recorded=recorded,
            missing=missing,
        )

    async def get_annual_notice_due(self) -> list[ServiceAgreement]:
        """Return ACTIVE agreements needing annual notice.

        Returns agreements where last_annual_notice_sent is NULL
        or year < current year.

        Validates: Requirements 37.1, 37.2, 37.3
        """
        self.log_started("get_annual_notice_due")

        current_year = datetime.now(timezone.utc).year
        stmt = (
            select(ServiceAgreement)
            .options(
                selectinload(ServiceAgreement.customer),
                selectinload(ServiceAgreement.tier),
            )
            .where(
                ServiceAgreement.status == AgreementStatus.ACTIVE.value,
                (
                    ServiceAgreement.last_annual_notice_sent.is_(None)
                    | (
                        extract("year", ServiceAgreement.last_annual_notice_sent)
                        < current_year
                    )
                ),
            )
            .order_by(ServiceAgreement.created_at.asc())
        )
        result = await self.session.execute(stmt)
        agreements = list(result.scalars().all())

        self.log_completed("get_annual_notice_due", count=len(agreements))
        return agreements

    async def get_disclosures_for_agreement(
        self,
        agreement_id: UUID,
    ) -> list[DisclosureRecord]:
        """Get all disclosure records for an agreement, sorted by sent_at DESC.

        Validates: Requirements 38.1, 38.2
        """
        self.log_started(
            "get_disclosures_for_agreement",
            agreement_id=str(agreement_id),
        )
        stmt = (
            select(DisclosureRecord)
            .where(DisclosureRecord.agreement_id == agreement_id)
            .order_by(DisclosureRecord.sent_at.desc())
        )
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())
        self.log_completed(
            "get_disclosures_for_agreement",
            count=len(records),
        )
        return records

    async def get_disclosures_for_customer(
        self,
        customer_id: UUID,
    ) -> list[DisclosureRecord]:
        """Get all disclosure records for a customer across agreements.

        Sorted by sent_at DESC.

        Validates: Requirements 38.2, 38.3
        """
        self.log_started(
            "get_disclosures_for_customer",
            customer_id=str(customer_id),
        )
        stmt = (
            select(DisclosureRecord)
            .where(DisclosureRecord.customer_id == customer_id)
            .order_by(DisclosureRecord.sent_at.desc())
        )
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())
        self.log_completed(
            "get_disclosures_for_customer",
            count=len(records),
        )
        return records

    async def validate_consent_language_version(
        self,
        version: str,
    ) -> bool:
        """Validate that a consent language version exists and is not deprecated.

        Returns True if version exists and deprecated_date is NULL.
        Logs warning if not found or deprecated, but does not raise.

        Validates: Requirements 11.4, 11.5
        """
        stmt = select(ConsentLanguageVersion).where(
            ConsentLanguageVersion.version == version,
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            self.logger.warning(
                "compliance.complianceservice.validate_consent_language_version_warning",
                version=version,
                reason="version_not_found",
            )
            return False

        if record.deprecated_date is not None:
            self.logger.warning(
                "compliance.complianceservice.validate_consent_language_version_warning",
                version=version,
                reason="version_deprecated",
                deprecated_date=str(record.deprecated_date),
            )
            return False

        return True

    async def process_pre_checkout_consent(
        self,
        *,
        sms_consent: bool,
        terms_accepted: bool,
        consent_language: str,
        disclosure_content: str,
        phone: str,
        consent_method: str = "web_form",
        ip_address: str | None = None,
        user_agent: str | None = None,
        email_marketing_consent: bool = False,
        consent_form_version: str | None = None,
    ) -> tuple[UUID, SmsConsentRecord, DisclosureRecord]:
        """Validate and process pre-checkout consent.

        Only terms_accepted is required. sms_consent=false is accepted
        (TCPA: purchase cannot be conditioned on SMS consent).
        Always creates an SmsConsentRecord with consent_given matching
        the request's sms_consent value.

        Raises ConsentValidationError if terms_accepted is false.

        Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.4, 11.4, 11.5
        """
        self.log_started(
            "process_pre_checkout_consent",
            sms_consent=sms_consent,
            terms_accepted=terms_accepted,
            email_marketing_consent=email_marketing_consent,
        )

        # Only terms_accepted is required — sms_consent is optional per TCPA
        if not terms_accepted:
            self.log_rejected(
                "process_pre_checkout_consent",
                reason="consent_validation_failed",
                missing_fields=["terms_accepted"],
            )
            raise ConsentValidationError(["terms_accepted"])

        # Validate consent language version if provided (non-blocking)
        if consent_form_version:
            _ = await self.validate_consent_language_version(consent_form_version)

        consent_token = uuid4()

        sms_record = await self.create_sms_consent(
            phone=phone,
            consent_given=sms_consent,
            method=consent_method,
            language_shown=consent_language,
            token=consent_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        # Store consent_form_version on the record if provided
        if consent_form_version:
            sms_record.consent_form_version = consent_form_version
            await self.session.flush()

        disclosure_record = await self.create_disclosure(
            disclosure_type=DisclosureType.PRE_SALE,
            agreement_id=None,
            customer_id=None,
            content=disclosure_content,
            sent_via="web_form",
            consent_token=consent_token,
        )

        self.log_completed(
            "process_pre_checkout_consent",
            consent_token=str(consent_token),
            email_marketing_consent=email_marketing_consent,
        )
        return consent_token, sms_record, disclosure_record
