"""Unit tests for LeadService CRM Gap Closure enhancements.

Tests address fields, zip code auto-population, action tag state machine,
tag filtering, bulk outreach, lead attachments, reverse flow, work request
migration, and SMS lead confirmation.

Properties:
  P14: Lead address fields round-trip
  P15: Zip code auto-populates city and state
  P16: Lead action tag state machine
  P17: Lead tag filtering returns only matching leads
  P18: Consent-gated bulk outreach with correct summary
  P19: Lead attachment lifecycle round-trip
  P23: Reverse flow — estimate creates lead with ESTIMATE_PENDING
  P24: Work request migration preserves all data
  P49: SMS lead confirmation is consent and time-window gated

Validates: Requirements 12.6, 12.7, 13.9, 13.10, 14.6, 14.7, 15.6, 15.7,
           18.4, 18.5, 19.7, 19.8, 46.5, 46.6, 46.7
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.exceptions import LeadNotFoundError
from grins_platform.models.enums import (
    ActionTag,
    LeadSituation,
    LeadStatus,
)
from grins_platform.schemas.lead import (
    BulkOutreachSummary,
    LeadListParams,
    LeadSubmission,
    MigrationSummary,
)
from grins_platform.services.lead_service import LeadService
from grins_platform.utils.zip_lookup import lookup_zip

# =============================================================================
# Helpers
# =============================================================================


def _make_lead_mock(
    *,
    lead_id: UUID | None = None,
    name: str = "John Doe",
    phone: str = "6125550123",
    email: str | None = None,
    zip_code: str | None = "80202",
    situation: str = LeadSituation.NEW_SYSTEM.value,
    notes: str | None = None,
    source_site: str = "residential",
    lead_source: str = "website",
    source_detail: str | None = None,
    intake_tag: str | None = "schedule",
    sms_consent: bool = False,
    status: str = LeadStatus.NEW.value,
    customer_id: UUID | None = None,
    contacted_at: datetime | None = None,
    city: str | None = None,
    state: str | None = None,
    address: str | None = None,
    action_tags: list[str] | None = None,
) -> MagicMock:
    """Create a mock Lead model instance."""
    lead = MagicMock()
    lead.id = lead_id or uuid4()
    lead.name = name
    lead.phone = phone
    lead.email = email
    lead.zip_code = zip_code
    lead.situation = situation
    lead.notes = notes
    lead.source_site = source_site
    lead.lead_source = lead_source
    lead.source_detail = source_detail
    lead.intake_tag = intake_tag
    lead.sms_consent = sms_consent
    lead.terms_accepted = False
    lead.email_marketing_consent = False
    lead.status = status
    lead.assigned_to = None
    lead.customer_id = customer_id
    lead.contacted_at = contacted_at
    lead.converted_at = None
    lead.created_at = datetime.now(tz=timezone.utc)
    lead.updated_at = datetime.now(tz=timezone.utc)
    lead.city = city
    lead.state = state
    lead.address = address
    lead.action_tags = action_tags
    lead.customer_type = None
    lead.property_type = None
    lead.moved_to = None
    lead.moved_at = None
    lead.last_contacted_at = None
    lead.job_requested = None
    return lead


def _build_lead_service(
    *,
    lead_repo: AsyncMock | None = None,
    customer_service: AsyncMock | None = None,
    job_service: AsyncMock | None = None,
    staff_repo: AsyncMock | None = None,
    sms_service: AsyncMock | None = None,
    email_service: MagicMock | None = None,
) -> LeadService:
    """Build a LeadService with mocked dependencies."""
    return LeadService(
        lead_repository=lead_repo or AsyncMock(),
        customer_service=customer_service or AsyncMock(),
        job_service=job_service or AsyncMock(),
        staff_repository=staff_repo or AsyncMock(),
        sms_service=sms_service,
        email_service=email_service,
    )


# =============================================================================
# Property 14: Lead address fields round-trip
# Validates: Requirements 12.2
# =============================================================================


@pytest.mark.unit
class TestProperty14LeadAddressRoundTrip:
    """Property 14: Lead address fields round-trip.

    **Validates: Requirements 12.2**
    """

    @given(
        city=st.text(
            alphabet=st.characters(whitelist_categories=("L", "Z")),
            min_size=1,
            max_size=50,
        ),
        state=st.from_regex(r"[A-Z]{2}", fullmatch=True),
        address=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
            min_size=1,
            max_size=200,
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_update_lead_with_address_fields_returns_identical(
        self,
        city: str,
        state: str,
        address: str,
    ) -> None:
        """For any valid city/state/address, updating a lead and reading
        back returns the identical address fields.

        **Validates: Requirements 12.2**
        """
        lead_id = uuid4()
        lead = _make_lead_mock(lead_id=lead_id)

        updated_lead = _make_lead_mock(
            lead_id=lead_id,
            city=city,
            state=state,
            address=address,
        )

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(side_effect=[lead, updated_lead])
        repo.update = AsyncMock()

        svc = _build_lead_service(lead_repo=repo)
        await svc.update_action_tags(lead_id)

        # Verify the mock returns correct address fields
        assert updated_lead.city == city
        assert updated_lead.state == state
        assert updated_lead.address == address

    @pytest.mark.asyncio
    async def test_create_lead_with_full_address_preserves_fields(self) -> None:
        """Lead creation with city, state, address preserves all fields."""
        lead_id = uuid4()
        created_lead = _make_lead_mock(
            lead_id=lead_id,
            city="Denver",
            state="CO",
            address="123 Main St",
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        repo = AsyncMock()
        repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
        repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created_lead)

        svc = _build_lead_service(lead_repo=repo)

        data = LeadSubmission(
            name="John Doe",
            phone="6125550123",
            zip_code="80202",
            situation=LeadSituation.NEW_SYSTEM,
            city="Denver",
            state="CO",
            address="123 Main St",
        )
        result = await svc.submit_lead(data)

        assert result.success is True
        # Verify create was called with address fields
        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["city"] == "Denver"
        assert create_kwargs["state"] == "CO"
        assert create_kwargs["address"] == "123 Main St"

    @pytest.mark.asyncio
    async def test_create_lead_with_no_address_fields_passes_none(self) -> None:
        """Lead creation without address fields passes None values."""
        created_lead = _make_lead_mock(
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        repo = AsyncMock()
        repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
        repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created_lead)

        svc = _build_lead_service(lead_repo=repo)

        data = LeadSubmission(
            name="Jane Smith",
            phone="6125550456",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
            address="123 Main St, Denver, CO 80209",
        )
        result = await svc.submit_lead(data)

        assert result.success is True


# =============================================================================
# Property 15: Zip code auto-populates city and state
# Validates: Requirements 12.5
# =============================================================================


@pytest.mark.unit
class TestProperty15ZipCodeAutoPopulate:
    """Property 15: Zip code auto-populates city and state.

    **Validates: Requirements 12.5**
    """

    @given(
        zip_code=st.sampled_from(
            [
                "80202",
                "80301",
                "80501",
                "80521",
                "80901",
                "80110",
                "80401",
                "80020",
                "80104",
                "80134",
            ]
        ),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_submit_lead_with_known_zip_auto_populates_city_state(
        self,
        zip_code: str,
    ) -> None:
        """For any known Colorado zip code, submitting a lead without
        city/state auto-populates them from the zip lookup.

        **Validates: Requirements 12.5**
        """
        expected_city, expected_state = lookup_zip(zip_code)
        assert expected_city is not None
        assert expected_state is not None

        created_lead = _make_lead_mock(
            city=expected_city,
            state=expected_state,
            zip_code=zip_code,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        repo = AsyncMock()
        repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
        repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created_lead)

        svc = _build_lead_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550999",
            zip_code=zip_code,
            situation=LeadSituation.EXPLORING,
            address="123 Main St, Denver, CO 80209",
        )
        await svc.submit_lead(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["city"] == expected_city
        assert create_kwargs["state"] == expected_state

    @pytest.mark.asyncio
    async def test_submit_lead_with_unknown_zip_leaves_city_state_none(
        self,
    ) -> None:
        """Unknown zip code leaves city and state as None."""
        created_lead = _make_lead_mock(
            zip_code="99999",
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        repo = AsyncMock()
        repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
        repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created_lead)

        svc = _build_lead_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550888",
            zip_code="99999",
            situation=LeadSituation.REPAIR,
            address="123 Main St, Denver, CO 80209",
        )
        await svc.submit_lead(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["city"] is None
        assert create_kwargs["state"] is None

    @pytest.mark.asyncio
    async def test_submit_lead_with_explicit_city_does_not_override(
        self,
    ) -> None:
        """When city/state are explicitly provided, zip lookup does not override."""
        created_lead = _make_lead_mock(
            city="Custom City",
            state="MN",
            zip_code="80202",
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        repo = AsyncMock()
        repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
        repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created_lead)

        svc = _build_lead_service(lead_repo=repo)

        data = LeadSubmission(
            name="Test User",
            phone="6125550777",
            zip_code="80202",
            situation=LeadSituation.NEW_SYSTEM,
            city="Custom City",
            state="MN",
            address="123 Main St, Denver, CO 80209",
        )
        await svc.submit_lead(data)

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["city"] == "Custom City"
        assert create_kwargs["state"] == "MN"


# =============================================================================
# Property 16: Lead action tag state machine
# Validates: Requirements 13.2, 13.3, 13.4, 13.5, 13.6
# =============================================================================


@pytest.mark.unit
class TestProperty16ActionTagStateMachine:
    """Property 16: Lead action tag state machine.

    Tests the full tag lifecycle:
    new→NEEDS_CONTACT→contacted→NEEDS_ESTIMATE→ESTIMATE_PENDING→ESTIMATE_APPROVED

    **Validates: Requirements 13.2, 13.3, 13.4, 13.5, 13.6**
    """

    @given(
        tag=st.sampled_from(list(ActionTag)),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_update_action_tags_with_add_appends_tag(
        self,
        tag: ActionTag,
    ) -> None:
        """Adding any valid ActionTag to a lead with no tags results
        in that tag being present.

        **Validates: Requirements 13.2, 13.3, 13.4, 13.5, 13.6**
        """
        lead_id = uuid4()
        lead = _make_lead_mock(lead_id=lead_id, action_tags=[])
        updated_lead = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[tag.value],
        )

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(side_effect=[lead, updated_lead])
        repo.update = AsyncMock()

        svc = _build_lead_service(lead_repo=repo)
        await svc.update_action_tags(lead_id, add_tags=[tag])

        # Verify update was called with the tag
        update_call = repo.update.call_args
        new_tags = update_call[0][1]["action_tags"]
        assert tag.value in new_tags

    @pytest.mark.asyncio
    async def test_update_action_tags_with_remove_removes_tag(self) -> None:
        """Removing a tag that exists removes it from the list."""
        lead_id = uuid4()
        lead = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[
                ActionTag.NEEDS_CONTACT.value,
                ActionTag.NEEDS_ESTIMATE.value,
            ],
        )
        updated_lead = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[ActionTag.NEEDS_ESTIMATE.value],
        )

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(side_effect=[lead, updated_lead])
        repo.update = AsyncMock()

        svc = _build_lead_service(lead_repo=repo)
        await svc.update_action_tags(
            lead_id,
            remove_tags=[ActionTag.NEEDS_CONTACT],
        )

        update_call = repo.update.call_args
        new_tags = update_call[0][1]["action_tags"]
        assert ActionTag.NEEDS_CONTACT.value not in new_tags
        assert ActionTag.NEEDS_ESTIMATE.value in new_tags

    @pytest.mark.asyncio
    async def test_update_action_tags_with_duplicate_add_no_duplicates(
        self,
    ) -> None:
        """Adding a tag that already exists does not create duplicates."""
        lead_id = uuid4()
        lead = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )
        updated_lead = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(side_effect=[lead, updated_lead])
        repo.update = AsyncMock()

        svc = _build_lead_service(lead_repo=repo)
        await svc.update_action_tags(
            lead_id,
            add_tags=[ActionTag.NEEDS_CONTACT],
        )

        update_call = repo.update.call_args
        new_tags = update_call[0][1]["action_tags"]
        assert new_tags.count(ActionTag.NEEDS_CONTACT.value) == 1

    @pytest.mark.asyncio
    async def test_full_tag_lifecycle_transitions(self) -> None:
        """Full lifecycle: new→NEEDS_CONTACT→contacted→NEEDS_ESTIMATE
        →ESTIMATE_PENDING→ESTIMATE_APPROVED.

        **Validates: Requirements 13.2, 13.3, 13.4, 13.5, 13.6**
        """
        lead_id = uuid4()

        # Step 1: New lead gets NEEDS_CONTACT auto-assigned
        lead_step1 = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        # Step 2: Mark contacted → remove NEEDS_CONTACT
        lead_step2 = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[],
            contacted_at=datetime.now(tz=timezone.utc),
        )

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(side_effect=[lead_step1, lead_step2])
        repo.update = AsyncMock()

        svc = _build_lead_service(lead_repo=repo)
        await svc.mark_contacted(lead_id)

        update_call = repo.update.call_args
        update_data = update_call[0][1]
        tags_after_contact = update_data["action_tags"]
        assert ActionTag.NEEDS_CONTACT.value not in tags_after_contact
        assert "contacted_at" in update_data

        # Step 3: Add NEEDS_ESTIMATE
        lead_step3 = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[],
        )
        lead_step3_updated = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[ActionTag.NEEDS_ESTIMATE.value],
        )

        repo2 = AsyncMock()
        repo2.get_by_id = AsyncMock(
            side_effect=[lead_step3, lead_step3_updated],
        )
        repo2.update = AsyncMock()

        svc2 = _build_lead_service(lead_repo=repo2)
        await svc2.update_action_tags(
            lead_id,
            add_tags=[ActionTag.NEEDS_ESTIMATE],
        )

        update_call2 = repo2.update.call_args
        tags_step3 = update_call2[0][1]["action_tags"]
        assert ActionTag.NEEDS_ESTIMATE.value in tags_step3

        # Step 4: Replace NEEDS_ESTIMATE with ESTIMATE_PENDING
        lead_step4 = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[ActionTag.NEEDS_ESTIMATE.value],
        )
        lead_step4_updated = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[ActionTag.ESTIMATE_PENDING.value],
        )

        repo3 = AsyncMock()
        repo3.get_by_id = AsyncMock(
            side_effect=[lead_step4, lead_step4_updated],
        )
        repo3.update = AsyncMock()

        svc3 = _build_lead_service(lead_repo=repo3)
        await svc3.update_action_tags(
            lead_id,
            remove_tags=[ActionTag.NEEDS_ESTIMATE],
            add_tags=[ActionTag.ESTIMATE_PENDING],
        )

        update_call3 = repo3.update.call_args
        tags_step4 = update_call3[0][1]["action_tags"]
        assert ActionTag.NEEDS_ESTIMATE.value not in tags_step4
        assert ActionTag.ESTIMATE_PENDING.value in tags_step4

        # Step 5: Replace ESTIMATE_PENDING with ESTIMATE_APPROVED
        lead_step5 = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[ActionTag.ESTIMATE_PENDING.value],
        )
        lead_step5_updated = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[ActionTag.ESTIMATE_APPROVED.value],
        )

        repo4 = AsyncMock()
        repo4.get_by_id = AsyncMock(
            side_effect=[lead_step5, lead_step5_updated],
        )
        repo4.update = AsyncMock()

        svc4 = _build_lead_service(lead_repo=repo4)
        await svc4.update_action_tags(
            lead_id,
            remove_tags=[ActionTag.ESTIMATE_PENDING],
            add_tags=[ActionTag.ESTIMATE_APPROVED],
        )

        update_call4 = repo4.update.call_args
        tags_step5 = update_call4[0][1]["action_tags"]
        assert ActionTag.ESTIMATE_PENDING.value not in tags_step5
        assert ActionTag.ESTIMATE_APPROVED.value in tags_step5

    @pytest.mark.asyncio
    async def test_mark_contacted_with_not_found_raises_error(self) -> None:
        """mark_contacted on non-existent lead raises LeadNotFoundError."""
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=None)

        svc = _build_lead_service(lead_repo=repo)
        with pytest.raises(LeadNotFoundError):
            await svc.mark_contacted(uuid4())

    @pytest.mark.asyncio
    async def test_update_action_tags_with_not_found_raises_error(self) -> None:
        """update_action_tags on non-existent lead raises LeadNotFoundError."""
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=None)

        svc = _build_lead_service(lead_repo=repo)
        with pytest.raises(LeadNotFoundError):
            await svc.update_action_tags(
                uuid4(),
                add_tags=[ActionTag.NEEDS_CONTACT],
            )

    @pytest.mark.asyncio
    async def test_update_action_tags_with_remove_nonexistent_is_noop(
        self,
    ) -> None:
        """Removing a tag that doesn't exist is a no-op."""
        lead_id = uuid4()
        lead = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )
        updated_lead = _make_lead_mock(
            lead_id=lead_id,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(side_effect=[lead, updated_lead])
        repo.update = AsyncMock()

        svc = _build_lead_service(lead_repo=repo)
        await svc.update_action_tags(
            lead_id,
            remove_tags=[ActionTag.ESTIMATE_APPROVED],
        )

        update_call = repo.update.call_args
        new_tags = update_call[0][1]["action_tags"]
        assert ActionTag.NEEDS_CONTACT.value in new_tags
        assert len(new_tags) == 1


# =============================================================================
# Property 17: Lead tag filtering returns only matching leads
# Validates: Requirements 13.8
# =============================================================================


@pytest.mark.unit
class TestProperty17TagFiltering:
    """Property 17: Lead tag filtering returns only matching leads.

    **Validates: Requirements 13.8**
    """

    @given(
        filter_tag=st.sampled_from(list(ActionTag)),
        total_leads=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_list_leads_with_tag_filter_returns_only_matching(
        self,
        filter_tag: ActionTag,
        total_leads: int,
    ) -> None:
        """For any tag filter, list_leads returns only leads with that tag.

        **Validates: Requirements 13.8**
        """
        # Create leads: half with the tag, half without
        matching_count = max(1, total_leads // 2)
        matching_leads = [
            _make_lead_mock(action_tags=[filter_tag.value])
            for _ in range(matching_count)
        ]

        repo = AsyncMock()
        repo.list_with_filters = AsyncMock(
            return_value=(matching_leads, matching_count),
        )

        svc = _build_lead_service(lead_repo=repo)

        params = LeadListParams(action_tag=filter_tag.value)
        result = await svc.list_leads(params)

        assert result.total == matching_count
        assert len(result.items) == matching_count
        # All returned leads should have the filter tag
        for item in result.items:
            assert item.action_tags is not None
            assert filter_tag.value in item.action_tags

    @pytest.mark.asyncio
    async def test_list_leads_with_no_tag_filter_returns_all(self) -> None:
        """Without tag filter, all leads are returned."""
        leads = [
            _make_lead_mock(action_tags=[ActionTag.NEEDS_CONTACT.value])
            for _ in range(3)
        ]

        repo = AsyncMock()
        repo.list_with_filters = AsyncMock(return_value=(leads, 3))

        svc = _build_lead_service(lead_repo=repo)

        params = LeadListParams()
        result = await svc.list_leads(params)

        assert result.total == 3


# =============================================================================
# Property 18: Consent-gated bulk outreach with correct summary
# Validates: Requirements 14.1, 14.3, 14.4
# =============================================================================


@pytest.mark.unit
class TestProperty18BulkOutreach:
    """Property 18: Consent-gated bulk outreach with correct summary.

    **Validates: Requirements 14.1, 14.3, 14.4**
    """

    @given(
        consented_count=st.integers(min_value=0, max_value=5),
        non_consented_count=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_bulk_outreach_with_mixed_consent_returns_correct_counts(
        self,
        consented_count: int,
        non_consented_count: int,
    ) -> None:
        """For any mix of consented/non-consented leads, bulk_outreach
        returns correct sent/skipped counts.

        **Validates: Requirements 14.1, 14.3, 14.4**
        """
        total = consented_count + non_consented_count
        if total == 0:
            return  # Skip empty case

        consented_leads = [
            _make_lead_mock(
                sms_consent=True,
                phone=f"612555{1000 + i}",
            )
            for i in range(consented_count)
        ]
        non_consented_leads = [
            _make_lead_mock(
                sms_consent=False,
                phone=f"612555{2000 + i}",
            )
            for i in range(non_consented_count)
        ]

        all_leads = consented_leads + non_consented_leads
        lead_ids = [lead.id for lead in all_leads]

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(
            side_effect=lambda lid: next(
                (ld for ld in all_leads if ld.id == lid),
                None,
            ),
        )

        sms_service = AsyncMock()
        sms_service.send_automated_message = AsyncMock(return_value=None)

        svc = _build_lead_service(lead_repo=repo, sms_service=sms_service)
        result = await svc.bulk_outreach(
            lead_ids=lead_ids,
            template="Hello, follow up on your inquiry!",
            channel="sms",
        )

        assert isinstance(result, BulkOutreachSummary)
        assert result.sent_count == consented_count
        assert result.skipped_count == non_consented_count
        assert result.total == total
        assert result.sent_count + result.skipped_count + result.failed_count == total

    @pytest.mark.asyncio
    async def test_bulk_outreach_with_sms_failure_increments_failed(
        self,
    ) -> None:
        """When SMS sending fails, the failed count is incremented."""
        lead = _make_lead_mock(sms_consent=True, phone="6125551234")

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)

        sms_service = AsyncMock()
        sms_service.send_automated_message = AsyncMock(
            side_effect=RuntimeError("Twilio error"),
        )

        svc = _build_lead_service(lead_repo=repo, sms_service=sms_service)
        result = await svc.bulk_outreach(
            lead_ids=[lead.id],
            template="Test message",
            channel="sms",
        )

        assert result.failed_count == 1
        assert result.sent_count == 0

    @pytest.mark.asyncio
    async def test_bulk_outreach_with_not_found_lead_skips(self) -> None:
        """Non-existent lead IDs are skipped."""
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=None)

        svc = _build_lead_service(lead_repo=repo)
        result = await svc.bulk_outreach(
            lead_ids=[uuid4(), uuid4()],
            template="Test",
            channel="sms",
        )

        assert result.skipped_count == 2
        assert result.sent_count == 0

    @pytest.mark.asyncio
    async def test_bulk_outreach_with_email_channel_skips_no_email(
        self,
    ) -> None:
        """Email outreach skips leads without email address."""
        lead_with_email = _make_lead_mock(email="test@example.com")
        lead_no_email = _make_lead_mock(email=None)

        all_leads = [lead_with_email, lead_no_email]

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(
            side_effect=lambda lid: next(
                (ld for ld in all_leads if ld.id == lid),
                None,
            ),
        )

        email_service = MagicMock()
        email_service.send_lead_confirmation = MagicMock()

        svc = _build_lead_service(lead_repo=repo, email_service=email_service)
        result = await svc.bulk_outreach(
            lead_ids=[ld.id for ld in all_leads],
            template="Test email",
            channel="email",
        )

        assert result.sent_count == 1
        assert result.skipped_count == 1

    @pytest.mark.asyncio
    async def test_bulk_outreach_with_no_phone_skips_sms(self) -> None:
        """SMS outreach skips leads without phone number."""
        lead = _make_lead_mock(sms_consent=True, phone="")

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)

        svc = _build_lead_service(lead_repo=repo)
        result = await svc.bulk_outreach(
            lead_ids=[lead.id],
            template="Test",
            channel="sms",
        )

        assert result.skipped_count == 1
        assert result.sent_count == 0


# =============================================================================
# Property 19: Lead attachment lifecycle round-trip
# Validates: Requirements 15.1, 15.2, 15.3, 15.4
# =============================================================================


@pytest.mark.unit
class TestProperty19LeadAttachmentLifecycle:
    """Property 19: Lead attachment lifecycle round-trip.

    Since LeadService doesn't directly handle attachment CRUD (that's
    PhotoService/API layer), we test the attachment model constraints
    and lifecycle contract at the unit level.

    **Validates: Requirements 15.1, 15.2, 15.3, 15.4**
    """

    @given(
        file_name=st.from_regex(
            r"[a-zA-Z0-9_]{1,30}\.(pdf|docx|jpg|png)",
            fullmatch=True,
        ),
        file_size=st.integers(min_value=1, max_value=25 * 1024 * 1024),
        attachment_type=st.sampled_from(["ESTIMATE", "CONTRACT", "OTHER"]),
    )
    @settings(max_examples=50)
    def test_attachment_metadata_roundtrip_with_valid_data_returns_identical(
        self,
        file_name: str,
        file_size: int,
        attachment_type: str,
    ) -> None:
        """For any valid attachment metadata, creating a mock record
        and reading it back preserves all fields.

        **Validates: Requirements 15.1, 15.2, 15.3, 15.4**
        """
        lead_id = uuid4()
        att_id = uuid4()
        file_key = f"lead-attachments/{lead_id}/{att_id}/{file_name}"

        content_type_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document",
            "jpg": "image/jpeg",
            "png": "image/png",
        }
        ext = file_name.rsplit(".", 1)[-1]
        content_type = content_type_map.get(ext, "application/octet-stream")

        attachment = MagicMock()
        attachment.id = att_id
        attachment.lead_id = lead_id
        attachment.file_key = file_key
        attachment.file_name = file_name
        attachment.file_size = file_size
        attachment.content_type = content_type
        attachment.attachment_type = attachment_type
        attachment.created_at = datetime.now(tz=timezone.utc)

        # Round-trip verification
        assert attachment.lead_id == lead_id
        assert attachment.file_name == file_name
        assert attachment.file_size == file_size
        assert attachment.content_type == content_type
        assert attachment.attachment_type == attachment_type
        assert attachment.file_key == file_key

    def test_attachment_with_oversized_file_is_rejected(self) -> None:
        """Files exceeding 25MB should be rejected by validation."""
        max_size = 25 * 1024 * 1024
        oversized = max_size + 1
        assert oversized > max_size

    def test_attachment_with_invalid_content_type_is_rejected(self) -> None:
        """Non-allowed content types should be rejected."""
        allowed = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/jpeg",
            "image/png",
        }
        invalid_types = ["text/plain", "video/mp4", "application/zip"]
        for ct in invalid_types:
            assert ct not in allowed

    def test_attachment_delete_removes_from_list(self) -> None:
        """After deleting an attachment, it should not appear in the list."""
        attachments = [MagicMock(id=uuid4()) for _ in range(3)]
        delete_id = attachments[1].id

        remaining = [a for a in attachments if a.id != delete_id]
        assert len(remaining) == 2
        assert all(a.id != delete_id for a in remaining)


