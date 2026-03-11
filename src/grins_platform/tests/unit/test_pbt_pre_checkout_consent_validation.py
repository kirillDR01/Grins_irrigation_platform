"""Property test for pre-checkout consent validation.

Property 15: Pre-Checkout Consent Validation (TCPA-compliant)
Only terms_accepted=false triggers ConsentValidationError.
sms_consent=false is accepted per TCPA (purchase not conditioned on SMS consent).
When terms_accepted=true → sms_consent_record + PRE_SALE disclosure_record
created with same consent_token, consent_given matching sms_consent value.

Validates: Requirements 1.1, 1.2, 1.3, 1.4, 30.2, 30.3
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.exceptions import ConsentValidationError
from grins_platform.models.disclosure_record import DisclosureRecord
from grins_platform.models.enums import DisclosureType
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.services.compliance_service import ComplianceService

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

phones = st.from_regex(r"\d{10}", fullmatch=True)
consent_languages = st.text(min_size=10, max_size=100)
disclosure_contents = st.text(min_size=10, max_size=200)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session() -> AsyncMock:
    """Mock session that tracks add() calls."""
    session = AsyncMock()
    session.added: list[object] = []  # type: ignore[attr-defined]

    def _add(obj: object) -> None:
        session.added.append(obj)  # type: ignore[attr-defined]
        if hasattr(obj, "id") and getattr(obj, "id", None) is None:
            obj.id = uuid4()  # type: ignore[union-attr]

    session.add = MagicMock(side_effect=_add)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestPreCheckoutConsentValidationProperty:
    """Property 15: Pre-Checkout Consent Validation (TCPA-compliant)."""

    @given(
        phone=phones,
        language=consent_languages,
        content=disclosure_contents,
    )
    @settings(max_examples=30)
    async def test_both_false_raises_no_records(
        self,
        phone: str,
        language: str,
        content: str,
    ) -> None:
        """sms_consent=false AND terms_accepted=false → error (terms), no records."""
        session = _mock_session()
        svc = ComplianceService(session)

        with pytest.raises(ConsentValidationError) as exc_info:
            await svc.process_pre_checkout_consent(
                sms_consent=False,
                terms_accepted=False,
                consent_language=language,
                disclosure_content=content,
                phone=phone,
            )

        # Only terms_accepted triggers rejection per TCPA fix
        assert "terms_accepted" in exc_info.value.missing_fields
        assert "sms_consent" not in exc_info.value.missing_fields
        assert len(session.added) == 0  # type: ignore[attr-defined]

    @given(
        phone=phones,
        language=consent_languages,
        content=disclosure_contents,
    )
    @settings(max_examples=30)
    async def test_sms_false_terms_true_creates_records(
        self,
        phone: str,
        language: str,
        content: str,
    ) -> None:
        """sms_consent=false, terms_accepted=true → accepted, consent_given=false."""
        session = _mock_session()
        svc = ComplianceService(session)

        _token, sms_rec, _disc_rec = await svc.process_pre_checkout_consent(
            sms_consent=False,
            terms_accepted=True,
            consent_language=language,
            disclosure_content=content,
            phone=phone,
        )

        assert len(session.added) == 2  # type: ignore[attr-defined]
        assert isinstance(sms_rec, SmsConsentRecord)
        assert sms_rec.consent_given is False
        assert sms_rec.phone_number == phone

    @given(
        phone=phones,
        language=consent_languages,
        content=disclosure_contents,
    )
    @settings(max_examples=30)
    async def test_sms_true_terms_false_raises_no_records(
        self,
        phone: str,
        language: str,
        content: str,
    ) -> None:
        """sms_consent=true, terms_accepted=false → error, no records."""
        session = _mock_session()
        svc = ComplianceService(session)

        with pytest.raises(ConsentValidationError) as exc_info:
            await svc.process_pre_checkout_consent(
                sms_consent=True,
                terms_accepted=False,
                consent_language=language,
                disclosure_content=content,
                phone=phone,
            )

        assert "terms_accepted" in exc_info.value.missing_fields
        assert "sms_consent" not in exc_info.value.missing_fields
        assert len(session.added) == 0  # type: ignore[attr-defined]

    @given(
        sms_consent=st.booleans(),
        terms_accepted=st.booleans(),
        phone=phones,
        language=consent_languages,
        content=disclosure_contents,
    )
    @settings(max_examples=50)
    async def test_terms_false_rejects_with_no_records(
        self,
        sms_consent: bool,
        terms_accepted: bool,
        phone: str,
        language: str,
        content: str,
    ) -> None:
        """Only terms_accepted=false triggers rejection, regardless of sms_consent."""
        session = _mock_session()
        svc = ComplianceService(session)

        if not terms_accepted:
            with pytest.raises(ConsentValidationError):
                await svc.process_pre_checkout_consent(
                    sms_consent=sms_consent,
                    terms_accepted=terms_accepted,
                    consent_language=language,
                    disclosure_content=content,
                    phone=phone,
                )
            assert len(session.added) == 0  # type: ignore[attr-defined]
        else:
            # terms_accepted=true always succeeds regardless of sms_consent
            _token, sms_rec, _disc_rec = await svc.process_pre_checkout_consent(
                sms_consent=sms_consent,
                terms_accepted=terms_accepted,
                consent_language=language,
                disclosure_content=content,
                phone=phone,
            )
            assert len(session.added) == 2  # type: ignore[attr-defined]
            assert sms_rec.consent_given is sms_consent

    @given(
        phone=phones,
        language=consent_languages,
        content=disclosure_contents,
    )
    @settings(max_examples=30)
    async def test_both_true_creates_records_with_shared_token(
        self,
        phone: str,
        language: str,
        content: str,
    ) -> None:
        """sms_consent=true AND terms_accepted=true → two records, same token."""
        session = _mock_session()
        svc = ComplianceService(session)

        token, sms_rec, disc_rec = await svc.process_pre_checkout_consent(
            sms_consent=True,
            terms_accepted=True,
            consent_language=language,
            disclosure_content=content,
            phone=phone,
        )

        assert len(session.added) == 2  # type: ignore[attr-defined]

        # Verify SMS consent record
        assert isinstance(sms_rec, SmsConsentRecord)
        assert sms_rec.consent_given is True
        assert sms_rec.phone_number == phone
        assert sms_rec.consent_token == token

        # Verify PRE_SALE disclosure record
        assert isinstance(disc_rec, DisclosureRecord)
        assert disc_rec.disclosure_type == DisclosureType.PRE_SALE.value
        assert disc_rec.consent_token == token
        assert disc_rec.customer_id is None
        assert disc_rec.agreement_id is None

    @given(
        phone=phones,
        language=consent_languages,
        content=disclosure_contents,
    )
    @settings(max_examples=20)
    async def test_valid_consent_token_is_uuid(
        self,
        phone: str,
        language: str,
        content: str,
    ) -> None:
        """Returned consent_token is a valid UUID shared by both records."""
        session = _mock_session()
        svc = ComplianceService(session)

        token, sms_rec, disc_rec = await svc.process_pre_checkout_consent(
            sms_consent=True,
            terms_accepted=True,
            consent_language=language,
            disclosure_content=content,
            phone=phone,
        )

        # Token is a UUID
        assert isinstance(token, UUID)
        # Both records share the same token
        assert sms_rec.consent_token == disc_rec.consent_token == token
