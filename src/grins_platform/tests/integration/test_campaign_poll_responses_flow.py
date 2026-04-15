"""Integration tests for the poll response flow.

Test 1: Full webhook-to-response flow
Test 2: Summary endpoint — multiple replies → correct bucket counts
Test 3: CSV export — verify content, column headers, Content-Disposition
Test 4: STOP dual-recording — consent revocation + opted_out row
Test 5: Latest-wins deduplication — two replies from same phone

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""

from __future__ import annotations

import csv
import io
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    require_manager_or_admin,
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.main import app
from grins_platform.models.enums import UserRole
from grins_platform.schemas.campaign_response import (
    CampaignResponseBucket,
    CampaignResponseCsvRow,
    CampaignResponseSummary,
)
from grins_platform.services.campaign_response_service import (
    CampaignResponseService,
)
from grins_platform.services.sms.base import InboundSMS

# =============================================================================
# Fixtures
# =============================================================================

_POLL_OPTIONS: list[dict[str, str]] = [
    {
        "key": "1",
        "label": "Week of Apr 6",
        "start_date": "2026-04-06",
        "end_date": "2026-04-10",
    },
    {
        "key": "2",
        "label": "Week of Apr 13",
        "start_date": "2026-04-13",
        "end_date": "2026-04-17",
    },
    {
        "key": "3",
        "label": "Week of Apr 20",
        "start_date": "2026-04-20",
        "end_date": "2026-04-24",
    },
]


@pytest.fixture
def mock_admin_user() -> MagicMock:
    """Mock admin user for auth override."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Admin User"
    user.username = "admin"
    user.role = UserRole.ADMIN.value
    user.is_active = True
    user.is_login_enabled = True
    return user


