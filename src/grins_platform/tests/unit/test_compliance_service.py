"""Unit tests for ComplianceService.

Tests disclosure record creation, SMS consent record creation,
orphaned record linkage, compliance status computation, annual notice
due query logic, and INSERT-ONLY enforcement.

Validates: Requirements 29.1-29.4, 33.1-33.4, 34.1-34.3, 35.1-35.3,
36.1-36.2, 37.1-37.3, 40.1
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import AgreementStatus, DisclosureType
from grins_platform.services.compliance_service import (
    ComplianceService,
    ComplianceStatus,
)

# =============================================================================
# Helpers
# =============================================================================


def _mock_session() -> AsyncMock:
    """Create a mock async session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_disclosure(
    *,
    disclosure_type: str = DisclosureType.PRE_SALE.value,
    agreement_id=None,
    customer_id=None,
    consent_token=None,
) -> MagicMock:
    record = MagicMock()
    record.id = uuid4()
    record.disclosure_type = disclosure_type
    record.agreement_id = agreement_id
    record.customer_id = customer_id
    record.consent_token = consent_token
    record.sent_at = datetime.now(tz=timezone.utc)
    return record


def _make_consent(
    *,
    consent_given: bool = True,
    customer_id=None,
    consent_token=None,
) -> MagicMock:
    record = MagicMock()
    record.id = uuid4()
    record.consent_given = consent_given
    record.customer_id = customer_id
    record.consent_token = consent_token
    return record


def _make_agreement(
    *,
    agreement_id=None,
    status: str = AgreementStatus.ACTIVE.value,
    last_annual_notice_sent=None,
) -> MagicMock:
    agr = MagicMock()
    agr.id = agreement_id or uuid4()
    agr.status = status
    agr.last_annual_notice_sent = last_annual_notice_sent
    agr.status_logs = []
    agr.created_at = datetime.now(tz=timezone.utc)
    return agr


def _make_status_log(new_status: str) -> MagicMock:
    log = MagicMock()
    log.new_status = new_status
    log.created_at = datetime.now(tz=timezone.utc)
    return log


# =============================================================================
# Tests: Disclosure Record Creation
# =============================================================================


