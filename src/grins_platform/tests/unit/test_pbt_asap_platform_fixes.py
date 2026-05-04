"""Property-based tests for ASAP Platform Fixes spec.

Covers Properties 4-13 (backend only; Properties 1-3 are frontend).

- Properties 4, 5: Token generation and validation (auth_service)
- Properties 6, 7, 8, 9, 10: Lead operations (lead_service)
- Properties 11, 12: Manual lead creation (lead_service)
- Property 13: Job type update (job_service)
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

_T = TypeVar("_T")


def _run_async(coro: Awaitable[_T]) -> _T:
    """Run an async coroutine in a fresh event loop.

    Avoids `asyncio.get_event_loop()` which is deprecated and may return
    a closed loop when pytest-asyncio has already run earlier in the
    session, breaking these sync Hypothesis tests in full-suite runs.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


from grins_platform.exceptions import (
    LeadAlreadyConvertedError,
    LeadNotFoundError,
)
from grins_platform.exceptions.auth import (
    InvalidTokenError,
    TokenExpiredError,
)
from grins_platform.models.enums import (
    LeadSituation,
    LeadStatus,
    UserRole,
)
from grins_platform.schemas.lead import ManualLeadCreate
from grins_platform.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    REFRESH_TOKEN_EXPIRE_DAYS,
    AuthService,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

roles = st.sampled_from([UserRole.ADMIN, UserRole.TECH, UserRole.MANAGER])
phone_digits = st.text(
    alphabet="0123456789",
    min_size=10,
    max_size=10,
).filter(lambda s: s[0] in "23456789")

non_empty_name = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
    min_size=1,
    max_size=60,
).filter(lambda s: len(s.strip()) > 0)

non_empty_description = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs", "P")),
    min_size=1,
    max_size=200,
).filter(lambda s: len(s.strip()) > 0)

lead_situations = st.sampled_from(list(LeadSituation))

# Valid job types from the design doc
valid_job_types = st.sampled_from(
    [
        "spring_startup",
        "summer_tuneup",
        "winterization",
        "repair",
        "diagnostic",
        "installation",
        "landscaping",
    ]
)

non_converted_statuses = st.sampled_from(
    [
        LeadStatus.NEW,
        LeadStatus.CONTACTED,
        LeadStatus.QUALIFIED,
    ]
)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_staff(
    user_id: UUID | None = None,
    role: str = "admin",
) -> MagicMock:
    """Create a mock Staff object."""
    staff = MagicMock()
    staff.id = user_id or uuid4()
    staff.role = role
    staff.is_login_enabled = True
    staff.username = "testuser"
    staff.password_hash = "hashed"
    staff.failed_login_attempts = 0
    staff.locked_until = None
    return staff


def _make_mock_lead(
    lead_id: UUID | None = None,
    status: str = LeadStatus.NEW.value,
    name: str = "Test User",
    phone: str = "5551234567",
    email: str | None = None,
    situation: str = LeadSituation.EXPLORING.value,
) -> MagicMock:
    """Create a mock Lead object."""
    lead = MagicMock()
    lead.id = lead_id or uuid4()
    lead.status = status
    lead.name = name
    lead.phone = phone
    lead.email = email
    lead.situation = situation
    lead.sms_consent = False
    lead.terms_accepted = False
    lead.email_marketing_consent = False
    return lead


def _make_auth_service() -> AuthService:
    """Create an AuthService with a mock repository."""
    repo = AsyncMock()
    return AuthService(repository=repo)


def _make_lead_service():
    """Create a LeadService with mock dependencies."""
    from grins_platform.services.lead_service import LeadService

    lead_repo = AsyncMock()
    customer_service = AsyncMock()
    job_service = AsyncMock()
    staff_repo = AsyncMock()
    return LeadService(
        lead_repository=lead_repo,
        customer_service=customer_service,
        job_service=job_service,
        staff_repository=staff_repo,
    )


def _make_job_service():
    """Create a JobService with mock dependencies."""
    from grins_platform.services.job_service import JobService

    job_repo = AsyncMock()
    customer_repo = AsyncMock()
    property_repo = AsyncMock()
    service_repo = AsyncMock()
    return JobService(
        job_repository=job_repo,
        customer_repository=customer_repo,
        property_repository=property_repo,
        service_repository=service_repo,
    )


