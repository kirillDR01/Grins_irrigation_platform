"""Auth guard coverage — one parametrized pass over every state-mutating
and PII-reading endpoint that must require a valid bearer token.

Matches the inventory in the CR-5 fix plan: jobs, appointments, customers.
Public endpoints (leads POST, webhooks, /auth/*, /health, duplicate check
for the public form) are deliberately excluded.

Validates: CR-5 (Req 4 extension)
"""

from __future__ import annotations

import uuid
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app


def _uuid() -> str:
    return str(uuid4())


def _phone() -> str:
    return "+16125551234"


def _minimal_job_body() -> dict[str, Any]:
    return {
        "customer_id": _uuid(),
        "property_id": _uuid(),
        "job_type": "spring_startup",
    }


def _minimal_customer_body() -> dict[str, Any]:
    return {
        "first_name": "Test",
        "last_name": "User",
        "phone": _phone(),
    }


def _minimal_appointment_body() -> dict[str, Any]:
    return {
        "job_id": _uuid(),
        "staff_id": _uuid(),
        "scheduled_date": "2026-05-01",
        "time_window_start": "09:00:00",
        "time_window_end": "11:00:00",
    }


# (method, path, body) — path placeholders get filled per-call.
AUTH_REQUIRED_ENDPOINTS: list[tuple[str, str, dict[str, Any] | None]] = [
    # --- jobs ---
    ("POST", "/api/v1/jobs", _minimal_job_body()),
    ("PUT", f"/api/v1/jobs/{_uuid()}", {"notes": "updated"}),
    ("DELETE", f"/api/v1/jobs/{_uuid()}", None),
    ("PUT", f"/api/v1/jobs/{_uuid()}/status", {"status": "scheduled"}),
    ("POST", f"/api/v1/jobs/{_uuid()}/calculate-price", None),
    ("POST", f"/api/v1/jobs/{_uuid()}/complete", {}),
    ("POST", f"/api/v1/jobs/{_uuid()}/on-my-way", None),
    ("POST", f"/api/v1/jobs/{_uuid()}/started", None),
    ("POST", f"/api/v1/jobs/{_uuid()}/notes", {"note": "hello"}),
    ("POST", f"/api/v1/jobs/{_uuid()}/invoice", None),
    ("POST", f"/api/v1/jobs/{_uuid()}/review-push", None),
    # --- appointments ---
    ("POST", "/api/v1/appointments", _minimal_appointment_body()),
    (
        "PUT",
        f"/api/v1/appointments/{_uuid()}",
        {"notes": "updated"},
    ),
    ("DELETE", f"/api/v1/appointments/{_uuid()}", None),
    # --- customers: mutating ---
    ("POST", "/api/v1/customers", _minimal_customer_body()),
    (
        "POST",
        f"/api/v1/customers/{_uuid()}/merge",
        {"duplicate_id": _uuid(), "field_selections": {}},
    ),
    (
        "POST",
        f"/api/v1/customers/{_uuid()}/merge/preview",
        {"duplicate_id": _uuid(), "field_selections": {}},
    ),
    ("PUT", f"/api/v1/customers/{_uuid()}", {"first_name": "X"}),
    ("DELETE", f"/api/v1/customers/{_uuid()}", None),
    (
        "PUT",
        f"/api/v1/customers/{_uuid()}/flags",
        {"is_priority": True},
    ),
    # --- customers: PII reads ---
    ("GET", f"/api/v1/customers/{_uuid()}", None),
    ("GET", "/api/v1/customers", None),
    ("GET", "/api/v1/customers/duplicates", None),
    ("GET", f"/api/v1/customers/lookup/phone/{_phone()}", None),
    (
        "GET",
        "/api/v1/customers/lookup/email/test@example.com",
        None,
    ),
    # --- customers: documents (upload, list, download, delete) ---
    (
        "POST",
        f"/api/v1/customers/{_uuid()}/documents?document_type=estimate",
        None,
    ),
    ("GET", f"/api/v1/customers/{_uuid()}/documents", None),
    (
        "GET",
        f"/api/v1/customers/{_uuid()}/documents/{_uuid()}/download",
        None,
    ),
    ("DELETE", f"/api/v1/customers/{_uuid()}/documents/{_uuid()}", None),
]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    AUTH_REQUIRED_ENDPOINTS,
    ids=[f"{m} {p}" for m, p, _ in AUTH_REQUIRED_ENDPOINTS],
)
async def test_endpoint_requires_auth(
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    """Unauthenticated requests to these endpoints return 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        kwargs: dict[str, Any] = {}
        if body is not None:
            kwargs["json"] = body
        response = await client.request(method, path, **kwargs)

    assert response.status_code == 401, (
        f"{method} {path} returned {response.status_code} without auth — "
        f"expected 401. Body: {response.text[:200]}"
    )


# --- smoke tests for intentionally-public endpoints ---


@pytest.mark.integration
@pytest.mark.asyncio
async def test_public_lead_submit_is_not_guarded() -> None:
    """``POST /api/v1/leads`` is the public marketing form. It must NOT
    require a bearer token — external users submit leads without one.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Minimal lead body may still fail validation — we only care that
        # the failure is not 401.
        response = await client.post(
            "/api/v1/leads",
            json={"name": "Test", "phone": _phone()},
        )

    assert response.status_code != 401, (
        "POST /api/v1/leads must remain public. Got 401 → auth guard was "
        "added in error."
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_check_is_not_guarded() -> None:
    """``GET /api/v1/customers/check-duplicate`` is used by the public
    marketing form to warn about duplicate phone/email submissions. It
    must stay open (flagged as follow-up in the plan).

    This test only checks the auth layer — not the DB. If the auth
    dependency were attached, FastAPI would reject with 401 before
    reaching the handler. We detect that by checking the missing-phone
    validation path (422) or a non-401 response.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Omit ``phone`` so the handler rejects with 422 before hitting the DB —
        # this still proves the auth layer let us through.
        response = await client.get("/api/v1/customers/check-duplicate")

    assert response.status_code != 401, (
        "GET /api/v1/customers/check-duplicate must stay public for the "
        "marketing lead form. Got 401 → auth guard was added in error."
    )