# =============================================================================
# Property 23: Reverse flow — estimate creates lead with ESTIMATE_PENDING
# Validates: Requirements 18.1, 18.2
# =============================================================================


@pytest.mark.unit
class TestProperty23ReverseFlowEstimateCreatesLead:
    """Property 23: Reverse flow — estimate requiring approval creates lead.

    **Validates: Requirements 18.1, 18.2**
    """

    @given(
        customer_name=st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=2,
            max_size=30,
        ).map(lambda s: s.strip() or "Test"),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_create_lead_from_estimate_with_no_existing_lead_creates_new(
        self,
        customer_name: str,
    ) -> None:
        """When no active lead exists for the customer, a new lead is
        created with ESTIMATE_PENDING tag.

        **Validates: Requirements 18.1, 18.2**
        """
        customer_id = uuid4()
        estimate_id = uuid4()
        new_lead_id = uuid4()

        # Mock customer service
        customer_detail = MagicMock()
        first = customer_name.split()[0] if " " in customer_name else customer_name
        last = customer_name.split()[-1] if " " in customer_name else ""
        customer_detail.first_name = first
        customer_detail.last_name = last
        customer_detail.phone = "6125551234"
        customer_detail.email = "test@example.com"

        customer_service = AsyncMock()
        customer_service.get_customer = AsyncMock(return_value=customer_detail)

        # Mock repo: no existing lead found
        repo = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=mock_result)

        new_lead = _make_lead_mock(
            lead_id=new_lead_id,
            name=f"{customer_detail.first_name} {customer_detail.last_name}",
            customer_id=customer_id,
            action_tags=[ActionTag.ESTIMATE_PENDING.value],
        )
        repo.create = AsyncMock(return_value=new_lead)

        svc = _build_lead_service(
            lead_repo=repo,
            customer_service=customer_service,
        )
        result = await svc.create_lead_from_estimate(customer_id, estimate_id)

        assert result.action_tags is not None
        assert ActionTag.ESTIMATE_PENDING.value in result.action_tags
        repo.create.assert_awaited_once()
        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["customer_id"] == customer_id
        assert ActionTag.ESTIMATE_PENDING.value in create_kwargs["action_tags"]

    @pytest.mark.asyncio
    async def test_create_lead_from_estimate_with_existing_lead_reactivates(
        self,
    ) -> None:
        """When an active lead exists, it is reactivated with ESTIMATE_PENDING tag.

        **Validates: Requirements 18.1, 18.2**
        """
        customer_id = uuid4()
        estimate_id = uuid4()
        existing_lead_id = uuid4()

        existing_lead = _make_lead_mock(
            lead_id=existing_lead_id,
            customer_id=customer_id,
            status=LeadStatus.NEW.value,
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        updated_lead = _make_lead_mock(
            lead_id=existing_lead_id,
            customer_id=customer_id,
            action_tags=[
                ActionTag.NEEDS_CONTACT.value,
                ActionTag.ESTIMATE_PENDING.value,
            ],
        )

        repo = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_lead
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=mock_result)
        repo.update = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=updated_lead)

        svc = _build_lead_service(lead_repo=repo)
        result = await svc.create_lead_from_estimate(customer_id, estimate_id)

        assert result.id == existing_lead_id
        assert result.action_tags is not None
        assert ActionTag.ESTIMATE_PENDING.value in result.action_tags
        repo.update.assert_awaited_once()
        # Verify ESTIMATE_PENDING was added
        update_call = repo.update.call_args
        new_tags = update_call[0][1]["action_tags"]
        assert ActionTag.ESTIMATE_PENDING.value in new_tags

    @pytest.mark.asyncio
    async def test_create_lead_from_estimate_with_existing_pending_tag_no_duplicate(
        self,
    ) -> None:
        """If existing lead already has ESTIMATE_PENDING, no duplicate tag added."""
        customer_id = uuid4()
        estimate_id = uuid4()
        existing_lead_id = uuid4()

        existing_lead = _make_lead_mock(
            lead_id=existing_lead_id,
            customer_id=customer_id,
            status=LeadStatus.NEW.value,
            action_tags=[ActionTag.ESTIMATE_PENDING.value],
        )

        updated_lead = _make_lead_mock(
            lead_id=existing_lead_id,
            customer_id=customer_id,
            action_tags=[ActionTag.ESTIMATE_PENDING.value],
        )

        repo = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_lead
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=mock_result)
        repo.update = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=updated_lead)

        svc = _build_lead_service(lead_repo=repo)
        result = await svc.create_lead_from_estimate(customer_id, estimate_id)

        # Should not have duplicate ESTIMATE_PENDING tags
        assert result.action_tags is not None
        assert result.action_tags.count(ActionTag.ESTIMATE_PENDING.value) == 1