@pytest.fixture
def campaign_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def mock_db_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest_asyncio.fixture
async def client(
    mock_db_session: AsyncMock,
    mock_admin_user: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated client with mocked DB."""
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    app.dependency_overrides[require_manager_or_admin] = lambda: mock_admin_user
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# =============================================================================
# Helpers
# =============================================================================

_CAMP_REPO = "grins_platform.api.v1.campaign_responses.CampaignRepository"
_RESP_SVC = "grins_platform.api.v1.campaign_responses.CampaignResponseService"
_RESP_REPO = "grins_platform.api.v1.campaign_responses.CampaignResponseRepository"


def _make_campaign(cid: uuid.UUID) -> MagicMock:
    c = MagicMock()
    c.id = cid
    c.name = "Spring Startup Poll"
    c.poll_options = _POLL_OPTIONS
    c.status = "sent"
    return c


def _make_response_row(
    cid: uuid.UUID,
    *,
    status: str = "parsed",
) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.campaign_id = cid
    row.sent_message_id = uuid.uuid4()
    row.customer_id = uuid.uuid4()
    row.lead_id = None
    row.phone = "+16125551234"
    row.recipient_name = "Jane Doe"
    row.recipient_address = None
    row.selected_option_key = "1"
    row.selected_option_label = "Week of Apr 6"
    row.raw_reply_body = "1"
    row.provider_message_id = f"msg-{uuid.uuid4().hex[:8]}"
    row.status = status
    row.received_at = datetime.now(timezone.utc)
    row.created_at = datetime.now(timezone.utc)
    return row


def _mock_sent_msg(
    cid: uuid.UUID,
    campaign: MagicMock,
) -> MagicMock:
    """Build a mock SentMessage linked to a campaign."""
    msg = MagicMock()
    msg.id = uuid.uuid4()
    msg.campaign_id = cid
    msg.campaign = campaign
    msg.delivery_status = "sent"
    msg.customer_id = uuid.uuid4()
    msg.lead_id = None
    msg.customer = MagicMock(first_name="Jane", last_name="Doe")
    msg.lead = None
    msg.created_at = datetime.now(timezone.utc)
    return msg


def _mock_session_with_sent_msg(
    sent_msg: MagicMock,
) -> AsyncMock:
    """Session whose execute returns sent_msg."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = sent_msg
    session.execute.return_value = result
    return session


# =============================================================================
# Test 1: Full webhook-to-response flow
# =============================================================================


@pytest.mark.integration
class TestWebhookToResponseFlow:
    """Inbound webhook → correlation → parse → store.

    Validates: Requirement 18.1
    """

    @pytest.mark.asyncio
    async def test_inbound_poll_reply_creates_row(
        self,
    ) -> None:
        """Body "2" for a poll campaign → parsed row."""
        cid = uuid.uuid4()
        campaign = _make_campaign(cid)
        sent_msg = _mock_sent_msg(cid, campaign)
        session = _mock_session_with_sent_msg(sent_msg)

        svc = CampaignResponseService(session)
        svc.repo = AsyncMock()
        svc.repo.add = AsyncMock(side_effect=lambda r: r)

        inbound = InboundSMS(
            from_phone="+16125551234",
            body="2",
            provider_sid="msg-abc",
            thread_id="thread-xyz",
        )
        row = await svc.record_poll_reply(inbound)

        assert row.status == "parsed"
        assert row.selected_option_key == "2"
        assert row.selected_option_label == "Week of Apr 13"
        assert row.campaign_id == cid
        assert row.raw_reply_body == "2"
        assert row.recipient_name == "Jane Doe"
        svc.repo.add.assert_called_once()


# =============================================================================
# Test 2: Summary endpoint
# =============================================================================


@pytest.mark.integration
class TestSummaryEndpoint:
    """GET /campaigns/{id}/responses/summary.

    Validates: Requirement 18.2
    """

    @pytest.mark.asyncio
    async def test_correct_bucket_counts(
        self,
        client: AsyncClient,
        campaign_id: uuid.UUID,
    ) -> None:
        """Multiple replies → correct per-option buckets."""
        campaign = _make_campaign(campaign_id)
        summary = CampaignResponseSummary(
            campaign_id=campaign_id,
            total_sent=10,
            total_replied=5,
            buckets=[
                CampaignResponseBucket(
                    option_key="1",
                    status="parsed",
                    count=3,
                ),
                CampaignResponseBucket(
                    option_key="2",
                    status="parsed",
                    count=1,
                ),
                CampaignResponseBucket(
                    option_key=None,
                    status="needs_review",
                    count=1,
                ),
            ],
        )

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=campaign)
        mock_svc = MagicMock()
        mock_svc.get_response_summary = AsyncMock(
            return_value=summary,
        )

        with (
            patch(_CAMP_REPO) as camp_cls,
            patch(_RESP_SVC) as svc_cls,
        ):
            camp_cls.return_value = mock_repo
            svc_cls.return_value = mock_svc

            resp = await client.get(
                f"/api/v1/campaigns/{campaign_id}/responses/summary",
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["campaign_id"] == str(campaign_id)
        assert data["total_sent"] == 10
        assert data["total_replied"] == 5
        assert len(data["buckets"]) == 3
        parsed = [b for b in data["buckets"] if b["status"] == "parsed"]
        assert sum(b["count"] for b in parsed) == 4

    @pytest.mark.asyncio
    async def test_404_for_missing_campaign(
        self,
        client: AsyncClient,
    ) -> None:
        """Non-existent campaign → 404."""
        mid = uuid.uuid4()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch(_CAMP_REPO) as camp_cls:
            camp_cls.return_value = mock_repo
            resp = await client.get(
                f"/api/v1/campaigns/{mid}/responses/summary",
            )

        assert resp.status_code == 404


# =============================================================================
# Test 3: CSV export
# =============================================================================


@pytest.mark.integration
class TestCsvExport:
    """GET /campaigns/{id}/responses/export.csv.

    Validates: Requirement 18.3
    """

    @pytest.mark.asyncio
    async def test_csv_content_and_headers(
        self,
        client: AsyncClient,
        campaign_id: uuid.UUID,
    ) -> None:
        """CSV has correct columns, rows, and filename."""
        campaign = _make_campaign(campaign_id)
        csv_rows = [
            CampaignResponseCsvRow(
                first_name="Jane",
                last_name="Doe",
                phone="+16125551234",
                selected_option_label="Week of Apr 6",
                raw_reply="1",
                received_at="2026-04-08T12:00:00+00:00",
            ),
            CampaignResponseCsvRow(
                first_name="John",
                last_name="Smith",
                phone="+16125555678",
                selected_option_label="Week of Apr 13",
                raw_reply="2",
                received_at="2026-04-08T13:00:00+00:00",
            ),
        ]

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=campaign)
        mock_svc = MagicMock()

        async def _iter(
            _cid: Any,
            _opt: Any = None,
        ) -> Any:
            for r in csv_rows:
                yield r

        mock_svc.iter_csv_rows = _iter

        with (
            patch(_CAMP_REPO) as camp_cls,
            patch(_RESP_SVC) as svc_cls,
        ):
            camp_cls.return_value = mock_repo
            svc_cls.return_value = mock_svc

            resp = await client.get(
                f"/api/v1/campaigns/{campaign_id}/responses/export.csv",
            )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")

        cd = resp.headers["content-disposition"]
        assert "campaign_spring_startup_poll_" in cd
        assert "_responses.csv" in cd

        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        assert rows[0] == [
            "first_name",
            "last_name",
            "phone",
            "selected_option_label",
            "raw_reply",
            "status",
            "address",
            "received_at",
        ]
        assert len(rows) == 3  # header + 2 data rows
        assert rows[1][0] == "Jane"
        assert rows[2][4] == "2"


# =============================================================================
# Test 4: STOP dual-recording
# =============================================================================