# ===================================================================
# Property 4: Token expiry meets minimum thresholds
# Feature: asap-platform-fixes, Property 4
# ===================================================================


@pytest.mark.unit
class TestProperty4TokenExpiry:
    """Property 4: Token expiry meets minimum thresholds.

    **Validates: Requirements 3.1, 3.2, 3.4**
    """

    @given(user_id=st.uuids(), role=roles)
    @settings(max_examples=20)
    def test_access_token_expiry_at_least_60_minutes(
        self,
        user_id: UUID,
        role: UserRole,
    ) -> None:
        """Access token expiration is at least 60 minutes from issuance."""
        from jose import jwt as jose_jwt

        svc = _make_auth_service()
        # Truncate to seconds since JWT exp is integer seconds
        before = datetime.now(UTC).replace(microsecond=0)
        token = svc._create_access_token(user_id, role)

        payload = jose_jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        min_expected = before + timedelta(minutes=60)

        assert exp >= min_expected, (
            f"Access token expires at {exp}, expected at least {min_expected}"
        )

    @given(user_id=st.uuids(), role=roles)
    @settings(max_examples=20)
    def test_refresh_token_expiry_at_least_30_days(
        self,
        user_id: UUID,
        role: UserRole,
    ) -> None:
        """Refresh token expiration is at least 30 days from issuance."""
        from jose import jwt as jose_jwt

        svc = _make_auth_service()
        # Truncate to seconds since JWT exp is integer seconds
        before = datetime.now(UTC).replace(microsecond=0)
        token = svc._create_refresh_token(user_id)

        payload = jose_jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        min_expected = before + timedelta(days=30)

        assert exp >= min_expected, (
            f"Refresh token expires at {exp}, expected at least {min_expected}"
        )

    def test_constants_match_minimum_thresholds(self) -> None:
        """Verify the module-level constants meet the spec."""
        assert ACCESS_TOKEN_EXPIRE_MINUTES >= 60
        assert REFRESH_TOKEN_EXPIRE_DAYS >= 30


# ===================================================================
# Property 5: Refresh token validity determines session outcome
# Feature: asap-platform-fixes, Property 5
# ===================================================================


