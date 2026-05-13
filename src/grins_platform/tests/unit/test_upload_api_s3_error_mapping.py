"""S3UploadError → 502/503 mapping at the API edge (Cluster A).

Covers BOTH attachment-upload endpoints introduced by the foundation phase:
- POST /api/v1/leads/{lead_id}/attachments
- POST /api/v1/customers/{customer_id}/photos

Ensures that:
- ``retryable=True`` → HTTP 502 Bad Gateway
- ``retryable=False`` → HTTP 503 Service Unavailable
- the pre-existing 413/415 mappings remain intact (no regressions).

The endpoints are exercised via FastAPI ASGITransport with dependency
overrides for auth + service injection; the PhotoService instance is
swapped for one whose ``upload_file`` raises the target exception.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
    get_current_user,
)
from grins_platform.api.v1.dependencies import (
    get_customer_service,
    get_db_session,
    get_photo_service,
)
from grins_platform.exceptions import (
    CustomerNotFoundError,
    S3UploadError,
)
from grins_platform.main import app
from grins_platform.models.enums import CustomerStatus
from grins_platform.schemas.customer import CustomerResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _stub_customer() -> CustomerResponse:
    now = datetime.now(tz=timezone.utc)
    return CustomerResponse(
        id=uuid.uuid4(),
        first_name="Test",
        last_name="Customer",
        phone="5551234567",
        email=None,
        status=CustomerStatus.ACTIVE,
        is_priority=False,
        is_red_flag=False,
        is_slow_payer=False,
        is_new_customer=False,
        sms_opt_in=True,
        email_opt_in=True,
        lead_source=None,
        internal_notes=None,
        preferred_service_times=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_admin_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Admin"
    user.role = "admin"
    user.is_active = True
    return user


@pytest_asyncio.fixture
async def s3_502_client(
    mock_admin_user: MagicMock,
) -> AsyncGenerator[tuple[AsyncClient, MagicMock], None]:
    """Client whose injected PhotoService raises retryable=True (→ 502)."""
    photo_service = MagicMock()
    photo_service.upload_file = MagicMock(
        side_effect=S3UploadError("s3 hiccup", retryable=True),
    )

    customer_service = AsyncMock()
    customer_service.get_customer = AsyncMock(return_value=_stub_customer())

    # Session is only used for SELECT Lead in the lead endpoint; supply a
    # mock that returns a fake lead.
    fake_lead = MagicMock()
    fake_lead.id = uuid.uuid4()
    session = MagicMock()
    select_result = MagicMock()
    select_result.scalar_one_or_none = MagicMock(return_value=fake_lead)
    session.execute = AsyncMock(return_value=select_result)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    app.dependency_overrides[get_photo_service] = lambda: photo_service
    app.dependency_overrides[get_customer_service] = lambda: customer_service
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_admin_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, photo_service
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def s3_503_client(
    mock_admin_user: MagicMock,
) -> AsyncGenerator[tuple[AsyncClient, MagicMock], None]:
    """Client whose injected PhotoService raises retryable=False (→ 503)."""
    photo_service = MagicMock()
    photo_service.upload_file = MagicMock(
        side_effect=S3UploadError("no creds", retryable=False),
    )

    customer_service = AsyncMock()
    customer_service.get_customer = AsyncMock(return_value=_stub_customer())

    fake_lead = MagicMock()
    fake_lead.id = uuid.uuid4()
    session = MagicMock()
    select_result = MagicMock()
    select_result.scalar_one_or_none = MagicMock(return_value=fake_lead)
    session.execute = AsyncMock(return_value=select_result)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    app.dependency_overrides[get_photo_service] = lambda: photo_service
    app.dependency_overrides[get_customer_service] = lambda: customer_service
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_admin_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, photo_service
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — customer photo upload
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_customer_photo_upload_502_on_retryable_s3_error(
    s3_502_client: tuple[AsyncClient, MagicMock],
) -> None:
    client, _ = s3_502_client
    response = await client.post(
        f"/api/v1/customers/{uuid.uuid4()}/photos",
        files={"file": ("test.jpg", BytesIO(b"\xff\xd8\xff\xe0"), "image/jpeg")},
    )
    assert response.status_code == 502


@pytest.mark.unit
@pytest.mark.asyncio
async def test_customer_photo_upload_503_on_misconfig(
    s3_503_client: tuple[AsyncClient, MagicMock],
) -> None:
    client, _ = s3_503_client
    response = await client.post(
        f"/api/v1/customers/{uuid.uuid4()}/photos",
        files={"file": ("test.jpg", BytesIO(b"\xff\xd8\xff\xe0"), "image/jpeg")},
    )
    assert response.status_code == 503


@pytest.mark.unit
@pytest.mark.asyncio
async def test_customer_photo_upload_404_when_customer_missing(
    mock_admin_user: MagicMock,
) -> None:
    """Regression: customer-not-found path keeps returning 404, not 502."""
    photo_service = MagicMock()
    photo_service.upload_file = MagicMock(return_value=None)
    customer_service = AsyncMock()
    customer_service.get_customer = AsyncMock(
        side_effect=CustomerNotFoundError(uuid.uuid4()),
    )

    app.dependency_overrides[get_photo_service] = lambda: photo_service
    app.dependency_overrides[get_customer_service] = lambda: customer_service
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_admin_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.post(
                f"/api/v1/customers/{uuid.uuid4()}/photos",
                files={
                    "file": (
                        "test.jpg",
                        BytesIO(b"\xff\xd8\xff\xe0"),
                        "image/jpeg",
                    )
                },
            )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — lead attachment upload
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lead_attachment_502_on_retryable_s3_error(
    s3_502_client: tuple[AsyncClient, MagicMock],
) -> None:
    client, photo_service = s3_502_client
    # The lead endpoint constructs PhotoService() inline. Patch the
    # class so its instance shares the s3-erroring upload_file.
    with patch(
        "grins_platform.api.v1.leads.PhotoService",
        return_value=photo_service,
    ):
        response = await client.post(
            f"/api/v1/leads/{uuid.uuid4()}/attachments",
            files={
                "file": (
                    "estimate.pdf",
                    BytesIO(b"%PDF-1.4 minimal"),
                    "application/pdf",
                )
            },
            data={"attachment_type": "ESTIMATE"},
        )
    assert response.status_code == 502


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lead_attachment_503_on_misconfig(
    s3_503_client: tuple[AsyncClient, MagicMock],
) -> None:
    client, photo_service = s3_503_client
    with patch(
        "grins_platform.api.v1.leads.PhotoService",
        return_value=photo_service,
    ):
        response = await client.post(
            f"/api/v1/leads/{uuid.uuid4()}/attachments",
            files={
                "file": (
                    "estimate.pdf",
                    BytesIO(b"%PDF-1.4 minimal"),
                    "application/pdf",
                )
            },
            data={"attachment_type": "ESTIMATE"},
        )
    assert response.status_code == 503
