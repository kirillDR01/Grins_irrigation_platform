"""Unit tests for customer tag API endpoints.

Tests GET /api/v1/customers/{customer_id}/tags
      PUT /api/v1/customers/{customer_id}/tags

Validates: Requirements 12.4, 12.5, 12.6, 12.7
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from grins_platform.api.v1.customers import router
from grins_platform.api.v1.dependencies import (
    get_customer_merge_service,
    get_customer_service,
    get_db_session,
    get_duplicate_detection_service,
    get_photo_service,
)
from grins_platform.models.customer_tag import CustomerTag
from grins_platform.schemas.customer_tag import (
    CustomerTagResponse,
    TagSource,
    TagTone,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tag_response(
    label: str = "VIP",
    tone: TagTone = TagTone.neutral,
    source: TagSource = TagSource.manual,
    customer_id: uuid.UUID | None = None,
) -> CustomerTagResponse:
    return CustomerTagResponse(
        id=uuid.uuid4(),
        customer_id=customer_id or uuid.uuid4(),
        label=label,
        tone=tone,
        source=source,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def app(mock_db: AsyncMock) -> FastAPI:
    from grins_platform.api.v1.auth_dependencies import (
        get_current_active_user,
        get_current_user,
    )

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/customers")

    fake_user = MagicMock()
    fake_user.id = uuid.uuid4()
    fake_user.role = "admin"

    test_app.dependency_overrides[get_current_user] = lambda: fake_user
    test_app.dependency_overrides[get_current_active_user] = lambda: fake_user
    test_app.dependency_overrides[get_customer_service] = lambda: AsyncMock()
    test_app.dependency_overrides[get_customer_merge_service] = lambda: AsyncMock()
    test_app.dependency_overrides[get_duplicate_detection_service] = lambda: AsyncMock()
    test_app.dependency_overrides[get_photo_service] = lambda: MagicMock()

    async def _db_override() -> AsyncMock:
        return mock_db

    test_app.dependency_overrides[get_db_session] = _db_override
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /{customer_id}/tags
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetCustomerTags:
    def test_returns_tags_for_existing_customer(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        """GET returns list of tags when customer exists."""
        from sqlalchemy.engine import Result

        cid = uuid.uuid4()
        customer_mock = MagicMock()
        customer_mock.id = cid
        result_mock = MagicMock(spec=Result)
        result_mock.scalar_one_or_none.return_value = customer_mock

        tag_result_mock = MagicMock(spec=Result)
        tag_result_mock.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [result_mock, tag_result_mock]

        resp = client.get(f"/api/v1/customers/{cid}/tags")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_returns_404_when_customer_not_found(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        """GET returns 404 when customer does not exist."""
        from sqlalchemy.engine import Result

        cid = uuid.uuid4()
        result_mock = MagicMock(spec=Result)
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        resp = client.get(f"/api/v1/customers/{cid}/tags")
        assert resp.status_code == 404

    def test_returns_empty_list_when_no_tags(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        """GET returns empty list when customer has no tags."""
        from sqlalchemy.engine import Result

        cid = uuid.uuid4()
        customer_mock = MagicMock()
        customer_mock.id = cid
        result_mock = MagicMock(spec=Result)
        result_mock.scalar_one_or_none.return_value = customer_mock

        tag_result_mock = MagicMock(spec=Result)
        tag_result_mock.scalars.return_value.all.return_value = []
        mock_db.execute.side_effect = [result_mock, tag_result_mock]

        resp = client.get(f"/api/v1/customers/{cid}/tags")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# PUT /{customer_id}/tags
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateCustomerTags:
    def test_returns_404_when_customer_not_found(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        """PUT returns 404 when customer does not exist."""
        from sqlalchemy.engine import Result

        cid = uuid.uuid4()
        result_mock = MagicMock(spec=Result)
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        resp = client.put(
            f"/api/v1/customers/{cid}/tags",
            json={"tags": [{"label": "VIP", "tone": "neutral"}]},
        )
        assert resp.status_code == 404

    def test_returns_422_for_duplicate_labels(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        """PUT returns 422 when request contains duplicate labels."""
        from sqlalchemy.engine import Result

        cid = uuid.uuid4()
        customer_mock = MagicMock()
        customer_mock.id = cid
        result_mock = MagicMock(spec=Result)
        result_mock.scalar_one_or_none.return_value = customer_mock
        mock_db.execute.return_value = result_mock

        resp = client.put(
            f"/api/v1/customers/{cid}/tags",
            json={"tags": [{"label": "VIP"}, {"label": "VIP"}]},
        )
        assert resp.status_code == 422

    def test_returns_422_for_label_too_long(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        """PUT returns 422 when a label exceeds 32 characters."""
        cid = uuid.uuid4()
        resp = client.put(
            f"/api/v1/customers/{cid}/tags",
            json={"tags": [{"label": "A" * 33}]},
        )
        assert resp.status_code == 422

    def test_returns_422_for_empty_label(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        """PUT returns 422 when a label is empty."""
        cid = uuid.uuid4()
        resp = client.put(
            f"/api/v1/customers/{cid}/tags",
            json={"tags": [{"label": ""}]},
        )
        assert resp.status_code == 422

    def test_returns_422_for_invalid_tone(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        """PUT returns 422 when tone is not a valid value."""
        cid = uuid.uuid4()
        resp = client.put(
            f"/api/v1/customers/{cid}/tags",
            json={"tags": [{"label": "VIP", "tone": "rainbow"}]},
        )
        assert resp.status_code == 422

    def test_accepts_empty_tags_list(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        """PUT with empty tags list clears all manual tags."""
        from sqlalchemy.engine import Result

        cid = uuid.uuid4()
        customer_mock = MagicMock()
        customer_mock.id = cid
        result_mock = MagicMock(spec=Result)
        result_mock.scalar_one_or_none.return_value = customer_mock

        tag_result_mock = MagicMock(spec=Result)
        tag_result_mock.scalars.return_value.all.return_value = []
        mock_db.execute.side_effect = [result_mock, tag_result_mock]

        resp = client.put(
            f"/api/v1/customers/{cid}/tags",
            json={"tags": []},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tags" in data
        assert data["tags"] == []

    def test_returns_200_with_saved_tags(
        self, client: TestClient, mock_db: AsyncMock
    ) -> None:
        """PUT returns 200 with the saved tag list."""
        from sqlalchemy.engine import Result

        cid = uuid.uuid4()
        customer_mock = MagicMock()
        customer_mock.id = cid
        result_mock = MagicMock(spec=Result)
        result_mock.scalar_one_or_none.return_value = customer_mock

        tag_result_mock = MagicMock(spec=Result)
        tag_result_mock.scalars.return_value.all.return_value = []

        new_tag = CustomerTag(
            customer_id=cid, label="VIP", tone="neutral", source="manual"
        )
        new_tag.id = uuid.uuid4()
        new_tag.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        mock_db.execute.side_effect = [result_mock, tag_result_mock]
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch(
            "grins_platform.repositories.customer_tag_repository"
            ".CustomerTagRepository.create",
            new_callable=AsyncMock,
            return_value=new_tag,
        ):
            resp = client.put(
                f"/api/v1/customers/{cid}/tags",
                json={"tags": [{"label": "VIP", "tone": "neutral"}]},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "tags" in data