@pytest.mark.unit
class TestProperty5RefreshTokenValidity:
    """Property 5: Refresh token validity determines session outcome.

    **Validates: Requirements 4.2, 4.3**
    """

    @given(user_id=st.uuids(), role=roles)
    @settings(max_examples=20)
    def test_valid_refresh_token_returns_new_access_token(
        self,
        user_id: UUID,
        role: UserRole,
    ) -> None:
        """A valid refresh token should produce a new access token."""
        from jose import jwt as jose_jwt

        svc = _make_auth_service()
        staff = _make_mock_staff(user_id=user_id, role="admin")
        svc.repository.get_by_id = AsyncMock(return_value=staff)

        refresh_token = svc._create_refresh_token(user_id)
        access_token, expires_in = _run_async(
            svc.refresh_access_token(refresh_token),
        )

        # Should return a valid access token
        payload = jose_jwt.decode(
            access_token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        assert payload["type"] == "access"
        assert payload["sub"] == str(user_id)
        assert expires_in == ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def test_expired_refresh_token_is_rejected(self) -> None:
        """An expired refresh token should raise TokenExpiredError."""
        svc = _make_auth_service()
        user_id = uuid4()

        # Create a token that expired 1 day ago
        expired_token = svc._create_refresh_token(
            user_id,
            expires_delta=timedelta(seconds=-1),
        )

        with pytest.raises(TokenExpiredError):
            _run_async(svc.refresh_access_token(expired_token))

    def test_malformed_refresh_token_is_rejected(self) -> None:
        """A malformed token should raise InvalidTokenError."""
        svc = _make_auth_service()

        with pytest.raises(InvalidTokenError):
            _run_async(svc.refresh_access_token("not-a-valid-jwt-token"))


# ===================================================================
# Property 6: Lead deletion removes the record
# Feature: asap-platform-fixes, Property 6
# ===================================================================


@pytest.mark.unit
class TestProperty6LeadDeletion:
    """Property 6: Lead deletion removes the record.

    **Validates: Requirements 5.1**
    """

    @given(lead_id=st.uuids())
    @settings(max_examples=20)
    def test_delete_lead_removes_record(self, lead_id: UUID) -> None:
        """Deleting an existing lead makes it non-retrievable."""
        svc = _make_lead_service()
        mock_lead = _make_mock_lead(lead_id=lead_id)

        # First call returns the lead (for delete), second returns None (for get)
        svc.lead_repository.get_by_id = AsyncMock(
            side_effect=[mock_lead, None],
        )
        svc.lead_repository.delete = AsyncMock()

        # Delete the lead
        _run_async(svc.delete_lead(lead_id))

        # Verify delete was called
        svc.lead_repository.delete.assert_awaited_once_with(lead_id)

        # Attempting to get the lead should raise LeadNotFoundError
        with pytest.raises(LeadNotFoundError):
            _run_async(svc.get_lead(lead_id))


# ===================================================================
# Property 7: Lead conversion preserves user-provided job description
# Feature: asap-platform-fixes, Property 7
# ===================================================================


@pytest.mark.unit
class TestProperty7ConversionJobDescription:
    """Property 7: Lead conversion preserves user-provided job description.

    **Validates: Requirements 6.1**
    """

    @given(
        lead_id=st.uuids(),
        job_description=non_empty_description,
    )
    @settings(max_examples=20)
    def test_conversion_uses_user_provided_description(
        self,
        lead_id: UUID,
        job_description: str,
    ) -> None:
        """Converting a lead with create_job=True uses the user's description."""
        from grins_platform.schemas.lead import LeadConversionRequest

        svc = _make_lead_service()
        mock_lead = _make_mock_lead(
            lead_id=lead_id,
            status=LeadStatus.NEW.value,
        )
        svc.lead_repository.get_by_id = AsyncMock(return_value=mock_lead)
        svc.lead_repository.update = AsyncMock()

        # Mock customer creation
        mock_customer = MagicMock()
        mock_customer.id = uuid4()
        svc.customer_service.create_customer = AsyncMock(
            return_value=mock_customer,
        )
        svc.customer_service.repository = AsyncMock()

        # Mock job creation — capture the JobCreate data
        mock_job = MagicMock()
        mock_job.id = uuid4()
        svc.job_service.create_job = AsyncMock(return_value=mock_job)

        data = LeadConversionRequest(
            create_job=True,
            job_description=job_description,
            force=True,
        )

        _run_async(svc.convert_lead(lead_id, data))

        # Verify the job was created with the user's description
        call_args = svc.job_service.create_job.call_args
        job_create_data = call_args[0][0]  # first positional arg
        assert job_create_data.description == job_description, (
            f"Expected description '{job_description}', "
            f"got '{job_create_data.description}'"
        )


# ===================================================================
# Property 8: Lead conversion updates status to converted
# Feature: asap-platform-fixes, Property 8
# ===================================================================


@pytest.mark.unit
class TestProperty8ConversionStatusUpdate:
    """Property 8: Lead conversion updates status to converted.

    **Validates: Requirements 6.2**
    """

    @given(
        lead_id=st.uuids(),
        initial_status=non_converted_statuses,
    )
    @settings(max_examples=20)
    def test_conversion_sets_status_to_converted(
        self,
        lead_id: UUID,
        initial_status: LeadStatus,
    ) -> None:
        """Converting a non-converted lead sets its status to 'converted'."""
        from grins_platform.schemas.lead import LeadConversionRequest

        svc = _make_lead_service()
        mock_lead = _make_mock_lead(
            lead_id=lead_id,
            status=initial_status.value,
        )
        svc.lead_repository.get_by_id = AsyncMock(return_value=mock_lead)
        svc.lead_repository.update = AsyncMock()

        mock_customer = MagicMock()
        mock_customer.id = uuid4()
        svc.customer_service.create_customer = AsyncMock(
            return_value=mock_customer,
        )
        svc.customer_service.repository = AsyncMock()

        data = LeadConversionRequest(create_job=False, force=True)

        _run_async(svc.convert_lead(lead_id, data))

        # Verify the lead was updated with converted status
        update_call = svc.lead_repository.update.call_args
        update_dict = update_call[0][1]
        assert update_dict["status"] == LeadStatus.CONVERTED.value


# ===================================================================
# Property 9: Lead conversion without job creates customer only
# Feature: asap-platform-fixes, Property 9
# ===================================================================


@pytest.mark.unit
class TestProperty9ConversionWithoutJob:
    """Property 9: Lead conversion without job creates customer only.

    **Validates: Requirements 6.3**
    """

    @given(lead_id=st.uuids())
    @settings(max_examples=20)
    def test_conversion_without_job_returns_none_job_id(
        self,
        lead_id: UUID,
    ) -> None:
        """Converting with create_job=False creates customer, returns job_id=None."""
        from grins_platform.schemas.lead import LeadConversionRequest

        svc = _make_lead_service()
        mock_lead = _make_mock_lead(
            lead_id=lead_id,
            status=LeadStatus.NEW.value,
        )
        svc.lead_repository.get_by_id = AsyncMock(return_value=mock_lead)
        svc.lead_repository.update = AsyncMock()

        mock_customer = MagicMock()
        mock_customer.id = uuid4()
        svc.customer_service.create_customer = AsyncMock(
            return_value=mock_customer,
        )
        svc.customer_service.repository = AsyncMock()

        data = LeadConversionRequest(create_job=False, force=True)

        result = _run_async(svc.convert_lead(lead_id, data))

        # Customer should be created
        svc.customer_service.create_customer.assert_awaited_once()
        # Job should NOT be created
        svc.job_service.create_job.assert_not_awaited()
        # Response should have job_id=None
        assert result.job_id is None
        assert result.customer_id == mock_customer.id


# ===================================================================
# Property 10: Already-converted leads are rejected
# Feature: asap-platform-fixes, Property 10
# ===================================================================


@pytest.mark.unit
class TestProperty10AlreadyConvertedRejection:
    """Property 10: Already-converted leads are rejected.

    **Validates: Requirements 6.4**
    """

    @given(lead_id=st.uuids())
    @settings(max_examples=20)
    def test_converting_already_converted_lead_raises_error(
        self,
        lead_id: UUID,
    ) -> None:
        """Attempting to convert an already-converted lead raises error."""
        from grins_platform.schemas.lead import LeadConversionRequest

        svc = _make_lead_service()
        mock_lead = _make_mock_lead(
            lead_id=lead_id,
            status=LeadStatus.CONVERTED.value,
        )
        svc.lead_repository.get_by_id = AsyncMock(return_value=mock_lead)

        data = LeadConversionRequest(create_job=False, force=True)

        with pytest.raises(LeadAlreadyConvertedError):
            _run_async(svc.convert_lead(lead_id, data))


# ===================================================================
# Property 11: Manual lead creation requires name and phone
# Feature: asap-platform-fixes, Property 11
# ===================================================================


@pytest.mark.unit
class TestProperty11ManualLeadValidation:
    """Property 11: Manual lead creation requires name and phone.

    **Validates: Requirements 7.3**
    """

    @given(phone=phone_digits)
    @settings(max_examples=20)
    def test_empty_name_is_rejected(self, phone: str) -> None:
        """A lead with empty name should be rejected by validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ManualLeadCreate(name="", phone=phone)

    @given(name=non_empty_name)
    @settings(max_examples=20)
    def test_empty_phone_is_rejected(self, name: str) -> None:
        """A lead with empty phone should be rejected by validation."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ManualLeadCreate(name=name, phone="")

    @given(name=non_empty_name, phone=phone_digits)
    @settings(max_examples=20)
    def test_valid_name_and_phone_accepted(
        self,
        name: str,
        phone: str,
    ) -> None:
        """A lead with non-empty name and valid phone should be accepted."""
        lead = ManualLeadCreate(name=name, phone=phone)
        assert lead.name
        assert lead.phone


# ===================================================================
# Property 12: Manual lead creation round trip
# Feature: asap-platform-fixes, Property 12
# ===================================================================


@pytest.mark.unit
class TestProperty12ManualLeadRoundTrip:
    """Property 12: Manual lead creation round trip.

    **Validates: Requirements 7.4**
    """

    @given(
        name=non_empty_name,
        phone=phone_digits,
        email=st.just(None),
        situation=lead_situations,
    )
    @settings(max_examples=20)
    def test_create_and_retrieve_returns_matching_fields(
        self,
        name: str,
        phone: str,
        email: str | None,
        situation: LeadSituation,
    ) -> None:
        """Creating a manual lead and retrieving it returns matching data."""
        from grins_platform.schemas.lead import LeadResponse  # noqa: F401

        svc = _make_lead_service()

        # Build the input data
        data = ManualLeadCreate(
            name=name,
            phone=phone,
            email=email,
            situation=situation,
        )

        # The normalized phone from the schema
        normalized_phone = data.phone

        # Mock the repository create to return a lead-like object
        now = datetime.now(UTC)
        created_lead = MagicMock()
        created_lead.id = uuid4()
        created_lead.name = data.name
        created_lead.phone = normalized_phone
        created_lead.email = email
        created_lead.situation = situation.value
        created_lead.status = LeadStatus.NEW.value
        created_lead.lead_source = "manual"
        created_lead.source_detail = "Manual CRM entry"
        created_lead.source_site = "admin"
        created_lead.notes = None
        created_lead.zip_code = None
        created_lead.city = None
        created_lead.state = None
        created_lead.address = None
        created_lead.intake_tag = None
        created_lead.action_tags = ["needs_contact"]
        created_lead.assigned_to = None
        created_lead.customer_id = None
        created_lead.contacted_at = None
        created_lead.converted_at = None
        created_lead.customer_type = None
        created_lead.property_type = None
        created_lead.sms_consent = False
        created_lead.terms_accepted = False
        created_lead.email_marketing_consent = False
        created_lead.created_at = now
        created_lead.updated_at = now
        created_lead.moved_to = None
        created_lead.moved_at = None
        created_lead.last_contacted_at = None
        created_lead.job_requested = None

        svc.lead_repository.create = AsyncMock(return_value=created_lead)

        # Mock get_by_id to return the same lead for retrieval
        svc.lead_repository.get_by_id = AsyncMock(return_value=created_lead)

        # Create the lead
        with (
            patch(
                "grins_platform.services.lead_service.extract_zip_from_address",
                return_value=None,
            ),
            patch(
                "grins_platform.services.lead_service.lookup_zip",
                return_value=(None, None),
            ),
        ):
            create_result = _run_async(svc.create_manual_lead(data))

        # Retrieve the lead
        get_result = _run_async(svc.get_lead(created_lead.id))

        # Verify round-trip fields match
        assert create_result.name == data.name
        assert create_result.phone == normalized_phone
        assert get_result.name == data.name
        assert get_result.phone == normalized_phone


# ===================================================================
# Property 13: Job type update persists
# Feature: asap-platform-fixes, Property 13
# ===================================================================


@pytest.mark.unit
class TestProperty13JobTypeUpdatePersists:
    """Property 13: Job type update persists.

    **Validates: Requirements 8.1, 8.3**
    """

    @given(
        job_id=st.uuids(),
        new_job_type=valid_job_types,
    )
    @settings(max_examples=20)
    def test_update_job_type_persists(
        self,
        job_id: UUID,
        new_job_type: str,
    ) -> None:
        """Updating a job's type and retrieving it reflects the new type."""
        from grins_platform.schemas.job import JobUpdate

        svc = _make_job_service()

        # Mock existing job
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_job.job_type = "repair"  # original type
        mock_job.category = "ready_to_schedule"
        mock_job.status = "to_be_scheduled"

        # After update, the job should have the new type
        updated_job = MagicMock()
        updated_job.id = job_id
        updated_job.job_type = new_job_type

        svc.job_repository.get_by_id = AsyncMock(return_value=mock_job)
        svc.job_repository.update = AsyncMock(return_value=updated_job)

        update_data = JobUpdate(job_type=new_job_type)

        result = _run_async(svc.update_job(job_id, update_data))

        # Verify the update was called with the new job type
        update_call = svc.job_repository.update.call_args
        update_dict = update_call[0][1]
        assert update_dict["job_type"] == new_job_type

        # Verify the returned job has the new type
        assert result.job_type == new_job_type
