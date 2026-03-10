"""Property test for immutable compliance and consent records.

Property 14: Immutable Compliance and Consent Records
For any existing disclosure_record or sms_consent_record, UPDATE and DELETE
operations fail; opt-outs recorded as new rows with consent_given=false.

Validates: Requirements 29.2, 33.2
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.disclosure_record import DisclosureRecord
from grins_platform.models.enums import DisclosureType
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.services.compliance_service import ComplianceService

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

phones = st.from_regex(r"\d{10}", fullmatch=True)
consent_methods = st.sampled_from(["web_form", "sms_reply", "in_person"])
consent_languages = st.text(min_size=10, max_size=100)
disclosure_types = st.sampled_from(list(DisclosureType))
sent_vias = st.sampled_from(["email", "sms", "pending"])
contents = st.text(min_size=1, max_size=200)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session_for_create() -> AsyncMock:
    """Mock session that tracks add() calls and simulates flush/refresh."""
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
# Property tests (async — Hypothesis + pytest-asyncio)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestImmutableComplianceConsentPropertyAsync:
    """Property 14 — async property tests for INSERT-ONLY behaviour."""

    @given(
        phone=phones,
        method=consent_methods,
        language=consent_languages,
    )
    @settings(max_examples=30)
    async def test_opt_out_creates_new_row_not_update(
        self,
        phone: str,
        method: str,
        language: str,
    ) -> None:
        """Opt-outs are recorded as new INSERT rows with consent_given=false."""
        session = _mock_session_for_create()
        svc = ComplianceService(session)

        await svc.create_sms_consent(
            phone=phone,
            consent_given=False,
            method=method,
            language_shown=language,
        )

        assert len(session.added) == 1  # type: ignore[attr-defined]
        added = session.added[0]  # type: ignore[attr-defined]
        assert isinstance(added, SmsConsentRecord)
        assert added.consent_given is False
        assert added.phone_number == phone

    @given(
        phone=phones,
        method=consent_methods,
        language=consent_languages,
    )
    @settings(max_examples=30)
    async def test_consent_grant_creates_new_row(
        self,
        phone: str,
        method: str,
        language: str,
    ) -> None:
        """Consent grants also create new rows (INSERT-ONLY pattern)."""
        session = _mock_session_for_create()
        svc = ComplianceService(session)

        await svc.create_sms_consent(
            phone=phone,
            consent_given=True,
            method=method,
            language_shown=language,
        )

        assert len(session.added) == 1  # type: ignore[attr-defined]
        added = session.added[0]  # type: ignore[attr-defined]
        assert isinstance(added, SmsConsentRecord)
        assert added.consent_given is True

    @given(
        dtype=disclosure_types,
        content=contents,
        sent_via=sent_vias,
    )
    @settings(max_examples=30)
    async def test_disclosure_creation_is_insert_only(
        self,
        dtype: DisclosureType,
        content: str,
        sent_via: str,
    ) -> None:
        """Every disclosure is created via INSERT, never via UPDATE."""
        session = _mock_session_for_create()
        svc = ComplianceService(session)

        await svc.create_disclosure(
            disclosure_type=dtype,
            agreement_id=uuid4(),
            customer_id=uuid4(),
            content=content,
            sent_via=sent_via,
        )

        assert len(session.added) == 1  # type: ignore[attr-defined]
        added = session.added[0]  # type: ignore[attr-defined]
        assert isinstance(added, DisclosureRecord)
        assert added.disclosure_type == dtype.value

    @given(
        phone=phones,
        method=consent_methods,
        language=consent_languages,
    )
    @settings(max_examples=20)
    async def test_sequential_opt_in_opt_out_creates_two_rows(
        self,
        phone: str,
        method: str,
        language: str,
    ) -> None:
        """Opt-in followed by opt-out produces two separate INSERT rows."""
        session = _mock_session_for_create()
        svc = ComplianceService(session)

        await svc.create_sms_consent(
            phone=phone,
            consent_given=True,
            method=method,
            language_shown=language,
        )
        await svc.create_sms_consent(
            phone=phone,
            consent_given=False,
            method=method,
            language_shown=language,
        )

        assert len(session.added) == 2  # type: ignore[attr-defined]
        assert session.added[0].consent_given is True  # type: ignore[attr-defined]
        assert session.added[1].consent_given is False  # type: ignore[attr-defined]
        # Both are distinct objects (new rows, not updates)
        assert session.added[0] is not session.added[1]  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Structural tests (sync — no Hypothesis needed)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImmutableComplianceConsentPropertySync:
    """Property 14 — structural checks for INSERT-ONLY enforcement."""

    def test_disclosure_record_has_no_update_method(self) -> None:
        """DisclosureRecord model exposes no update/save method."""
        public_methods = [
            m
            for m in dir(DisclosureRecord)
            if not m.startswith("_") and callable(getattr(DisclosureRecord, m, None))
        ]
        for method_name in public_methods:
            assert method_name not in ("update", "save", "delete", "modify")

    def test_sms_consent_record_has_no_update_method(self) -> None:
        """SmsConsentRecord model exposes no update/save method."""
        public_methods = [
            m
            for m in dir(SmsConsentRecord)
            if not m.startswith("_") and callable(getattr(SmsConsentRecord, m, None))
        ]
        for method_name in public_methods:
            assert method_name not in ("update", "save", "delete", "modify")

    def test_compliance_service_has_no_update_or_delete_methods(self) -> None:
        """ComplianceService exposes no methods to update or delete records.

        The only mutation methods are create_* (INSERT) and
        link_orphaned_records (links pre-checkout records).
        """
        public_methods = [
            m
            for m in dir(ComplianceService)
            if not m.startswith("_") and callable(getattr(ComplianceService, m, None))
        ]
        forbidden = [
            "update_disclosure",
            "delete_disclosure",
            "update_consent",
            "delete_consent",
            "update_sms_consent",
            "delete_sms_consent",
            "remove_disclosure",
            "remove_consent",
        ]
        for method_name in forbidden:
            assert method_name not in public_methods, (
                f"ComplianceService should not have "
                f"{method_name} — records are INSERT-ONLY"
            )