@pytest.mark.unit
class TestCreateDisclosure:
    """Tests for ComplianceService.create_disclosure."""

    @pytest.mark.asyncio
    async def test_creates_pre_sale_disclosure(self) -> None:
        """PRE_SALE disclosure created with correct fields."""
        session = _mock_session()
        svc = ComplianceService(session)
        agreement_id = uuid4()
        customer_id = uuid4()
        content = "Pre-sale disclosure content"

        await svc.create_disclosure(
            disclosure_type=DisclosureType.PRE_SALE,
            agreement_id=agreement_id,
            customer_id=customer_id,
            content=content,
            sent_via="email",
        )

        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert added.disclosure_type == DisclosureType.PRE_SALE.value
        assert added.agreement_id == agreement_id
        assert added.customer_id == customer_id
        assert added.sent_via == "email"
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert added.content_hash == expected_hash
        assert added.content_snapshot == content

    @pytest.mark.asyncio
    async def test_creates_confirmation_disclosure(self) -> None:
        """CONFIRMATION disclosure created."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_disclosure(
            disclosure_type=DisclosureType.CONFIRMATION,
            agreement_id=uuid4(),
            customer_id=uuid4(),
            content="Confirmation content",
            sent_via="email",
        )

        added = session.add.call_args[0][0]
        assert added.disclosure_type == DisclosureType.CONFIRMATION.value

    @pytest.mark.asyncio
    async def test_creates_renewal_notice_disclosure(self) -> None:
        """RENEWAL_NOTICE disclosure created."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_disclosure(
            disclosure_type=DisclosureType.RENEWAL_NOTICE,
            agreement_id=uuid4(),
            customer_id=uuid4(),
            content="Renewal notice",
            sent_via="email",
        )

        added = session.add.call_args[0][0]
        assert added.disclosure_type == DisclosureType.RENEWAL_NOTICE.value

    @pytest.mark.asyncio
    async def test_creates_annual_notice_disclosure(self) -> None:
        """ANNUAL_NOTICE disclosure created."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_disclosure(
            disclosure_type=DisclosureType.ANNUAL_NOTICE,
            agreement_id=uuid4(),
            customer_id=uuid4(),
            content="Annual notice",
            sent_via="email",
        )

        added = session.add.call_args[0][0]
        assert added.disclosure_type == DisclosureType.ANNUAL_NOTICE.value

    @pytest.mark.asyncio
    async def test_creates_cancellation_conf_disclosure(self) -> None:
        """CANCELLATION_CONF disclosure created."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_disclosure(
            disclosure_type=DisclosureType.CANCELLATION_CONF,
            agreement_id=uuid4(),
            customer_id=uuid4(),
            content="Cancellation confirmation",
            sent_via="email",
        )

        added = session.add.call_args[0][0]
        assert added.disclosure_type == DisclosureType.CANCELLATION_CONF.value

    @pytest.mark.asyncio
    async def test_creates_material_change_disclosure(self) -> None:
        """MATERIAL_CHANGE disclosure created."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_disclosure(
            disclosure_type=DisclosureType.MATERIAL_CHANGE,
            agreement_id=uuid4(),
            customer_id=uuid4(),
            content="Material change notice",
            sent_via="email",
        )

        added = session.add.call_args[0][0]
        assert added.disclosure_type == DisclosureType.MATERIAL_CHANGE.value

    @pytest.mark.asyncio
    async def test_disclosure_with_consent_token(self) -> None:
        """Disclosure created with consent_token for pre-checkout linkage."""
        session = _mock_session()
        svc = ComplianceService(session)
        token = uuid4()

        await svc.create_disclosure(
            disclosure_type=DisclosureType.PRE_SALE,
            agreement_id=None,
            customer_id=None,
            content="Pre-checkout disclosure",
            sent_via="web",
            consent_token=token,
        )

        added = session.add.call_args[0][0]
        assert added.consent_token == token
        assert added.agreement_id is None
        assert added.customer_id is None

    @pytest.mark.asyncio
    async def test_disclosure_with_recipient_info(self) -> None:
        """Disclosure stores recipient email and phone."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_disclosure(
            disclosure_type=DisclosureType.CONFIRMATION,
            agreement_id=uuid4(),
            customer_id=uuid4(),
            content="Content",
            sent_via="email",
            recipient_email="test@example.com",
            recipient_phone="6125551234",
        )

        added = session.add.call_args[0][0]
        assert added.recipient_email == "test@example.com"
        assert added.recipient_phone == "6125551234"

    @pytest.mark.asyncio
    async def test_disclosure_content_hash_is_sha256(self) -> None:
        """Content hash is SHA-256 of content string."""
        session = _mock_session()
        svc = ComplianceService(session)
        content = "Unique disclosure content for hashing"

        await svc.create_disclosure(
            disclosure_type=DisclosureType.PRE_SALE,
            agreement_id=uuid4(),
            customer_id=uuid4(),
            content=content,
            sent_via="email",
        )

        added = session.add.call_args[0][0]
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert added.content_hash == expected
        assert len(added.content_hash) == 64  # SHA-256 hex length

    @pytest.mark.asyncio
    async def test_disclosure_delivery_confirmed_default_false(self) -> None:
        """delivery_confirmed defaults to False."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_disclosure(
            disclosure_type=DisclosureType.PRE_SALE,
            agreement_id=uuid4(),
            customer_id=uuid4(),
            content="Content",
            sent_via="email",
        )

        added = session.add.call_args[0][0]
        assert added.delivery_confirmed is False

    @pytest.mark.asyncio
    async def test_disclosure_delivery_confirmed_true(self) -> None:
        """delivery_confirmed can be set to True."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_disclosure(
            disclosure_type=DisclosureType.PRE_SALE,
            agreement_id=uuid4(),
            customer_id=uuid4(),
            content="Content",
            sent_via="email",
            delivery_confirmed=True,
        )

        added = session.add.call_args[0][0]
        assert added.delivery_confirmed is True


# =============================================================================
# Tests: SMS Consent Record Creation
# =============================================================================


