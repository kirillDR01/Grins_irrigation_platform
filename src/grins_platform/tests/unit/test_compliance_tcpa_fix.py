"""Unit tests for Compliance_Service TCPA fix.

Tests the fixed pre-checkout consent flow where only terms_accepted
is required, and consent language version validation.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 11.4, 11.5
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.exceptions import ConsentValidationError
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.services.compliance_service import ComplianceService


def _mock_session() -> AsyncMock:
    """Create a mock async session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.mark.unit
class TestPreCheckoutConsentTcpaFix:
    """Tests for the TCPA-compliant pre-checkout consent flow."""

    @pytest.mark.asyncio
    async def test_sms_false_terms_true_accepted(self) -> None:
        """sms_consent=false, terms_accepted=true → accepted (key TCPA fix)."""
        session = _mock_session()
        svc = ComplianceService(session)

        result = await svc.process_pre_checkout_consent(
            sms_consent=False,
            terms_accepted=True,
            consent_language="test consent",
            disclosure_content="test disclosure",
            phone="6125551234",
        )

        assert len(result) == 3
        token, _sms_record, _disclosure_record = result
        assert token is not None

    @pytest.mark.asyncio
    async def test_sms_false_terms_false_rejected_422(self) -> None:
        """sms_consent=false, terms_accepted=false → rejected."""
        session = _mock_session()
        svc = ComplianceService(session)

        with pytest.raises(ConsentValidationError) as exc_info:
            await svc.process_pre_checkout_consent(
                sms_consent=False,
                terms_accepted=False,
                consent_language="test",
                disclosure_content="test",
                phone="6125551234",
            )

        assert exc_info.value.missing_fields == ["terms_accepted"]

    @pytest.mark.asyncio
    async def test_sms_true_terms_true_accepted_consent_true(self) -> None:
        """sms_consent=true, terms_accepted=true → accepted, consent_given=true."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.process_pre_checkout_consent(
            sms_consent=True,
            terms_accepted=True,
            consent_language="test",
            disclosure_content="test",
            phone="6125551234",
        )

        added_objects = [call[0][0] for call in session.add.call_args_list]
        sms_records = [
            obj for obj in added_objects if isinstance(obj, SmsConsentRecord)
        ]
        assert len(sms_records) == 1
        assert sms_records[0].consent_given is True

    @pytest.mark.asyncio
    async def test_sms_false_creates_consent_record_false(self) -> None:
        """sms_consent=false creates SmsConsentRecord with consent_given=false."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.process_pre_checkout_consent(
            sms_consent=False,
            terms_accepted=True,
            consent_language="test",
            disclosure_content="test",
            phone="6125551234",
        )

        added_objects = [call[0][0] for call in session.add.call_args_list]
        sms_records = [
            obj for obj in added_objects if isinstance(obj, SmsConsentRecord)
        ]
        assert len(sms_records) == 1
        assert sms_records[0].consent_given is False

    @pytest.mark.asyncio
    async def test_sms_true_terms_false_rejected(self) -> None:
        """sms_consent=true, terms_accepted=false → rejected."""
        session = _mock_session()
        svc = ComplianceService(session)

        with pytest.raises(ConsentValidationError) as exc_info:
            await svc.process_pre_checkout_consent(
                sms_consent=True,
                terms_accepted=False,
                consent_language="test",
                disclosure_content="test",
                phone="6125551234",
            )

        assert exc_info.value.missing_fields == ["terms_accepted"]

    @pytest.mark.asyncio
    async def test_email_marketing_consent_parameter_accepted(self) -> None:
        """email_marketing_consent parameter is accepted without error."""
        session = _mock_session()
        svc = ComplianceService(session)

        result = await svc.process_pre_checkout_consent(
            sms_consent=True,
            terms_accepted=True,
            consent_language="test",
            disclosure_content="test",
            phone="6125551234",
            email_marketing_consent=True,
        )

        assert len(result) == 3


@pytest.mark.unit
class TestConsentLanguageVersionValidation:
    """Tests for consent language version validation."""

    @pytest.mark.asyncio
    async def test_valid_version_returns_true(self) -> None:
        """Valid, non-deprecated version returns True."""
        session = _mock_session()
        svc = ComplianceService(session)

        mock_record = MagicMock()
        mock_record.deprecated_date = None
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_record
        session.execute = AsyncMock(return_value=result_mock)

        assert await svc.validate_consent_language_version("v1.0") is True

    @pytest.mark.asyncio
    async def test_deprecated_version_returns_false(self) -> None:
        """Deprecated version returns False and logs warning."""
        session = _mock_session()
        svc = ComplianceService(session)

        mock_record = MagicMock()
        mock_record.deprecated_date = date(2025, 1, 1)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = mock_record
        session.execute = AsyncMock(return_value=result_mock)

        assert await svc.validate_consent_language_version("v0.9") is False

    @pytest.mark.asyncio
    async def test_unknown_version_returns_false(self) -> None:
        """Unknown version returns False and logs warning."""
        session = _mock_session()
        svc = ComplianceService(session)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        assert await svc.validate_consent_language_version("v99.0") is False

    @pytest.mark.asyncio
    async def test_version_validation_does_not_block_consent(self) -> None:
        """Unknown version does not block SmsConsentRecord creation."""
        session = _mock_session()
        svc = ComplianceService(session)

        # First call: version query returns None (not found)
        # Subsequent calls: default mock behavior
        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=version_result)

        result = await svc.process_pre_checkout_consent(
            sms_consent=True,
            terms_accepted=True,
            consent_language="test",
            disclosure_content="test",
            phone="6125551234",
            consent_form_version="v99.0",
        )

        # Should succeed despite unknown version
        assert len(result) == 3
