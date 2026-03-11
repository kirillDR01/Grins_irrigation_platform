"""Property-based tests for Compliance_Service TCPA fix.

Properties 1, 2, 18 from the integration gaps spec.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 11.4, 11.5
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

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


# =============================================================================
# Property 1: Pre-checkout consent only requires terms_accepted
# Validates: Requirements 1.1, 1.2
# =============================================================================


@pytest.mark.unit
class TestProperty1PreCheckoutOnlyRequiresTerms:
    """Pre-checkout consent rejected iff terms_accepted=false."""

    @given(sms_consent=st.booleans(), terms_accepted=st.booleans())
    @settings(max_examples=200)
    @pytest.mark.asyncio
    async def test_rejected_iff_terms_false(
        self,
        sms_consent: bool,
        terms_accepted: bool,
    ) -> None:
        """Consent rejected iff terms_accepted is false, regardless of sms_consent."""
        session = _mock_session()
        svc = ComplianceService(session)

        if not terms_accepted:
            with pytest.raises(ConsentValidationError) as exc_info:
                await svc.process_pre_checkout_consent(
                    sms_consent=sms_consent,
                    terms_accepted=terms_accepted,
                    consent_language="test",
                    disclosure_content="test",
                    phone="6125551234",
                )
            assert "terms_accepted" in exc_info.value.missing_fields
        else:
            result = await svc.process_pre_checkout_consent(
                sms_consent=sms_consent,
                terms_accepted=terms_accepted,
                consent_language="test",
                disclosure_content="test",
                phone="6125551234",
            )
            assert len(result) == 3  # (token, sms_record, disclosure_record)


# =============================================================================
# Property 2: SmsConsentRecord mirrors sms_consent value
# Validates: Requirements 1.3, 1.4
# =============================================================================


@pytest.mark.unit
class TestProperty2SmsConsentRecordMirrors:
    """For accepted requests, SmsConsentRecord.consent_given == sms_consent."""

    @given(sms_consent=st.booleans())
    @settings(max_examples=200)
    @pytest.mark.asyncio
    async def test_consent_given_mirrors_sms_consent(
        self,
        sms_consent: bool,
    ) -> None:
        """SmsConsentRecord.consent_given matches the request's sms_consent."""
        session = _mock_session()
        svc = ComplianceService(session)

        await svc.process_pre_checkout_consent(
            sms_consent=sms_consent,
            terms_accepted=True,
            consent_language="test",
            disclosure_content="test",
            phone="6125551234",
        )

        # Find the SmsConsentRecord that was added
        added_objects = [call[0][0] for call in session.add.call_args_list]
        sms_records = [
            obj for obj in added_objects if isinstance(obj, SmsConsentRecord)
        ]
        assert len(sms_records) == 1
        assert sms_records[0].consent_given is sms_consent


# =============================================================================
# Property 18: Consent version validation is non-blocking
# Validates: Requirements 11.4, 11.5
# =============================================================================


@pytest.mark.unit
class TestProperty18ConsentVersionNonBlocking:
    """Unknown/deprecated versions log warning but don't block record creation."""

    @given(version=st.text(min_size=1, max_size=20))
    @settings(max_examples=200)
    @pytest.mark.asyncio
    async def test_unknown_version_does_not_block(
        self,
        version: str,
    ) -> None:
        """Unknown consent version logs warning but consent still created."""
        session = _mock_session()
        svc = ComplianceService(session)

        # Mock the version query to return None (not found)
        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=version_result)

        # Should succeed despite unknown version
        result = await svc.process_pre_checkout_consent(
            sms_consent=True,
            terms_accepted=True,
            consent_language="test",
            disclosure_content="test",
            phone="6125551234",
            consent_form_version=version,
        )
        assert len(result) == 3
