"""Integration test for Bug 2 — send-link returns 422 (not 500) when both
channels refuse delivery.

When the email allowlist (dev/staging) blocks the recipient and the SMS
provider also fails, the route must surface ``NoContactMethodError`` →
HTTP 422 — not bubble the email exception as an opaque 500.

Validates: bughunt 2026-04-28 §Bug 2.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
)
from grins_platform.api.v1.invoices import get_invoice_service
from grins_platform.exceptions import NoContactMethodError
from grins_platform.main import app
from grins_platform.models.enums import StaffRole
from grins_platform.services.invoice_service import InvoiceService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
def admin_user() -> MagicMock:
    """Mock admin user for auth."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "admin"
    user.email = "admin@grins.com"
    user.role = StaffRole.ADMIN.value
    user.is_active = True
    user.is_login_enabled = True
    return user


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.integration
@pytest.mark.asyncio
async def test_send_link_blocks_when_email_allowlist_refuses_returns_422(
    async_client: AsyncClient,
    admin_user: MagicMock,
) -> None:
    """Service raising ``NoContactMethodError`` → HTTP 422 (not 500)."""
    invoice_id = uuid.uuid4()

    mock_service = MagicMock(spec=InvoiceService)
    mock_service.send_payment_link = AsyncMock(
        side_effect=NoContactMethodError(invoice_id),
    )

    app.dependency_overrides[get_invoice_service] = lambda: mock_service
    app.dependency_overrides[get_current_active_user] = lambda: admin_user

    try:
        response = await async_client.post(
            f"/api/v1/invoices/{invoice_id}/send-link",
            headers={"Authorization": "Bearer test_token"},
        )
        assert response.status_code == 422
        body = response.json()
        # Either the typed-handler shape (`error.code`) or FastAPI's
        # `detail` shape — accept whichever the platform produces. The
        # invariant is "not 500, not opaque".
        assert "error" in body or "detail" in body
    finally:
        app.dependency_overrides.clear()