@pytest.mark.unit
class TestCreateSmsConsent:
    """Tests for ComplianceService.create_sms_consent."""

    @pytest.mark.asyncio
    async def test_creates_consent_record(self) -> None:
        """SMS consent record created with correct fields."""
        session = _mock_session()
        svc = ComplianceService(session)
        token = uuid4()

        await svc.create_sms_consent(
            phone="6125551234",
            consent_given=True,
            method="web_form",
            language_shown="I agree to receive SMS...",
            token=token,
        )

        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert added.phone_number == "6125551234"
        assert added.consent_given is True
        assert added.consent_method == "web_form"
        assert added.consent_language_shown == "I agree to receive SMS..."
        assert added.consent_token == token

    @pytest.mark.asyncio
    async def test_creates_opt_out_record(self) -> None:
        """Opt-out recorded as new row with consent_given=False."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_sms_consent(
            phone="6125551234",
            consent_given=False,
            method="sms_reply",
            language_shown="STOP to opt out",
        )

        added = session.add.call_args[0][0]
        assert added.consent_given is False

    @pytest.mark.asyncio
    async def test_consent_with_customer_id(self) -> None:
        """Consent record linked to customer."""
        session = _mock_session()
        svc = ComplianceService(session)
        cust_id = uuid4()

        await svc.create_sms_consent(
            phone="6125551234",
            consent_given=True,
            method="web_form",
            language_shown="Consent text",
            customer_id=cust_id,
        )

        added = session.add.call_args[0][0]
        assert added.customer_id == cust_id

    @pytest.mark.asyncio
    async def test_consent_without_customer_id(self) -> None:
        """Pre-checkout consent has no customer_id."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_sms_consent(
            phone="6125551234",
            consent_given=True,
            method="web_form",
            language_shown="Consent text",
        )

        added = session.add.call_args[0][0]
        assert added.customer_id is None

    @pytest.mark.asyncio
    async def test_consent_with_ip_and_user_agent(self) -> None:
        """Consent stores IP address and user agent."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_sms_consent(
            phone="6125551234",
            consent_given=True,
            method="web_form",
            language_shown="Consent text",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        added = session.add.call_args[0][0]
        assert added.consent_ip_address == "192.168.1.1"
        assert added.consent_user_agent == "Mozilla/5.0"

    @pytest.mark.asyncio
    async def test_consent_default_type_marketing(self) -> None:
        """Default consent_type is 'marketing'."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_sms_consent(
            phone="6125551234",
            consent_given=True,
            method="web_form",
            language_shown="Consent text",
        )

        added = session.add.call_args[0][0]
        assert added.consent_type == "marketing"

    @pytest.mark.asyncio
    async def test_consent_custom_type(self) -> None:
        """Custom consent_type can be specified."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_sms_consent(
            phone="6125551234",
            consent_given=True,
            method="web_form",
            language_shown="Consent text",
            consent_type="transactional",
        )

        added = session.add.call_args[0][0]
        assert added.consent_type == "transactional"


# =============================================================================
# Tests: Orphaned Record Linkage
# =============================================================================


@pytest.mark.unit
class TestLinkOrphanedRecords:
    """Tests for ComplianceService.link_orphaned_records."""

    @pytest.mark.asyncio
    async def test_links_orphaned_disclosures(self) -> None:
        """Orphaned disclosure records linked to customer and agreement."""
        session = _mock_session()
        svc = ComplianceService(session)
        token = uuid4()
        customer_id = uuid4()
        agreement_id = uuid4()

        orphan = _make_disclosure(consent_token=token)
        orphan.customer_id = None
        orphan.agreement_id = None

        # First execute returns disclosures, second returns consents
        disc_result = MagicMock()
        disc_result.scalars.return_value.all.return_value = [orphan]
        consent_result = MagicMock()
        consent_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(side_effect=[disc_result, consent_result])

        result = await svc.link_orphaned_records(token, customer_id, agreement_id)

        assert result["disclosures_linked"] == 1
        assert result["consents_linked"] == 0
        assert orphan.customer_id == customer_id
        assert orphan.agreement_id == agreement_id

    @pytest.mark.asyncio
    async def test_links_orphaned_consents(self) -> None:
        """Orphaned SMS consent records linked to customer."""
        session = _mock_session()
        svc = ComplianceService(session)
        token = uuid4()
        customer_id = uuid4()
        agreement_id = uuid4()

        orphan = _make_consent(consent_token=token)
        orphan.customer_id = None

        disc_result = MagicMock()
        disc_result.scalars.return_value.all.return_value = []
        consent_result = MagicMock()
        consent_result.scalars.return_value.all.return_value = [orphan]
        session.execute = AsyncMock(side_effect=[disc_result, consent_result])

        result = await svc.link_orphaned_records(token, customer_id, agreement_id)

        assert result["disclosures_linked"] == 0
        assert result["consents_linked"] == 1
        assert orphan.customer_id == customer_id

    @pytest.mark.asyncio
    async def test_links_both_disclosures_and_consents(self) -> None:
        """Both orphaned disclosures and consents linked."""
        session = _mock_session()
        svc = ComplianceService(session)
        token = uuid4()
        customer_id = uuid4()
        agreement_id = uuid4()

        disc = _make_disclosure(consent_token=token)
        disc.customer_id = None
        disc.agreement_id = None
        consent = _make_consent(consent_token=token)
        consent.customer_id = None

        disc_result = MagicMock()
        disc_result.scalars.return_value.all.return_value = [disc]
        consent_result = MagicMock()
        consent_result.scalars.return_value.all.return_value = [consent]
        session.execute = AsyncMock(side_effect=[disc_result, consent_result])

        result = await svc.link_orphaned_records(token, customer_id, agreement_id)

        assert result["disclosures_linked"] == 1
        assert result["consents_linked"] == 1

    @pytest.mark.asyncio
    async def test_no_orphaned_records(self) -> None:
        """No orphaned records returns zero counts."""
        session = _mock_session()
        svc = ComplianceService(session)

        disc_result = MagicMock()
        disc_result.scalars.return_value.all.return_value = []
        consent_result = MagicMock()
        consent_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(side_effect=[disc_result, consent_result])

        result = await svc.link_orphaned_records(uuid4(), uuid4(), uuid4())

        assert result["disclosures_linked"] == 0
        assert result["consents_linked"] == 0


# =============================================================================
# Tests: Compliance Status Computation
# =============================================================================


@pytest.mark.unit
class TestGetComplianceStatus:
    """Tests for ComplianceService.get_compliance_status."""

    @pytest.mark.asyncio
    async def test_active_agreement_all_present(self) -> None:
        """ACTIVE agreement with PRE_SALE + CONFIRMATION = nothing missing."""
        session = _mock_session()
        svc = ComplianceService(session)
        agr_id = uuid4()

        agreement = _make_agreement(agreement_id=agr_id)

        agr_result = MagicMock()
        agr_result.scalar_one_or_none.return_value = agreement
        disc_result = MagicMock()
        disc_result.all.return_value = [
            (DisclosureType.PRE_SALE.value,),
            (DisclosureType.CONFIRMATION.value,),
        ]
        session.execute = AsyncMock(side_effect=[agr_result, disc_result])

        status = await svc.get_compliance_status(agr_id)

        assert isinstance(status, ComplianceStatus)
        assert status.agreement_id == agr_id
        assert DisclosureType.PRE_SALE.value in status.recorded
        assert DisclosureType.CONFIRMATION.value in status.recorded
        assert len(status.missing) == 0

    @pytest.mark.asyncio
    async def test_active_agreement_missing_confirmation(self) -> None:
        """ACTIVE agreement missing CONFIRMATION disclosure."""
        session = _mock_session()
        svc = ComplianceService(session)
        agr_id = uuid4()

        agreement = _make_agreement(agreement_id=agr_id)

        agr_result = MagicMock()
        agr_result.scalar_one_or_none.return_value = agreement
        disc_result = MagicMock()
        disc_result.all.return_value = [(DisclosureType.PRE_SALE.value,)]
        session.execute = AsyncMock(side_effect=[agr_result, disc_result])

        status = await svc.get_compliance_status(agr_id)

        assert DisclosureType.CONFIRMATION.value in status.missing

    @pytest.mark.asyncio
    async def test_pending_renewal_requires_renewal_notice(self) -> None:
        """PENDING_RENEWAL agreement requires RENEWAL_NOTICE disclosure."""
        session = _mock_session()
        svc = ComplianceService(session)
        agr_id = uuid4()

        agreement = _make_agreement(
            agreement_id=agr_id,
            status=AgreementStatus.PENDING_RENEWAL.value,
        )

        agr_result = MagicMock()
        agr_result.scalar_one_or_none.return_value = agreement
        disc_result = MagicMock()
        disc_result.all.return_value = [
            (DisclosureType.PRE_SALE.value,),
            (DisclosureType.CONFIRMATION.value,),
        ]
        session.execute = AsyncMock(side_effect=[agr_result, disc_result])

        status = await svc.get_compliance_status(agr_id)

        assert DisclosureType.RENEWAL_NOTICE.value in status.missing

    @pytest.mark.asyncio
    async def test_cancelled_requires_cancellation_conf(self) -> None:
        """CANCELLED agreement requires CANCELLATION_CONF disclosure."""
        session = _mock_session()
        svc = ComplianceService(session)
        agr_id = uuid4()

        agreement = _make_agreement(
            agreement_id=agr_id,
            status=AgreementStatus.CANCELLED.value,
        )

        agr_result = MagicMock()
        agr_result.scalar_one_or_none.return_value = agreement
        disc_result = MagicMock()
        disc_result.all.return_value = [
            (DisclosureType.PRE_SALE.value,),
            (DisclosureType.CONFIRMATION.value,),
        ]
        session.execute = AsyncMock(side_effect=[agr_result, disc_result])

        status = await svc.get_compliance_status(agr_id)

        assert DisclosureType.CANCELLATION_CONF.value in status.missing

    @pytest.mark.asyncio
    async def test_past_pending_renewal_in_logs(self) -> None:
        """Agreement that was previously PENDING_RENEWAL requires RENEWAL_NOTICE."""
        session = _mock_session()
        svc = ComplianceService(session)
        agr_id = uuid4()

        agreement = _make_agreement(
            agreement_id=agr_id,
            status=AgreementStatus.ACTIVE.value,
        )
        agreement.status_logs = [
            _make_status_log(AgreementStatus.PENDING_RENEWAL.value),
        ]

        agr_result = MagicMock()
        agr_result.scalar_one_or_none.return_value = agreement
        disc_result = MagicMock()
        disc_result.all.return_value = [
            (DisclosureType.PRE_SALE.value,),
            (DisclosureType.CONFIRMATION.value,),
        ]
        session.execute = AsyncMock(side_effect=[agr_result, disc_result])

        status = await svc.get_compliance_status(agr_id)

        assert DisclosureType.RENEWAL_NOTICE.value in status.missing

    @pytest.mark.asyncio
    async def test_no_agreement_found(self) -> None:
        """Non-existent agreement returns base required disclosures as missing."""
        session = _mock_session()
        svc = ComplianceService(session)
        agr_id = uuid4()

        agr_result = MagicMock()
        agr_result.scalar_one_or_none.return_value = None
        disc_result = MagicMock()
        disc_result.all.return_value = []
        session.execute = AsyncMock(side_effect=[agr_result, disc_result])

        status = await svc.get_compliance_status(agr_id)

        assert DisclosureType.PRE_SALE.value in status.missing
        assert DisclosureType.CONFIRMATION.value in status.missing


# =============================================================================
# Tests: Annual Notice Due
# =============================================================================


@pytest.mark.unit
class TestGetAnnualNoticeDue:
    """Tests for ComplianceService.get_annual_notice_due."""

    @pytest.mark.asyncio
    async def test_returns_agreements_needing_notice(self) -> None:
        """Returns ACTIVE agreements with no annual notice sent."""
        session = _mock_session()
        svc = ComplianceService(session)

        agr = _make_agreement(last_annual_notice_sent=None)
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [agr]
        session.execute = AsyncMock(return_value=result_mock)

        result = await svc.get_annual_notice_due()

        assert len(result) == 1
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_sent(self) -> None:
        """Returns empty list when all notices are current."""
        session = _mock_session()
        svc = ComplianceService(session)

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        result = await svc.get_annual_notice_due()

        assert len(result) == 0


# =============================================================================
# Tests: INSERT-ONLY Enforcement
# =============================================================================


@pytest.mark.unit
class TestInsertOnlyEnforcement:
    """Tests that ComplianceService only creates, never updates/deletes records.

    Validates: Requirements 29.2, 33.2
    """

    def test_service_has_no_update_disclosure_method(self) -> None:
        """ComplianceService has no method to update disclosure records."""
        assert not hasattr(ComplianceService, "update_disclosure")

    def test_service_has_no_delete_disclosure_method(self) -> None:
        """ComplianceService has no method to delete disclosure records."""
        assert not hasattr(ComplianceService, "delete_disclosure")

    def test_service_has_no_update_consent_method(self) -> None:
        """ComplianceService has no method to update consent records."""
        assert not hasattr(ComplianceService, "update_sms_consent")

    def test_service_has_no_delete_consent_method(self) -> None:
        """ComplianceService has no method to delete consent records."""
        assert not hasattr(ComplianceService, "delete_sms_consent")

    @pytest.mark.asyncio
    async def test_opt_out_creates_new_record(self) -> None:
        """Opt-out is a new INSERT with consent_given=False, not an UPDATE."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.create_sms_consent(
            phone="6125551234",
            consent_given=False,
            method="sms_reply",
            language_shown="STOP to opt out",
        )

        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert added.consent_given is False


# =============================================================================
# Tests: Disclosure Retrieval
# =============================================================================


@pytest.mark.unit
class TestDisclosureRetrieval:
    """Tests for disclosure retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_disclosures_for_agreement(self) -> None:
        """Returns disclosures for a specific agreement."""
        session = _mock_session()
        svc = ComplianceService(session)
        agr_id = uuid4()

        records = [_make_disclosure(), _make_disclosure()]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = records
        session.execute = AsyncMock(return_value=result_mock)

        result = await svc.get_disclosures_for_agreement(agr_id)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_disclosures_for_customer(self) -> None:
        """Returns disclosures for a customer across agreements."""
        session = _mock_session()
        svc = ComplianceService(session)
        cust_id = uuid4()

        records = [_make_disclosure(), _make_disclosure(), _make_disclosure()]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = records
        session.execute = AsyncMock(return_value=result_mock)

        result = await svc.get_disclosures_for_customer(cust_id)

        assert len(result) == 3