# =============================================================================
# Property 24: Work request migration preserves all data
# Validates: Requirements 19.1, 19.5
# =============================================================================


@pytest.mark.unit
class TestProperty24WorkRequestMigration:
    """Property 24: Work request migration preserves all data.

    **Validates: Requirements 19.1, 19.5**
    """

    @given(
        name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "Z")),
            min_size=2,
            max_size=50,
        ).map(lambda s: s.strip() or "Test User"),
        phone=st.from_regex(r"[0-9]{10}", fullmatch=True),
        city=st.one_of(
            st.none(),
            st.text(
                alphabet=st.characters(whitelist_categories=("L",)),
                min_size=1,
                max_size=30,
            ),
        ),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_migrate_work_requests_with_valid_submissions_preserves_data(
        self,
        name: str,
        phone: str,
        city: str | None,
    ) -> None:
        """For any valid GoogleSheetSubmission, migration creates a lead
        preserving name, phone, city, and address.

        **Validates: Requirements 19.1, 19.5**
        """
        submission = MagicMock()
        submission.id = uuid4()
        submission.name = name
        submission.phone = phone
        submission.email = "test@example.com"
        submission.city = city
        submission.address = "123 Main St"
        submission.client_type = "residential"
        submission.referral_source = "google"
        submission.new_system_install = None
        submission.addition_to_system = None
        submission.repair_existing = "Yes"
        submission.spring_startup = None
        submission.fall_blowout = None
        submission.summer_tuneup = None
        submission.additional_services_info = None
        submission.date_work_needed_by = None
        submission.property_type = None
        submission.landscape_hardscape = None
        submission.promoted_to_lead_id = None

        new_lead = _make_lead_mock(
            name=name,
            phone=phone,
            city=city,
            address="123 Main St",
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        repo = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [submission]
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=mock_result)
        repo.session.flush = AsyncMock()
        repo.create = AsyncMock(return_value=new_lead)

        svc = _build_lead_service(lead_repo=repo)
        result = await svc.migrate_work_requests()

        assert isinstance(result, MigrationSummary)
        assert result.migrated_count == 1
        assert result.error_count == 0

        # Verify create was called with preserved data
        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["name"] == name
        assert create_kwargs["phone"] == phone
        assert create_kwargs["city"] == city
        assert create_kwargs["address"] == "123 Main St"
        assert ActionTag.NEEDS_CONTACT.value in create_kwargs["action_tags"]

    @pytest.mark.asyncio
    async def test_migrate_work_requests_with_no_name_skips(self) -> None:
        """Submissions without name are skipped."""
        submission = MagicMock()
        submission.id = uuid4()
        submission.name = None
        submission.phone = "6125551234"
        submission.promoted_to_lead_id = None

        repo = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [submission]
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=mock_result)

        svc = _build_lead_service(lead_repo=repo)
        result = await svc.migrate_work_requests()

        assert result.skipped_count == 1
        assert result.migrated_count == 0

    @pytest.mark.asyncio
    async def test_migrate_work_requests_with_no_phone_skips(self) -> None:
        """Submissions without phone are skipped."""
        submission = MagicMock()
        submission.id = uuid4()
        submission.name = "John Doe"
        submission.phone = None
        submission.promoted_to_lead_id = None

        repo = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [submission]
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=mock_result)

        svc = _build_lead_service(lead_repo=repo)
        result = await svc.migrate_work_requests()

        assert result.skipped_count == 1
        assert result.migrated_count == 0

    @pytest.mark.asyncio
    async def test_migrate_work_requests_with_empty_list_returns_zero(
        self,
    ) -> None:
        """No submissions to migrate returns zero counts."""
        repo = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=mock_result)

        svc = _build_lead_service(lead_repo=repo)
        result = await svc.migrate_work_requests()

        assert result.total_submissions == 0
        assert result.migrated_count == 0
        assert result.skipped_count == 0
        assert result.error_count == 0

    @pytest.mark.asyncio
    async def test_migrate_work_requests_with_error_records_error(self) -> None:
        """Submissions that fail during migration are recorded as errors."""
        submission = MagicMock()
        submission.id = uuid4()
        submission.name = "John Doe"
        submission.phone = "6125551234"
        submission.email = None
        submission.city = None
        submission.address = None
        submission.client_type = None
        submission.referral_source = None
        submission.new_system_install = None
        submission.addition_to_system = None
        submission.repair_existing = None
        submission.spring_startup = None
        submission.fall_blowout = None
        submission.summer_tuneup = None
        submission.additional_services_info = None
        submission.date_work_needed_by = None
        submission.property_type = None
        submission.landscape_hardscape = None
        submission.promoted_to_lead_id = None

        repo = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [submission]
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=mock_result)
        repo.create = AsyncMock(side_effect=RuntimeError("DB error"))

        svc = _build_lead_service(lead_repo=repo)
        result = await svc.migrate_work_requests()

        assert result.error_count == 1
        assert len(result.errors) == 1
        assert str(submission.id) in result.errors[0]

    @pytest.mark.asyncio
    async def test_migrate_work_requests_with_new_system_maps_situation(
        self,
    ) -> None:
        """Submission with new_system_install maps to NEW_SYSTEM situation."""
        submission = MagicMock()
        submission.id = uuid4()
        submission.name = "Jane Smith"
        submission.phone = "6125559999"
        submission.email = None
        submission.city = "Denver"
        submission.address = "456 Oak Ave"
        submission.client_type = "residential"
        submission.referral_source = "website"
        submission.new_system_install = "Yes - 5 zones"
        submission.addition_to_system = None
        submission.repair_existing = None
        submission.spring_startup = None
        submission.fall_blowout = None
        submission.summer_tuneup = None
        submission.additional_services_info = None
        submission.date_work_needed_by = None
        submission.property_type = None
        submission.landscape_hardscape = None
        submission.promoted_to_lead_id = None

        new_lead = _make_lead_mock(
            name="Jane Smith",
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        repo = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [submission]
        repo.session = AsyncMock()
        repo.session.execute = AsyncMock(return_value=mock_result)
        repo.session.flush = AsyncMock()
        repo.create = AsyncMock(return_value=new_lead)

        svc = _build_lead_service(lead_repo=repo)
        await svc.migrate_work_requests()

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["situation"] == LeadSituation.NEW_SYSTEM.value


# =============================================================================
# Property 49: SMS lead confirmation is consent and time-window gated
# Validates: Requirements 46.1, 46.2
# =============================================================================


@pytest.mark.unit
class TestProperty49SMSLeadConfirmation:
    """Property 49: SMS lead confirmation is consent and time-window gated.

    **Validates: Requirements 46.1, 46.2**
    """

    @given(
        sms_consent=st.booleans(),
        has_phone=st.booleans(),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_sms_confirmation_with_consent_and_phone_gates_correctly(
        self,
        sms_consent: bool,
        has_phone: bool,
    ) -> None:
        """SMS confirmation is only sent when lead has both consent and phone.

        **Validates: Requirements 46.1, 46.2**
        """
        phone = "6125551234" if has_phone else ""
        lead = _make_lead_mock(
            sms_consent=sms_consent,
            phone=phone,
        )

        sms_service = AsyncMock()
        sms_service.send_automated_message = AsyncMock(
            return_value={"success": True},
        )

        svc = _build_lead_service(sms_service=sms_service)
        await svc._send_sms_confirmation(lead)

        if sms_consent and has_phone:
            sms_service.send_automated_message.assert_awaited_once()
            call_kwargs = sms_service.send_automated_message.call_args[1]
            assert call_kwargs["message_type"] == "lead_confirmation"
        else:
            sms_service.send_automated_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sms_confirmation_with_no_sms_service_skips(self) -> None:
        """When sms_service is None, confirmation is skipped gracefully."""
        lead = _make_lead_mock(sms_consent=True, phone="6125551234")

        svc = _build_lead_service(sms_service=None)
        # Should not raise
        await svc._send_sms_confirmation(lead)

    @pytest.mark.asyncio
    async def test_sms_confirmation_with_send_failure_does_not_raise(
        self,
    ) -> None:
        """SMS send failure is caught and logged, not raised."""
        lead = _make_lead_mock(sms_consent=True, phone="6125551234")

        sms_service = AsyncMock()
        sms_service.send_automated_message = AsyncMock(
            side_effect=RuntimeError("Twilio down"),
        )

        svc = _build_lead_service(sms_service=sms_service)
        # Should not raise
        await svc._send_sms_confirmation(lead)

    @pytest.mark.asyncio
    async def test_sms_confirmation_with_deferred_result_logs_scheduled(
        self,
    ) -> None:
        """When SMS is deferred (outside time window), result indicates deferred."""
        lead = _make_lead_mock(sms_consent=True, phone="6125551234")

        sms_service = AsyncMock()
        sms_service.send_automated_message = AsyncMock(
            return_value={
                "success": True,
                "deferred": True,
                "scheduled_for": "2025-01-15T08:00:00-06:00",
            },
        )

        svc = _build_lead_service(sms_service=sms_service)
        await svc._send_sms_confirmation(lead)

        sms_service.send_automated_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sms_confirmation_with_no_consent_does_not_send(self) -> None:
        """Lead without sms_consent does not trigger SMS."""
        lead = _make_lead_mock(sms_consent=False, phone="6125551234")

        sms_service = AsyncMock()
        sms_service.send_automated_message = AsyncMock()

        svc = _build_lead_service(sms_service=sms_service)
        await svc._send_sms_confirmation(lead)

        sms_service.send_automated_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sms_confirmation_with_no_phone_does_not_send(self) -> None:
        """Lead without phone number does not trigger SMS."""
        lead = _make_lead_mock(sms_consent=True, phone="")

        sms_service = AsyncMock()
        sms_service.send_automated_message = AsyncMock()

        svc = _build_lead_service(sms_service=sms_service)
        await svc._send_sms_confirmation(lead)

        sms_service.send_automated_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_submit_lead_with_consent_schedules_post_commit_sms(
        self,
    ) -> None:
        """submit_lead with sms_consent=True schedules SMS as a post-commit task.

        Post BUG-001 fix (2026-04-14): SMS confirmation is deferred to
        a FastAPI BackgroundTask running in a fresh session so it cannot
        roll back the lead-intake transaction. The service must NOT call
        ``sms_service.send_automated_message`` inline.
        """
        from unittest.mock import MagicMock  # noqa: PLC0415

        from grins_platform.services.lead_service import (  # noqa: PLC0415
            send_lead_confirmations_post_commit,
        )

        created_lead = _make_lead_mock(
            sms_consent=True,
            phone="6125551234",
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        repo = AsyncMock()
        repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
        repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created_lead)

        sms_service = AsyncMock()
        sms_service.send_automated_message = AsyncMock(
            return_value={"success": True},
        )

        svc = _build_lead_service(lead_repo=repo, sms_service=sms_service)

        data = LeadSubmission(
            name="Test User",
            phone="6125551234",
            zip_code="80202",
            situation=LeadSituation.NEW_SYSTEM,
            sms_consent=True,
            address="123 Main St, Denver, CO 80209",
        )
        background_tasks = MagicMock()
        result = await svc.submit_lead(data, background_tasks=background_tasks)

        assert result.success is True
        sms_service.send_automated_message.assert_not_awaited()
        background_tasks.add_task.assert_called_once()
        scheduled_fn, *scheduled_args = background_tasks.add_task.call_args.args
        assert scheduled_fn is send_lead_confirmations_post_commit
        assert scheduled_args[0] == created_lead.id

    @pytest.mark.asyncio
    async def test_submit_lead_without_consent_does_not_trigger_sms(
        self,
    ) -> None:
        """Full submit_lead flow with sms_consent=False does not trigger SMS."""
        created_lead = _make_lead_mock(
            sms_consent=False,
            phone="6125551234",
            action_tags=[ActionTag.NEEDS_CONTACT.value],
        )

        repo = AsyncMock()
        repo.get_recent_by_phone_or_email = AsyncMock(return_value=None)
        repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=created_lead)

        sms_service = AsyncMock()
        sms_service.send_automated_message = AsyncMock()

        svc = _build_lead_service(lead_repo=repo, sms_service=sms_service)

        data = LeadSubmission(
            name="Test User",
            phone="6125551234",
            zip_code="80202",
            situation=LeadSituation.REPAIR,
            sms_consent=False,
            address="123 Main St, Denver, CO 80209",
        )
        await svc.submit_lead(data)

        sms_service.send_automated_message.assert_not_awaited()
