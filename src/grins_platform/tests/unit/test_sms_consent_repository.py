"""Unit tests for SmsConsentRepository.

Validates: H-11 (bughunt 2026-04-16) — batch SMS-consent pre-filter.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from grins_platform.repositories.sms_consent_repository import SmsConsentRepository


@pytest.mark.unit
class TestSmsConsentRepositoryGetOptedOutCustomerIds:
    """Tests for SmsConsentRepository.get_opted_out_customer_ids."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> SmsConsentRepository:
        """Create repository with mock session."""
        return SmsConsentRepository(mock_session)

    @staticmethod
    def _mock_scalars_result(customer_ids: list[UUID | None]) -> MagicMock:
        """Build a MagicMock that mimics ``session.execute(stmt).scalars().all()``."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = customer_ids
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    @pytest.mark.asyncio
    async def test_get_opted_out_customer_ids_returns_subset_set(
        self,
        repository: SmsConsentRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Only the customer_ids with an opt-out record are returned."""
        cust_a = uuid4()
        cust_b = uuid4()
        cust_c = uuid4()

        # DB returns rows for A and C only.
        mock_session.execute.return_value = self._mock_scalars_result(
            [cust_a, cust_c],
        )

        result = await repository.get_opted_out_customer_ids(
            customer_ids=[cust_a, cust_b, cust_c],
        )

        assert result == {cust_a, cust_c}
        assert isinstance(result, set)
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_opted_out_customer_ids_returns_empty_set_when_none_opted_out(
        self,
        repository: SmsConsentRepository,
        mock_session: AsyncMock,
    ) -> None:
        """No opt-out rows -> empty set, not None."""
        cust_a = uuid4()
        cust_b = uuid4()
        mock_session.execute.return_value = self._mock_scalars_result([])

        result = await repository.get_opted_out_customer_ids(
            customer_ids=[cust_a, cust_b],
        )

        assert result == set()
        assert isinstance(result, set)
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_opted_out_customer_ids_ignores_customers_without_consent_record(
        self,
        repository: SmsConsentRepository,
        mock_session: AsyncMock,
    ) -> None:
        """A customer not represented in the result set is NOT in the output.

        Customers with zero SmsConsentRecord rows (or only consent_given=True
        rows) must not appear in the opted-out set — that matches the existing
        ``send_lien_notice`` / CR-5 behavior where a missing record means
        "not opted out".
        """
        cust_with_consent = uuid4()
        cust_no_record = uuid4()
        cust_opted_out = uuid4()

        # Only the opted-out customer surfaces in the query result.
        mock_session.execute.return_value = self._mock_scalars_result(
            [cust_opted_out],
        )

        result = await repository.get_opted_out_customer_ids(
            customer_ids=[cust_with_consent, cust_no_record, cust_opted_out],
        )

        assert result == {cust_opted_out}
        assert cust_with_consent not in result
        assert cust_no_record not in result

    @pytest.mark.asyncio
    async def test_get_opted_out_customer_ids_empty_input_skips_query(
        self,
        repository: SmsConsentRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Empty input returns empty set without executing a query.

        Guards against a pointless ``WHERE customer_id IN ()`` round trip
        when the caller has no candidates.
        """
        result = await repository.get_opted_out_customer_ids(customer_ids=[])

        assert result == set()
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_opted_out_customer_ids_filters_none_rows(
        self,
        repository: SmsConsentRepository,
        mock_session: AsyncMock,
    ) -> None:
        """NULL customer_id rows (lead-scoped records) are filtered out.

        SmsConsentRecord.customer_id is nullable — lead-only consent rows
        would show up as ``None`` if the IN-list accidentally matched. We
        defensively drop them so callers can trust the set is all UUIDs.
        """
        cust_a = uuid4()
        mock_session.execute.return_value = self._mock_scalars_result(
            [cust_a, None],
        )

        result = await repository.get_opted_out_customer_ids(
            customer_ids=[cust_a],
        )

        assert result == {cust_a}
        assert None not in result
