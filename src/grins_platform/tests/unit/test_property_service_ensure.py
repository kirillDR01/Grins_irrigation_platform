"""Unit tests for ``ensure_property_for_lead`` in property_service.

Validates bughunt H-5 / H-6: move_to_jobs and move_to_sales previously
dropped the lead's ``job_address``; the helper resolves or creates a
Property so ``property_id`` can flow through to Jobs / SalesEntry.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.services.property_service import (
    _normalize_address,
    _parse_address,
    ensure_property_for_lead,
)


@pytest.mark.unit
class TestNormalizeAddress:
    def test_lowercases(self) -> None:
        assert _normalize_address("123 MAIN ST") == "123 main st"

    def test_collapses_whitespace(self) -> None:
        assert _normalize_address("123   Main\tSt") == "123 main st"

    def test_strips_trailing_punctuation(self) -> None:
        assert _normalize_address("123 Main St. ") == "123 main st"
        assert _normalize_address("123 Main St,") == "123 main st"

    def test_is_idempotent(self) -> None:
        raw = "  1234 MAIN ST.,  "
        once = _normalize_address(raw)
        twice = _normalize_address(once)
        assert once == twice == "1234 main st"


@pytest.mark.unit
class TestParseAddress:
    def test_three_part_address(self) -> None:
        street, city, state, zip_code = _parse_address(
            "1234 Main St, Minneapolis, MN 55401",
        )
        assert street == "1234 Main St"
        assert city == "Minneapolis"
        assert state == "MN"
        assert zip_code == "55401"

    def test_extended_zip(self) -> None:
        _, _, _, zip_code = _parse_address(
            "100 W Broadway, Bloomington, MN 55420-1234",
        )
        assert zip_code == "55420-1234"

    def test_two_part_defaults_city_to_unknown_when_state_zip_only(self) -> None:
        street, city, state, zip_code = _parse_address("123 Main St, MN 55401")
        assert street == "123 Main St"
        assert city == "Unknown"
        assert state == "MN"
        assert zip_code == "55401"

    def test_single_part_falls_back(self) -> None:
        street, city, state, zip_code = _parse_address("Just a freeform line")
        assert street == "Just a freeform line"
        assert city == "Unknown"
        assert state == "MN"
        assert zip_code is None


@pytest.mark.unit
class TestEnsurePropertyForLead:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_address(self) -> None:
        session = AsyncMock()
        lead = SimpleNamespace(id=uuid4(), job_address=None)
        result = await ensure_property_for_lead(session, uuid4(), lead)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_empty_address(self) -> None:
        session = AsyncMock()
        lead = SimpleNamespace(id=uuid4(), job_address="   ")
        result = await ensure_property_for_lead(session, uuid4(), lead)
        assert result is None

    @pytest.mark.asyncio
    async def test_reuses_existing_match_idempotently(self) -> None:
        customer_id = uuid4()
        prop_id = uuid4()
        existing = MagicMock()
        existing.id = prop_id
        existing.address = "1234 Main St"
        existing.customer_id = customer_id

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [existing]
        exec_result = MagicMock()
        exec_result.scalars.return_value = scalars_mock

        session = AsyncMock()
        session.execute = AsyncMock(return_value=exec_result)

        lead = SimpleNamespace(
            id=uuid4(),
            job_address="  1234 Main St., Minneapolis, MN 55401",
        )

        result = await ensure_property_for_lead(session, customer_id, lead)
        assert result is existing
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_new_property_when_no_match(self) -> None:
        customer_id = uuid4()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        exec_result = MagicMock()
        exec_result.scalars.return_value = scalars_mock

        session = AsyncMock()
        session.execute = AsyncMock(return_value=exec_result)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        lead = SimpleNamespace(
            id=uuid4(),
            job_address="999 Maple Ave, Edina, MN 55436",
        )

        result = await ensure_property_for_lead(session, customer_id, lead)

        assert result is not None
        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert added.address == "999 Maple Ave"
        assert added.city == "Edina"
        assert added.state == "MN"
        assert added.zip_code == "55436"
        assert added.customer_id == customer_id
