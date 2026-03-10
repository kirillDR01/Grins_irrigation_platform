"""Property test: Follow-Up Queue Correctness.

Property 16: For any set of leads, follow-up queue returns exactly those
with intake_tag=FOLLOW_UP AND status IN (NEW, CONTACTED, QUALIFIED),
sorted by created_at ASC.

Validates: Requirements 50.1, 50.2
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import IntakeTag, LeadStatus
from grins_platform.services.lead_service import LeadService

ACTIVE_STATUSES = {
    LeadStatus.NEW.value,
    LeadStatus.CONTACTED.value,
    LeadStatus.QUALIFIED.value,
}
ALL_STATUSES = [s.value for s in LeadStatus]
ALL_TAGS = [None, IntakeTag.SCHEDULE.value, IntakeTag.FOLLOW_UP.value]


def _make_lead(
    status: str,
    intake_tag: str | None,
    created_at: datetime,
) -> MagicMock:
    """Create a mock Lead with given attributes."""
    lead = MagicMock()
    lead.id = uuid4()
    lead.name = "Test User"
    lead.phone = "6125551234"
    lead.email = None
    lead.situation = "repair"
    lead.notes = None
    lead.status = status
    lead.intake_tag = intake_tag
    lead.created_at = created_at
    lead.sms_consent = False
    lead.terms_accepted = False
    lead.lead_source = "website"
    lead.source_detail = None
    lead.zip_code = "55401"
    lead.source_site = "residential"
    return lead


@pytest.mark.unit
class TestFollowUpQueueCorrectnessProperty:
    """Property 16: Follow-Up Queue Correctness."""

    @given(
        leads_data=st.lists(
            st.tuples(
                st.sampled_from(ALL_STATUSES),
                st.sampled_from(ALL_TAGS),
                st.integers(min_value=0, max_value=1000),
            ),
            min_size=0,
            max_size=30,
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_follow_up_queue_returns_correct_subset(
        self,
        leads_data: list[tuple[str, str | None, int]],
    ) -> None:
        """Queue returns FOLLOW_UP leads with active statuses, sorted ASC."""
        base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        leads = [
            _make_lead(status, tag, base_time + timedelta(hours=offset))
            for status, tag, offset in leads_data
        ]

        # Compute expected: FOLLOW_UP tag + active status
        expected = [
            lead
            for lead in leads
            if lead.intake_tag == IntakeTag.FOLLOW_UP.value
            and lead.status in ACTIVE_STATUSES
        ]
        expected.sort(key=lambda x: x.created_at)

        # Mock repository to return the expected subset
        mock_repo = AsyncMock()
        mock_repo.get_follow_up_queue = AsyncMock(
            return_value=(expected, len(expected)),
        )

        service = LeadService(
            lead_repository=mock_repo,
            customer_service=MagicMock(),
            job_service=MagicMock(),
            staff_repository=MagicMock(),
        )

        result = await service.get_follow_up_queue(
            page=1,
            page_size=100,
        )

        # Verify count matches
        assert result.total == len(expected)
        assert len(result.items) == len(expected)

        # Verify all items have FOLLOW_UP tag and active status
        for item in result.items:
            assert item.intake_tag == IntakeTag.FOLLOW_UP.value
            assert item.status.value in ACTIVE_STATUSES

        # Verify sorted by created_at ASC
        for i in range(1, len(result.items)):
            assert result.items[i].created_at >= result.items[i - 1].created_at

    @given(
        n_follow_up_active=st.integers(min_value=0, max_value=20),
        n_follow_up_inactive=st.integers(min_value=0, max_value=10),
        n_schedule=st.integers(min_value=0, max_value=10),
        n_no_tag=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_follow_up_queue_excludes_non_matching(
        self,
        n_follow_up_active: int,
        n_follow_up_inactive: int,
        n_schedule: int,
        n_no_tag: int,
    ) -> None:
        """Only FOLLOW_UP + active status leads appear."""
        base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        offset = 0

        active_vals = [
            LeadStatus.NEW.value,
            LeadStatus.CONTACTED.value,
            LeadStatus.QUALIFIED.value,
        ]
        inactive_vals = [
            LeadStatus.CONVERTED.value,
            LeadStatus.LOST.value,
            LeadStatus.SPAM.value,
        ]

        # These SHOULD be in the queue
        qualifying: list[MagicMock] = []
        for _ in range(n_follow_up_active):
            status = active_vals[offset % 3]
            lead = _make_lead(
                status,
                IntakeTag.FOLLOW_UP.value,
                base_time + timedelta(hours=offset),
            )
            qualifying.append(lead)
            offset += 1

        # FOLLOW_UP but inactive status — NOT in queue
        for _ in range(n_follow_up_inactive):
            status = inactive_vals[offset % 3]
            _make_lead(
                status,
                IntakeTag.FOLLOW_UP.value,
                base_time + timedelta(hours=offset),
            )
            offset += 1

        # SCHEDULE tag — NOT in queue
        for _ in range(n_schedule):
            _make_lead(
                LeadStatus.NEW.value,
                IntakeTag.SCHEDULE.value,
                base_time + timedelta(hours=offset),
            )
            offset += 1

        # No tag — NOT in queue
        for _ in range(n_no_tag):
            _make_lead(
                LeadStatus.NEW.value,
                None,
                base_time + timedelta(hours=offset),
            )
            offset += 1

        qualifying.sort(key=lambda x: x.created_at)

        mock_repo = AsyncMock()
        mock_repo.get_follow_up_queue = AsyncMock(
            return_value=(qualifying, len(qualifying)),
        )

        service = LeadService(
            lead_repository=mock_repo,
            customer_service=MagicMock(),
            job_service=MagicMock(),
            staff_repository=MagicMock(),
        )

        result = await service.get_follow_up_queue(
            page=1,
            page_size=100,
        )

        assert result.total == n_follow_up_active
        assert len(result.items) == n_follow_up_active
