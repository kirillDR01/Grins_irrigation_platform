"""Regression test for SentMessageRepository.get_by_customer_and_type.

Bug found 2026-05-02: the dedupe lookup did NOT filter out rows whose
``superseded_at`` is set, so marking a stale receipt as superseded was
ignored — the dedupe still treated it as a recent send and refused to
send a fresh one. The sibling method :meth:`list_by_appointment` does
filter superseded; this test pins down that ``get_by_customer_and_type``
matches that contract.

Approach: assert the generated SQL WHERE clause contains the
``superseded_at IS NULL`` predicate when ``include_superseded`` is False
(the default), and does NOT contain it when ``include_superseded=True``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.repositories.sent_message_repository import (
    SentMessageRepository,
)
from grins_platform.schemas.ai import MessageType


def _captured_sql(session_mock: MagicMock) -> str:
    """Return the rendered SQL of the last execute() call."""
    args, _ = session_mock.execute.call_args
    stmt = args[0]
    return str(
        stmt.compile(compile_kwargs={"literal_binds": False}),
    )


@pytest.mark.unit
class TestDedupeFiltersSuperseded:
    @pytest.mark.asyncio
    async def test_default_call_filters_superseded_is_null(self) -> None:
        session = MagicMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result)
        repo = SentMessageRepository(session=session)

        await repo.get_by_customer_and_type(
            customer_id=uuid4(),
            message_type=MessageType.PAYMENT_RECEIPT,
        )

        sql = _captured_sql(session)
        assert "superseded_at IS NULL" in sql, (
            f"Expected superseded_at IS NULL filter in default dedupe query; "
            f"got: {sql}"
        )

    @pytest.mark.asyncio
    async def test_include_superseded_true_drops_filter(self) -> None:
        session = MagicMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result)
        repo = SentMessageRepository(session=session)

        await repo.get_by_customer_and_type(
            customer_id=uuid4(),
            message_type=MessageType.PAYMENT_RECEIPT,
            include_superseded=True,
        )

        sql = _captured_sql(session)
        assert "superseded_at IS NULL" not in sql, (
            f"Expected NO superseded_at filter when include_superseded=True; "
            f"got: {sql}"
        )

    @pytest.mark.asyncio
    async def test_appointment_scoped_call_still_filters_superseded(
        self,
    ) -> None:
        # The appointment_id branch must also pick up the superseded filter.
        session = MagicMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result)
        repo = SentMessageRepository(session=session)

        await repo.get_by_customer_and_type(
            customer_id=uuid4(),
            message_type=MessageType.APPOINTMENT_CONFIRMATION,
            appointment_id=uuid4(),
        )

        sql = _captured_sql(session)
        assert "superseded_at IS NULL" in sql
        assert "appointment_id" in sql
