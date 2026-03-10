"""Property test for agreement number format and sequentiality.

Property 3: Agreement Number Format and Sequentiality
For any generated agreement number, matches `^AGR-\\d{4}-\\d{3}$` with current
year; sequential portion strictly increasing within same year.

Validates: Requirements 2.3
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.agreement_service import AgreementService

seq_numbers = st.integers(min_value=1, max_value=999)

AGREEMENT_NUMBER_PATTERN = re.compile(r"^AGR-\d{4}-\d{3}$")


def _make_service(seq_values: list[int]) -> AgreementService:
    repo = AsyncMock()
    repo.get_next_agreement_number_seq = AsyncMock(side_effect=seq_values)
    return AgreementService(
        agreement_repo=repo,
        tier_repo=AsyncMock(),
        stripe_settings=MagicMock(is_configured=False),
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestAgreementNumberFormatProperty:
    """Property-based tests for agreement number format."""

    @given(seq=seq_numbers)
    @settings(max_examples=50)
    async def test_format_matches_pattern(self, seq: int) -> None:
        """Every generated number matches AGR-YYYY-NNN."""
        svc = _make_service([seq])
        result = await svc.generate_agreement_number()
        assert AGREEMENT_NUMBER_PATTERN.match(result), (
            f"'{result}' doesn't match pattern"
        )

    @given(seq=seq_numbers)
    @settings(max_examples=50)
    async def test_contains_current_year(self, seq: int) -> None:
        """Year portion equals the current UTC year."""
        svc = _make_service([seq])
        result = await svc.generate_agreement_number()
        year = datetime.now(tz=timezone.utc).year
        assert result.startswith(f"AGR-{year}-")

    @given(
        seq_a=st.integers(min_value=1, max_value=998),
        seq_b=st.integers(min_value=1, max_value=998),
    )
    @settings(max_examples=50)
    async def test_sequential_portion_strictly_increasing(
        self,
        seq_a: int,
        seq_b: int,
    ) -> None:
        """When repo returns increasing seqs, numeric suffix is strictly increasing."""
        lo, hi = sorted([seq_a, seq_b])
        if lo == hi:
            hi += 1
        svc = _make_service([lo, hi])
        r1 = await svc.generate_agreement_number()
        r2 = await svc.generate_agreement_number()
        num1 = int(r1.split("-")[-1])
        num2 = int(r2.split("-")[-1])
        assert num2 > num1
