"""Property-based tests for duplicate score computation.

Validates: Requirements 32.1, 32.2, 32.3, 32.4
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.duplicate_detection_service import (
    MAX_SCORE,
    DuplicateDetectionService,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_names = st.text(
    alphabet=st.characters(whitelist_categories=["L"]),
    min_size=2,
    max_size=30,
)

_phones = st.text(alphabet="0123456789", min_size=10, max_size=10).filter(
    lambda s: s[0] in "23456789",
)

_emails = st.from_regex(r"[a-z]{3,10}@[a-z]{3,8}\.(com|org|net)", fullmatch=True)

_addresses = st.text(
    alphabet=st.characters(whitelist_categories=["L", "N", "Zs"]),
    min_size=5,
    max_size=60,
).filter(lambda s: len(s.strip()) >= 5)

_zips = st.from_regex(r"[0-9]{5}", fullmatch=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_customer(
    *,
    first_name: str = "John",
    last_name: str = "Doe",
    phone: str | None = "6125551234",
    email: str | None = None,
    address: str | None = None,
    zip_code: str | None = None,
    has_property: bool = True,
) -> MagicMock:
    """Build a minimal mock Customer with optional property."""
    c = MagicMock()
    c.id = uuid4()
    c.first_name = first_name
    c.last_name = last_name
    c.phone = phone
    c.email = email

    if has_property and address:
        prop = MagicMock()
        prop.is_primary = True
        prop.address = address
        prop.zip_code = zip_code
        c.properties = [prop]
    else:
        c.properties = []

    return c


svc = DuplicateDetectionService()


# ===================================================================
# Property 1: Duplicate Score Commutativity
# score(A, B) == score(B, A)
# Validates: Req 32.1
# ===================================================================
@pytest.mark.unit
@given(
    first_a=_names,
    last_a=_names,
    phone_a=_phones,
    email_a=_emails,
    first_b=_names,
    last_b=_names,
    phone_b=_phones,
    email_b=_emails,
)
@settings(max_examples=200, deadline=None)
def test_duplicate_score_commutativity(
    first_a: str,
    last_a: str,
    phone_a: str,
    email_a: str,
    first_b: str,
    last_b: str,
    phone_b: str,
    email_b: str,
) -> None:
    a = _make_customer(
        first_name=first_a,
        last_name=last_a,
        phone=phone_a,
        email=email_a,
    )
    b = _make_customer(
        first_name=first_b,
        last_name=last_b,
        phone=phone_b,
        email=email_b,
    )

    score_ab, _ = svc.compute_score(a, b)
    score_ba, _ = svc.compute_score(b, a)

    assert score_ab == score_ba


# ===================================================================
# Property 2: Duplicate Score Self-Identity
# score(A, A) == max possible score for that record
# Validates: Req 32.2
# ===================================================================
@pytest.mark.unit
@given(
    first=_names,
    last=_names,
    phone=_phones,
    email=_emails,
    addr=_addresses,
    zip_code=_zips,
)
@settings(max_examples=100, deadline=None)
def test_duplicate_score_self_identity(
    first: str,
    last: str,
    phone: str,
    email: str,
    addr: str,
    zip_code: str,
) -> None:
    c = _make_customer(
        first_name=first,
        last_name=last,
        phone=phone,
        email=email,
        address=addr,
        zip_code=zip_code,
    )
    score, _ = svc.compute_score(c, c)
    assert score == MAX_SCORE


# ===================================================================
# Property 3: Duplicate Score Zero Floor
# No matching signals → score == 0
# Validates: Req 32.3
# ===================================================================
@pytest.mark.unit
@given(
    first_a=_names,
    last_a=_names,
    first_b=_names,
    last_b=_names,
)
@settings(max_examples=200, deadline=None)
def test_duplicate_score_zero_floor(
    first_a: str,
    last_a: str,
    first_b: str,
    last_b: str,
) -> None:
    # Unique phones, no emails, no properties → zero shared signals
    a = _make_customer(
        first_name=first_a,
        last_name=last_a,
        phone=None,
        email=None,
        has_property=False,
    )
    b = _make_customer(
        first_name=first_b,
        last_name=last_b,
        phone=None,
        email=None,
        has_property=False,
    )
    # Force different names to avoid name-similarity signal
    a.first_name = "Xylophone"
    a.last_name = "Qqqqqqq"
    b.first_name = "Zzzzzzzz"
    b.last_name = "Wwwwwww"

    score, signals = svc.compute_score(a, b)
    assert score == 0
    assert len(signals) == 0


# ===================================================================
# Property 4: Duplicate Score Bounded
# 0 <= score <= 100
# Validates: Req 32.4
# ===================================================================
@pytest.mark.unit
@given(
    first_a=_names,
    last_a=_names,
    phone_a=_phones,
    email_a=_emails,
    first_b=_names,
    last_b=_names,
    phone_b=_phones,
    email_b=_emails,
    addr_a=_addresses,
    addr_b=_addresses,
    zip_a=_zips,
    zip_b=_zips,
)
@settings(max_examples=200, deadline=None)
def test_duplicate_score_bounded(
    first_a: str,
    last_a: str,
    phone_a: str,
    email_a: str,
    first_b: str,
    last_b: str,
    phone_b: str,
    email_b: str,
    addr_a: str,
    addr_b: str,
    zip_a: str,
    zip_b: str,
) -> None:
    a = _make_customer(
        first_name=first_a,
        last_name=last_a,
        phone=phone_a,
        email=email_a,
        address=addr_a,
        zip_code=zip_a,
    )
    b = _make_customer(
        first_name=first_b,
        last_name=last_b,
        phone=phone_b,
        email=email_b,
        address=addr_b,
        zip_code=zip_b,
    )

    score, _ = svc.compute_score(a, b)
    assert 0 <= score <= MAX_SCORE
