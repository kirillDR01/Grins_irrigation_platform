"""Property-based regression test for Bug A — phone normalization idempotence.

Bug A was originally reported as a "phone truncation" suspicion but was
retracted after live verification: posting `+19527373399` to
`POST /api/v1/leads` on dev stored `phone='9527373399'` (correct: leading-1
stripped). All four input formats (`+19...`, `19...`, `952-737-...`,
`(952) 737...`) deduped to the same canonical value. Source review of every
`lead.phone` write site confirmed the canonical `normalize_phone` is correct.

This PBT locks in that idempotence so the report's "suspected" claim cannot
silently regress: for *every* valid US 10-digit number expressed in any of
the seven common input formats, `LeadSubmission.validate_phone` must produce
the same 10-digit canonical output.

Validates: e2e-signoff Bug A retraction
"""

from __future__ import annotations

import pytest
from hypothesis import (
    given,
    strategies as st,
)

from grins_platform.schemas.lead import LeadSubmission

pytestmark = pytest.mark.unit

# NANP: area-code first digit 2-9, exchange first digit 2-9.
_ten_digits_us = st.from_regex(r"\A[2-9]\d{2}[2-9]\d{6}\Z", fullmatch=True)


@given(d=_ten_digits_us)
def test_phone_normalization_idempotent_across_formats(d: str) -> None:
    """Every common US phone format normalizes to the same 10-digit canonical."""
    formats = [
        d,
        f"1{d}",
        f"+1{d}",
        f"+1 ({d[:3]}) {d[3:6]}-{d[6:]}",
        f"({d[:3]}) {d[3:6]}-{d[6:]}",
        f"{d[:3]}.{d[3:6]}.{d[6:]}",
        f"{d[:3]}-{d[3:6]}-{d[6:]}",
    ]
    for raw in formats:
        sub = LeadSubmission(
            name="Test Lead",
            phone=raw,
            zip_code="55416",
            email="kirillrakitinsecond@gmail.com",
            situation="new_system",  # type: ignore[arg-type]
            address="123 Test Ave",
            property_type="residential",
            sms_consent=False,
            terms_accepted=True,
            email_marketing_consent=False,
            consent_language_version="v1",
        )
        assert sub.phone == d, f"input {raw!r} produced {sub.phone!r}, expected {d!r}"