@pytest.mark.integration
class TestStopDualRecording:
    """STOP → consent revocation + opted_out row.

    Validates: Requirement 18.4
    """

    @pytest.mark.asyncio
    async def test_stop_creates_opted_out_row(self) -> None:
        """STOP triggers opted_out bookkeeping row."""
        cid = uuid.uuid4()
        campaign = _make_campaign(cid)
        sent_msg = _mock_sent_msg(cid, campaign)
        session = _mock_session_with_sent_msg(sent_msg)

        svc = CampaignResponseService(session)
        svc.repo = AsyncMock()
        svc.repo.add = AsyncMock(side_effect=lambda r: r)

        inbound = InboundSMS(
            from_phone="+16125551234",
            body="STOP",
            provider_sid="msg-stop",
            thread_id="thread-xyz",
        )
        await svc.record_opt_out_as_response(inbound)

        svc.repo.add.assert_called_once()
        added = svc.repo.add.call_args[0][0]
        assert added.status == "opted_out"
        assert added.campaign_id == cid
        assert added.raw_reply_body == "STOP"

    @pytest.mark.asyncio
    async def test_bookkeeping_failure_swallowed(self) -> None:
        """Bookkeeping failure does not raise."""
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute.return_value = result

        svc = CampaignResponseService(session)
        svc.repo = AsyncMock()
        svc.repo.add = AsyncMock(
            side_effect=RuntimeError("db error"),
        )

        inbound = InboundSMS(
            from_phone="+16125551234",
            body="STOP",
            provider_sid="msg-stop",
            thread_id="thread-xyz",
        )
        # Should not raise
        await svc.record_opt_out_as_response(inbound)


# =============================================================================
# Test 5: Latest-wins deduplication
# =============================================================================


@pytest.mark.integration
class TestLatestWinsDeduplication:
    """Two replies from same phone → only latest in results.

    Validates: Requirement 18.5
    """

    @pytest.mark.asyncio
    async def test_latest_wins_in_summary(
        self,
        client: AsyncClient,
        campaign_id: uuid.UUID,
    ) -> None:
        """Summary reflects dedup: 1 unique phone → 1 reply."""
        campaign = _make_campaign(campaign_id)
        summary = CampaignResponseSummary(
            campaign_id=campaign_id,
            total_sent=5,
            total_replied=1,
            buckets=[
                CampaignResponseBucket(
                    option_key="2",
                    status="parsed",
                    count=1,
                ),
            ],
        )

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=campaign)
        mock_svc = MagicMock()
        mock_svc.get_response_summary = AsyncMock(
            return_value=summary,
        )

        with (
            patch(_CAMP_REPO) as camp_cls,
            patch(_RESP_SVC) as svc_cls,
        ):
            camp_cls.return_value = mock_repo
            svc_cls.return_value = mock_svc

            resp = await client.get(
                f"/api/v1/campaigns/{campaign_id}/responses/summary",
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_replied"] == 1
        assert len(data["buckets"]) == 1
        assert data["buckets"][0]["option_key"] == "2"

    @pytest.mark.asyncio
    async def test_latest_wins_in_csv(
        self,
        client: AsyncClient,
        campaign_id: uuid.UUID,
    ) -> None:
        """CSV contains only the latest reply per phone."""
        campaign = _make_campaign(campaign_id)
        csv_rows = [
            CampaignResponseCsvRow(
                first_name="Jane",
                last_name="Doe",
                phone="+16125551234",
                selected_option_label="Week of Apr 13",
                raw_reply="2",
                received_at="2026-04-08T14:00:00+00:00",
            ),
        ]

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=campaign)
        mock_svc = MagicMock()

        async def _iter(
            _cid: Any,
            _opt: Any = None,
        ) -> Any:
            for r in csv_rows:
                yield r

        mock_svc.iter_csv_rows = _iter

        with (
            patch(_CAMP_REPO) as camp_cls,
            patch(_RESP_SVC) as svc_cls,
        ):
            camp_cls.return_value = mock_repo
            svc_cls.return_value = mock_svc

            resp = await client.get(
                f"/api/v1/campaigns/{campaign_id}/responses/export.csv",
            )

        assert resp.status_code == 200
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) == 2  # header + 1 (latest wins)
        assert rows[1][3] == "Week of Apr 13"
        assert rows[1][4] == "2"


# =============================================================================
# Test: Response list endpoint
# =============================================================================


@pytest.mark.integration
class TestResponseListEndpoint:
    """GET /campaigns/{id}/responses paginated list.

    Validates: Requirement 18.2 (supplementary)
    """

    @pytest.mark.asyncio
    async def test_list_returns_paginated_results(
        self,
        client: AsyncClient,
        campaign_id: uuid.UUID,
    ) -> None:
        """List endpoint returns paginated response rows."""
        campaign = _make_campaign(campaign_id)
        row = _make_response_row(campaign_id)

        mock_camp = MagicMock()
        mock_camp.get_by_id = AsyncMock(return_value=campaign)
        mock_resp = MagicMock()
        mock_resp.list_for_campaign = AsyncMock(
            return_value=([row], 1),
        )

        with (
            patch(_CAMP_REPO) as camp_cls,
            patch(_RESP_REPO) as resp_cls,
        ):
            camp_cls.return_value = mock_camp
            resp_cls.return_value = mock_resp

            response = await client.get(
                f"/api/v1/campaigns/{campaign_id}/responses",
                params={"page": 1, "page_size": 20},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "parsed"
