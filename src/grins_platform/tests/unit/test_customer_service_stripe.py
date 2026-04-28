"""Unit tests for CustomerService Stripe linkage helpers.

Covers ``get_or_create_stripe_customer`` — the idempotent helper that
backs the Phase 1 customer-linkage hardening for the Stripe Payment
Links feature. The helper must:
  * return early when the customer already has a Stripe ID populated,
  * raise ``CustomerNotFoundError`` for unknown IDs,
  * raise ``MergeConflictError`` when Stripe is unconfigured or fails,
  * persist the new ID via ``CustomerRepository.update`` on success.

Validates: Stripe Payment Links plan §Phase 1.2.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import stripe

from grins_platform.exceptions import (
    CustomerNotFoundError,
    MergeConflictError,
)
from grins_platform.models.customer import Customer
from grins_platform.models.enums import CustomerStatus
from grins_platform.services.customer_service import CustomerService


def _make_customer_mock(
    *,
    customer_id: UUID | None = None,
    stripe_customer_id: str | None = None,
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    phone: str | None = "6125551234",
    email: str | None = "ada@example.com",
) -> MagicMock:
    customer = MagicMock(spec=Customer)
    customer.id = customer_id or uuid4()
    customer.first_name = first_name
    customer.last_name = last_name
    customer.phone = phone
    customer.email = email
    customer.status = CustomerStatus.ACTIVE.value
    customer.is_priority = False
    customer.is_red_flag = False
    customer.is_slow_payer = False
    customer.is_new_customer = True
    customer.sms_opt_in = False
    customer.email_opt_in = False
    customer.lead_source = None
    customer.internal_notes = None
    customer.stripe_customer_id = stripe_customer_id
    customer.is_deleted = False
    customer.deleted_at = None
    customer.created_at = datetime.now(tz=timezone.utc)
    customer.updated_at = datetime.now(tz=timezone.utc)
    return customer


def _build_service() -> tuple[CustomerService, AsyncMock]:
    repo = AsyncMock()
    service = CustomerService(repository=repo)
    return service, repo


def _stripe_settings_mock(*, configured: bool = True) -> MagicMock:
    settings = MagicMock()
    settings.is_configured = configured
    settings.stripe_secret_key = "sk_test_x" if configured else ""
    settings.stripe_api_version = "2025-03-31.basil"
    return settings


@pytest.mark.unit
async def test_returns_existing_stripe_customer_id_without_calling_stripe() -> None:
    customer_id = uuid4()
    customer = _make_customer_mock(
        customer_id=customer_id,
        stripe_customer_id="cus_existing123",
    )
    service, repo = _build_service()
    repo.get_by_id.return_value = customer

    with patch("grins_platform.services.customer_service.stripe") as mock_stripe:
        result = await service.get_or_create_stripe_customer(customer_id)

    assert result == "cus_existing123"
    mock_stripe.Customer.create.assert_not_called()
    repo.update.assert_not_called()


@pytest.mark.unit
async def test_creates_new_stripe_customer_and_persists_id() -> None:
    customer_id = uuid4()
    customer = _make_customer_mock(
        customer_id=customer_id,
        stripe_customer_id=None,
    )
    service, repo = _build_service()
    repo.get_by_id.return_value = customer

    fake_customer: dict[str, Any] = {"id": "cus_new456"}
    with patch(
        "grins_platform.services.customer_service.StripeSettings",
        return_value=_stripe_settings_mock(),
    ), patch(
        "grins_platform.services.customer_service.stripe",
    ) as mock_stripe:
        mock_stripe.StripeError = stripe.StripeError
        mock_stripe.Customer.create.return_value = fake_customer
        result = await service.get_or_create_stripe_customer(customer_id)

    assert result == "cus_new456"
    mock_stripe.Customer.create.assert_called_once()
    create_kwargs = mock_stripe.Customer.create.call_args.kwargs
    assert create_kwargs["name"] == "Ada Lovelace"
    assert create_kwargs["email"] == "ada@example.com"
    assert create_kwargs["phone"] == "6125551234"
    assert create_kwargs["metadata"] == {"grins_customer_id": str(customer_id)}
    repo.update.assert_awaited_once_with(
        customer_id,
        {"stripe_customer_id": "cus_new456"},
    )


@pytest.mark.unit
async def test_omits_email_and_phone_when_customer_has_neither() -> None:
    customer_id = uuid4()
    customer = _make_customer_mock(
        customer_id=customer_id,
        stripe_customer_id=None,
        email=None,
        phone=None,
    )
    service, repo = _build_service()
    repo.get_by_id.return_value = customer

    with patch(
        "grins_platform.services.customer_service.StripeSettings",
        return_value=_stripe_settings_mock(),
    ), patch(
        "grins_platform.services.customer_service.stripe",
    ) as mock_stripe:
        mock_stripe.StripeError = stripe.StripeError
        mock_stripe.Customer.create.return_value = {"id": "cus_minimal"}
        await service.get_or_create_stripe_customer(customer_id)

    kwargs = mock_stripe.Customer.create.call_args.kwargs
    assert "email" not in kwargs
    assert "phone" not in kwargs
    assert kwargs["name"] == "Ada Lovelace"


@pytest.mark.unit
async def test_raises_customer_not_found_when_id_does_not_exist() -> None:
    service, repo = _build_service()
    repo.get_by_id.return_value = None

    with pytest.raises(CustomerNotFoundError):
        await service.get_or_create_stripe_customer(uuid4())


@pytest.mark.unit
async def test_raises_merge_conflict_when_stripe_unconfigured() -> None:
    customer_id = uuid4()
    service, repo = _build_service()
    repo.get_by_id.return_value = _make_customer_mock(
        customer_id=customer_id,
        stripe_customer_id=None,
    )

    with patch(
        "grins_platform.services.customer_service.StripeSettings",
        return_value=_stripe_settings_mock(configured=False),
    ), pytest.raises(MergeConflictError):
        await service.get_or_create_stripe_customer(customer_id)


@pytest.mark.unit
async def test_raises_merge_conflict_when_stripe_create_fails() -> None:
    customer_id = uuid4()
    service, repo = _build_service()
    repo.get_by_id.return_value = _make_customer_mock(
        customer_id=customer_id,
        stripe_customer_id=None,
    )

    with patch(
        "grins_platform.services.customer_service.StripeSettings",
        return_value=_stripe_settings_mock(),
    ), patch(
        "grins_platform.services.customer_service.stripe",
    ) as mock_stripe:
        mock_stripe.StripeError = stripe.StripeError
        mock_stripe.Customer.create.side_effect = stripe.StripeError("boom")

        with pytest.raises(MergeConflictError):
            await service.get_or_create_stripe_customer(customer_id)

    repo.update.assert_not_called()


# =============================================================================
# Post-write hook (Phase 1.4): create_customer / update_customer
# =============================================================================


from unittest.mock import AsyncMock as _AsyncMock

from grins_platform.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
)


def _customer_create_payload() -> CustomerCreate:
    return CustomerCreate(
        first_name="Ada",
        last_name="Lovelace",
        phone="6125551234",
        email="ada@example.com",
    )


@pytest.mark.unit
async def test_create_customer_invokes_best_effort_stripe_link() -> None:
    service, repo = _build_service()
    repo.find_by_phone.return_value = None
    repo.create.return_value = _make_customer_mock()

    service._best_effort_link_stripe_customer = _AsyncMock()
    await service.create_customer(_customer_create_payload())
    service._best_effort_link_stripe_customer.assert_awaited_once()


@pytest.mark.unit
async def test_update_customer_invokes_best_effort_stripe_link() -> None:
    customer_id = uuid4()
    service, repo = _build_service()
    repo.get_by_id.return_value = _make_customer_mock(customer_id=customer_id)
    repo.update.return_value = _make_customer_mock(customer_id=customer_id)

    service._best_effort_link_stripe_customer = _AsyncMock()
    await service.update_customer(
        customer_id,
        CustomerUpdate(first_name="Ada Augusta"),
    )
    service._best_effort_link_stripe_customer.assert_awaited_once_with(customer_id)


@pytest.mark.unit
async def test_create_customer_succeeds_when_stripe_hook_fails() -> None:
    """Stripe outage must not block customer creation."""
    service, repo = _build_service()
    repo.find_by_phone.return_value = None
    repo.create.return_value = _make_customer_mock()

    # Force the helper to raise — wrapper should swallow and log.
    service.get_or_create_stripe_customer = _AsyncMock(  # type: ignore[method-assign]
        side_effect=MergeConflictError("stripe boom"),
    )
    response = await service.create_customer(_customer_create_payload())
    assert response is not None


@pytest.mark.unit
async def test_update_customer_succeeds_when_stripe_hook_fails() -> None:
    customer_id = uuid4()
    service, repo = _build_service()
    repo.get_by_id.return_value = _make_customer_mock(customer_id=customer_id)
    repo.update.return_value = _make_customer_mock(customer_id=customer_id)

    service.get_or_create_stripe_customer = _AsyncMock(  # type: ignore[method-assign]
        side_effect=MergeConflictError("stripe boom"),
    )
    response = await service.update_customer(
        customer_id,
        CustomerUpdate(first_name="Ada Augusta"),
    )
    assert response is not None
