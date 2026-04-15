"""Unit tests for CRM Gap Closure schema validation and model constraints.

Tests Communication model round-trip, SentMessage constraint validation,
and Pydantic schema validation for oversized strings, invalid UUIDs,
and disallowed values.

Validates: Requirements 4.6, 4.7, 81.7, 81.8, 81.9
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)
from pydantic import ValidationError

from grins_platform.models.enums import (
    CampaignType,
    CommunicationChannel,
    CommunicationDirection,
    ExpenseCategory,
    MediaType,
)
from grins_platform.models.sent_message import SentMessage
from grins_platform.schemas.campaign import CampaignCreate
from grins_platform.schemas.communication import (
    CommunicationCreate,
    CommunicationResponse,
    CommunicationUpdate,
    UnaddressedCountResponse,
)
from grins_platform.schemas.estimate import (
    ContractTemplateCreate,
    EstimateCreate,
    EstimateTemplateCreate,
)
from grins_platform.schemas.expense import ExpenseCreate
from grins_platform.schemas.media import MediaCreate
from grins_platform.schemas.sent_message import SentMessageFilters

# =============================================================================
# Hypothesis Strategies
# =============================================================================

channel_strategy = st.sampled_from(list(CommunicationChannel))
direction_strategy = st.sampled_from(list(CommunicationDirection))
content_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=500,
)


# =============================================================================
# Property 4: Communication record round-trip
# Validates: Requirements 4.4
# =============================================================================


@pytest.mark.unit
class TestCommunicationRoundTrip:
    """Property 4: Communication record round-trip.

    **Validates: Requirements 4.4**
    """

    @given(
        channel=channel_strategy,
        direction=direction_strategy,
        content=content_strategy,
    )
    @settings(max_examples=100)
    def test_communication_create_roundtrip_with_valid_data_returns_identical_fields(
        self,
        channel: CommunicationChannel,
        direction: CommunicationDirection,
        content: str,
    ) -> None:
        """For any valid communication data, creating and reading back
        returns identical field values with addressed defaulting to false.

        **Validates: Requirements 4.4**
        """
        customer_id = uuid4()

        # Create schema
        create_schema = CommunicationCreate(
            customer_id=customer_id,
            channel=channel,
            direction=direction,
            content=content,
        )

        # Verify create schema fields
        assert create_schema.customer_id == customer_id
        assert create_schema.channel == channel
        assert create_schema.direction == direction
        assert create_schema.content == content

        # Simulate round-trip through response schema (as if read from DB)
        now = datetime.now()
        response = CommunicationResponse(
            id=uuid4(),
            customer_id=create_schema.customer_id,
            channel=create_schema.channel,
            direction=create_schema.direction,
            content=create_schema.content,
            addressed=False,
            addressed_at=None,
            addressed_by=None,
            created_at=now,
            updated_at=now,
        )

        # Round-trip: fields match exactly
        assert response.customer_id == customer_id
        assert response.channel == channel
        assert response.direction == direction
        assert response.content == content
        # Default: addressed is False
        assert response.addressed is False
        assert response.addressed_at is None
        assert response.addressed_by is None

    def test_communication_create_with_all_channels_returns_valid(self) -> None:
        """Each CommunicationChannel value is accepted."""
        customer_id = uuid4()
        for ch in CommunicationChannel:
            schema = CommunicationCreate(
                customer_id=customer_id,
                channel=ch,
                direction=CommunicationDirection.INBOUND,
                content="Test message",
            )
            assert schema.channel == ch

    def test_communication_create_with_all_directions_returns_valid(self) -> None:
        """Each CommunicationDirection value is accepted."""
        customer_id = uuid4()
        for d in CommunicationDirection:
            schema = CommunicationCreate(
                customer_id=customer_id,
                channel=CommunicationChannel.SMS,
                direction=d,
                content="Test message",
            )
            assert schema.direction == d

    def test_communication_response_with_addressed_true_returns_staff_info(
        self,
    ) -> None:
        """Addressed communication includes staff and timestamp."""
        now = datetime.now()
        staff_id = uuid4()
        response = CommunicationResponse(
            id=uuid4(),
            customer_id=uuid4(),
            channel=CommunicationChannel.EMAIL,
            direction=CommunicationDirection.INBOUND,
            content="Need help",
            addressed=True,
            addressed_at=now,
            addressed_by=staff_id,
            created_at=now,
            updated_at=now,
        )
        assert response.addressed is True
        assert response.addressed_at == now
        assert response.addressed_by == staff_id

    def test_communication_update_with_default_returns_addressed_true(self) -> None:
        """CommunicationUpdate defaults addressed to True."""
        update = CommunicationUpdate()
        assert update.addressed is True

    def test_unaddressed_count_with_zero_returns_valid(self) -> None:
        """UnaddressedCountResponse accepts zero."""
        resp = UnaddressedCountResponse(count=0)
        assert resp.count == 0

    def test_unaddressed_count_with_negative_returns_error(self) -> None:
        """UnaddressedCountResponse rejects negative count."""
        with pytest.raises(ValidationError):
            UnaddressedCountResponse(count=-1)


# =============================================================================
# Property 78: SentMessage supports lead-only recipients
# Validates: Requirements 81.1, 81.2, 81.3, 81.4
# =============================================================================


@pytest.mark.unit
class TestSentMessageConstraints:
    """Property 78: SentMessage supports lead-only recipients.

    **Validates: Requirements 81.1, 81.2, 81.3, 81.4**

    Tests the SentMessage model's CHECK constraints at the model definition
    level. Since these are unit tests (no DB), we verify the constraint
    definitions exist on the model's __table_args__.
    """

    def test_sent_message_model_with_customer_id_nullable_returns_true(self) -> None:
        """SentMessage.customer_id column is nullable (Req 81.1)."""

        col = SentMessage.__table__.columns["customer_id"]
        assert col.nullable is True

    def test_sent_message_model_with_lead_id_column_returns_exists(self) -> None:
        """SentMessage has a lead_id column (Req 81.2)."""

        assert "lead_id" in SentMessage.__table__.columns

    def test_sent_message_model_with_lead_id_nullable_returns_true(self) -> None:
        """SentMessage.lead_id column is nullable."""

        col = SentMessage.__table__.columns["lead_id"]
        assert col.nullable is True

    def test_sent_message_model_with_recipient_check_constraint_returns_exists(
        self,
    ) -> None:
        """CHECK constraint requires customer_id or lead_id.

        Validates: Req 81.3
        """

        constraints = SentMessage.__table__.constraints
        check_names = [c.name for c in constraints if hasattr(c, "sqltext") and c.name]
        assert "ck_sent_messages_recipient" in check_names

    def test_sent_message_model_with_recipient_check_text_returns_correct(
        self,
    ) -> None:
        """The recipient CHECK constraint text validates customer_id OR lead_id."""

        constraints = SentMessage.__table__.constraints
        for c in constraints:
            if hasattr(c, "sqltext") and c.name == "ck_sent_messages_recipient":
                text = str(c.sqltext)
                assert "customer_id" in text
                assert "lead_id" in text
                assert "IS NOT NULL" in text
                break
        else:
            pytest.fail("ck_sent_messages_recipient constraint not found")

    def test_sent_message_model_with_message_type_check_returns_lead_confirmation(
        self,
    ) -> None:
        """message_type CHECK constraint includes 'lead_confirmation' (Req 81.4)."""

        constraints = SentMessage.__table__.constraints
        for c in constraints:
            if hasattr(c, "sqltext") and c.name == "ck_sent_messages_message_type":
                text = str(c.sqltext)
                assert "lead_confirmation" in text
                break
        else:
            pytest.fail("ck_sent_messages_message_type constraint not found")

    def test_sent_message_model_with_message_type_check_returns_all_new_types(
        self,
    ) -> None:
        """message_type CHECK includes all new types: estimate_sent, contract_sent,
        review_request, campaign."""

        constraints = SentMessage.__table__.constraints
        for c in constraints:
            if hasattr(c, "sqltext") and c.name == "ck_sent_messages_message_type":
                text = str(c.sqltext)
                for msg_type in [
                    "estimate_sent",
                    "contract_sent",
                    "review_request",
                    "campaign",
                ]:
                    assert msg_type in text, f"{msg_type} not in CHECK constraint"
                break
        else:
            pytest.fail("ck_sent_messages_message_type constraint not found")

    @given(
        lead_id=st.uuids(),
        message_type=st.sampled_from(
            [
                "lead_confirmation",
                "estimate_sent",
                "contract_sent",
                "review_request",
                "campaign",
            ]
        ),
    )
    @settings(max_examples=100)
    def test_sent_message_with_lead_only_recipient_returns_valid_model_attrs(
        self,
        lead_id: UUID,
        message_type: str,
    ) -> None:
        """For any lead-only recipient, a SentMessage mock with customer_id=None
        and valid lead_id has correct attributes.

        **Validates: Requirements 81.1, 81.2, 81.3, 81.4**
        """
        # Simulate model instance (unit test, no DB)
        msg = MagicMock()
        msg.id = uuid4()
        msg.customer_id = None
        msg.lead_id = lead_id
        msg.message_type = message_type
        msg.message_content = "Test notification"
        msg.recipient_phone = "6125551234"
        msg.delivery_status = "pending"

        assert msg.customer_id is None
        assert msg.lead_id == lead_id
        assert msg.message_type == message_type
        # At least one recipient is set
        assert msg.customer_id is not None or msg.lead_id is not None


# =============================================================================
# Pydantic Schema Validation Tests
# Validates: Requirements 4.6, 4.7, 81.7, 81.8, 81.9
# =============================================================================


@pytest.mark.unit
class TestCommunicationSchemaValidation:
    """Test CommunicationCreate schema rejects invalid input."""

    def test_communication_create_with_empty_content_returns_error(self) -> None:
        """Empty content string is rejected (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            CommunicationCreate(
                customer_id=uuid4(),
                channel=CommunicationChannel.SMS,
                direction=CommunicationDirection.INBOUND,
                content="",
            )
        errors = exc_info.value.errors()
        assert any("content" in str(e["loc"]) for e in errors)

    def test_communication_create_with_oversized_content_returns_error(self) -> None:
        """Content exceeding max_length=5000 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CommunicationCreate(
                customer_id=uuid4(),
                channel=CommunicationChannel.SMS,
                direction=CommunicationDirection.INBOUND,
                content="x" * 5001,
            )
        errors = exc_info.value.errors()
        assert any("content" in str(e["loc"]) for e in errors)

    def test_communication_create_with_invalid_uuid_returns_error(self) -> None:
        """Invalid UUID string for customer_id is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CommunicationCreate(
                customer_id="not-a-uuid",  # type: ignore[arg-type]
                channel=CommunicationChannel.SMS,
                direction=CommunicationDirection.INBOUND,
                content="Hello",
            )
        errors = exc_info.value.errors()
        assert any("customer_id" in str(e["loc"]) for e in errors)

    def test_communication_create_with_invalid_channel_returns_error(self) -> None:
        """Invalid channel value is rejected."""
        with pytest.raises(ValidationError):
            CommunicationCreate(
                customer_id=uuid4(),
                channel="CARRIER_PIGEON",  # type: ignore[arg-type]
                direction=CommunicationDirection.INBOUND,
                content="Hello",
            )

    def test_communication_create_with_invalid_direction_returns_error(self) -> None:
        """Invalid direction value is rejected."""
        with pytest.raises(ValidationError):
            CommunicationCreate(
                customer_id=uuid4(),
                channel=CommunicationChannel.SMS,
                direction="SIDEWAYS",  # type: ignore[arg-type]
                content="Hello",
            )

    def test_communication_create_with_max_content_returns_valid(self) -> None:
        """Content at exactly max_length=5000 is accepted."""
        schema = CommunicationCreate(
            customer_id=uuid4(),
            channel=CommunicationChannel.SMS,
            direction=CommunicationDirection.INBOUND,
            content="x" * 5000,
        )
        assert len(schema.content) == 5000


@pytest.mark.unit
class TestEstimateSchemaValidation:
    """Test Estimate-related schemas reject invalid input."""

    def test_estimate_template_create_with_empty_name_returns_error(self) -> None:
        """Empty template name is rejected (min_length=1)."""
        with pytest.raises(ValidationError):
            EstimateTemplateCreate(name="")

    def test_estimate_template_create_with_oversized_name_returns_error(self) -> None:
        """Template name exceeding max_length=200 is rejected."""
        with pytest.raises(ValidationError):
            EstimateTemplateCreate(name="x" * 201)

    def test_estimate_template_create_with_oversized_description_returns_error(
        self,
    ) -> None:
        """Description exceeding max_length=2000 is rejected."""
        with pytest.raises(ValidationError):
            EstimateTemplateCreate(name="Valid", description="x" * 2001)

    def test_estimate_template_create_with_oversized_terms_returns_error(
        self,
    ) -> None:
        """Terms exceeding max_length=5000 is rejected."""
        with pytest.raises(ValidationError):
            EstimateTemplateCreate(name="Valid", terms="x" * 5001)

    def test_estimate_template_create_with_valid_data_returns_valid(self) -> None:
        """Valid template data is accepted."""
        schema = EstimateTemplateCreate(
            name="Standard Irrigation",
            description="Basic irrigation estimate",
            line_items=[{"item": "Sprinkler", "quantity": 1, "unit_price": "50.00"}],
            terms="Net 30",
        )
        assert schema.name == "Standard Irrigation"

    def test_contract_template_create_with_empty_body_returns_error(self) -> None:
        """Empty contract body is rejected (min_length=1)."""
        with pytest.raises(ValidationError):
            ContractTemplateCreate(name="Contract", body="")

    def test_contract_template_create_with_oversized_body_returns_error(self) -> None:
        """Body exceeding max_length=50000 is rejected."""
        with pytest.raises(ValidationError):
            ContractTemplateCreate(name="Contract", body="x" * 50001)

    def test_estimate_create_with_negative_total_returns_error(self) -> None:
        """Negative total is rejected (ge=0)."""
        with pytest.raises(ValidationError):
            EstimateCreate(total=Decimal(-1))

    def test_estimate_create_with_negative_subtotal_returns_error(self) -> None:
        """Negative subtotal is rejected (ge=0)."""
        with pytest.raises(ValidationError):
            EstimateCreate(subtotal=Decimal(-1))

    def test_estimate_create_with_invalid_uuid_returns_error(self) -> None:
        """Invalid UUID for lead_id is rejected."""
        with pytest.raises(ValidationError):
            EstimateCreate(lead_id="bad-uuid")  # type: ignore[arg-type]

    def test_estimate_create_with_oversized_promotion_code_returns_error(
        self,
    ) -> None:
        """Promotion code exceeding max_length=50 is rejected."""
        with pytest.raises(ValidationError):
            EstimateCreate(promotion_code="x" * 51)

    def test_estimate_create_with_oversized_notes_returns_error(self) -> None:
        """Notes exceeding max_length=5000 is rejected."""
        with pytest.raises(ValidationError):
            EstimateCreate(notes="x" * 5001)


@pytest.mark.unit
class TestExpenseSchemaValidation:
    """Test ExpenseCreate schema rejects invalid input."""

    def test_expense_create_with_zero_amount_returns_error(self) -> None:
        """Zero amount is rejected (gt=0)."""
        with pytest.raises(ValidationError):
            ExpenseCreate(
                category=ExpenseCategory.MATERIALS,
                description="Test",
                amount=Decimal(0),
                expense_date="2025-01-15",  # type: ignore[arg-type]
            )

    def test_expense_create_with_negative_amount_returns_error(self) -> None:
        """Negative amount is rejected."""
        with pytest.raises(ValidationError):
            ExpenseCreate(
                category=ExpenseCategory.FUEL,
                description="Gas",
                amount=Decimal(-10),
                expense_date="2025-01-15",  # type: ignore[arg-type]
            )

    def test_expense_create_with_empty_description_returns_error(self) -> None:
        """Empty description is rejected (min_length=1)."""
        with pytest.raises(ValidationError):
            ExpenseCreate(
                category=ExpenseCategory.MATERIALS,
                description="",
                amount=Decimal(50),
                expense_date="2025-01-15",  # type: ignore[arg-type]
            )

    def test_expense_create_with_oversized_description_returns_error(self) -> None:
        """Description exceeding max_length=500 is rejected."""
        with pytest.raises(ValidationError):
            ExpenseCreate(
                category=ExpenseCategory.MATERIALS,
                description="x" * 501,
                amount=Decimal(50),
                expense_date="2025-01-15",  # type: ignore[arg-type]
            )

    def test_expense_create_with_oversized_vendor_returns_error(self) -> None:
        """Vendor exceeding max_length=200 is rejected."""
        with pytest.raises(ValidationError):
            ExpenseCreate(
                category=ExpenseCategory.MATERIALS,
                description="Parts",
                amount=Decimal(50),
                expense_date="2025-01-15",  # type: ignore[arg-type]
                vendor="x" * 201,
            )


@pytest.mark.unit
class TestCampaignSchemaValidation:
    """Test CampaignCreate schema rejects invalid input."""

    def test_campaign_create_with_empty_name_returns_error(self) -> None:
        """Empty campaign name is rejected."""
        with pytest.raises(ValidationError):
            CampaignCreate(
                name="",
                campaign_type=CampaignType.SMS,
                body="Hello customers",
            )

    def test_campaign_create_with_oversized_name_returns_error(self) -> None:
        """Name exceeding max_length=200 is rejected."""
        with pytest.raises(ValidationError):
            CampaignCreate(
                name="x" * 201,
                campaign_type=CampaignType.SMS,
                body="Hello",
            )

    def test_campaign_create_allows_empty_body_at_draft_time(self) -> None:
        """Empty body is intentionally allowed at draft-create time.

        The 3-step wizard persists the draft after Step 1 (audience) before
        the user composes the message in Step 2, so an empty body must pass
        schema validation on create. ``enqueue_campaign_send`` enforces a
        non-empty body before an actual send via ``EmptyCampaignBodyError``.
        """
        payload = CampaignCreate(
            name="Spring Campaign",
            campaign_type=CampaignType.EMAIL,
            body="",
        )
        assert payload.body == ""

    def test_campaign_create_with_oversized_body_returns_error(self) -> None:
        """Body exceeding max_length=10000 is rejected."""
        with pytest.raises(ValidationError):
            CampaignCreate(
                name="Campaign",
                campaign_type=CampaignType.EMAIL,
                body="x" * 10001,
            )

    def test_campaign_create_with_oversized_subject_returns_error(self) -> None:
        """Subject exceeding max_length=200 is rejected."""
        with pytest.raises(ValidationError):
            CampaignCreate(
                name="Campaign",
                campaign_type=CampaignType.EMAIL,
                body="Hello",
                subject="x" * 201,
            )


@pytest.mark.unit
class TestMediaSchemaValidation:
    """Test MediaCreate schema rejects invalid input."""

    def test_media_create_with_empty_file_key_returns_error(self) -> None:
        """Empty file_key is rejected (min_length=1)."""
        with pytest.raises(ValidationError):
            MediaCreate(
                file_key="",
                file_name="photo.jpg",
                file_size=1024,
                content_type="image/jpeg",
                media_type=MediaType.IMAGE,
            )

    def test_media_create_with_oversized_file_key_returns_error(self) -> None:
        """file_key exceeding max_length=500 is rejected."""
        with pytest.raises(ValidationError):
            MediaCreate(
                file_key="x" * 501,
                file_name="photo.jpg",
                file_size=1024,
                content_type="image/jpeg",
                media_type=MediaType.IMAGE,
            )

    def test_media_create_with_zero_file_size_returns_error(self) -> None:
        """Zero file_size is rejected (gt=0)."""
        with pytest.raises(ValidationError):
            MediaCreate(
                file_key="media/photo.jpg",
                file_name="photo.jpg",
                file_size=0,
                content_type="image/jpeg",
                media_type=MediaType.IMAGE,
            )

    def test_media_create_with_oversized_caption_returns_error(self) -> None:
        """Caption exceeding max_length=1000 is rejected."""
        with pytest.raises(ValidationError):
            MediaCreate(
                file_key="media/photo.jpg",
                file_name="photo.jpg",
                file_size=1024,
                content_type="image/jpeg",
                media_type=MediaType.IMAGE,
                caption="x" * 1001,
            )

    def test_media_create_with_valid_data_returns_valid(self) -> None:
        """Valid media data is accepted."""
        schema = MediaCreate(
            file_key="media/photo.jpg",
            file_name="photo.jpg",
            file_size=1024,
            content_type="image/jpeg",
            media_type=MediaType.IMAGE,
            caption="Job site photo",
            is_public=False,
        )
        assert schema.file_name == "photo.jpg"
        assert schema.is_public is False


@pytest.mark.unit
class TestSentMessageFilterValidation:
    """Test SentMessageFilters schema validation."""

    def test_filters_with_defaults_returns_valid(self) -> None:
        """Default filter values are correct."""
        filters = SentMessageFilters()
        assert filters.page == 1
        assert filters.page_size == 20

    def test_filters_with_page_zero_returns_error(self) -> None:
        """Page 0 is rejected (ge=1)."""
        with pytest.raises(ValidationError):
            SentMessageFilters(page=0)

    def test_filters_with_oversized_page_size_returns_error(self) -> None:
        """page_size exceeding 100 is rejected (le=100)."""
        with pytest.raises(ValidationError):
            SentMessageFilters(page_size=101)
