"""Tests for Pydantic schemas.

This module contains unit tests and property-based tests for schema validation,
including phone number normalization, email validation, zone count bounds,
and enum validation.

**PBT: Property 4, Property 6**
"""

from datetime import datetime
from uuid import uuid4

import pytest

from grins_platform.models.enums import (
    CustomerStatus,
    LeadSource,
    PropertyType,
    SystemType,
)
from grins_platform.schemas.customer import (
    BulkPreferencesUpdate,
    BulkUpdateResponse,
    CustomerCreate,
    CustomerFlagsUpdate,
    CustomerListParams,
    CustomerResponse,
    CustomerUpdate,
    PaginatedCustomerResponse,
    ServiceHistorySummary,
    normalize_phone,
)
from grins_platform.schemas.property import (
    PropertyCreate,
    PropertyResponse,
    PropertyUpdate,
    is_in_service_area,
)


class TestNormalizePhone:
    """Test suite for phone number normalization function.

    **Validates: Requirement 6.10**
    """

    def test_normalize_10_digit_phone(self):
        """Test normalizing a 10-digit phone number."""
        assert normalize_phone("5551234567") == "5551234567"

    def test_normalize_phone_with_dashes(self):
        """Test normalizing phone with dashes."""
        assert normalize_phone("555-123-4567") == "5551234567"

    def test_normalize_phone_with_parentheses(self):
        """Test normalizing phone with parentheses."""
        assert normalize_phone("(555) 123-4567") == "5551234567"

    def test_normalize_phone_with_spaces(self):
        """Test normalizing phone with spaces."""
        assert normalize_phone("555 123 4567") == "5551234567"

    def test_normalize_phone_with_dots(self):
        """Test normalizing phone with dots."""
        assert normalize_phone("555.123.4567") == "5551234567"

    def test_normalize_phone_with_country_code(self):
        """Test normalizing phone with US country code."""
        assert normalize_phone("1-555-123-4567") == "5551234567"
        assert normalize_phone("+1 555 123 4567") == "5551234567"

    def test_normalize_phone_mixed_format(self):
        """Test normalizing phone with mixed formatting."""
        assert normalize_phone("+1 (555) 123-4567") == "5551234567"

    def test_normalize_phone_too_short_raises_error(self):
        """Test that too short phone raises ValueError."""
        with pytest.raises(ValueError, match="Phone must be 10 digits"):
            normalize_phone("555123")

    def test_normalize_phone_too_long_raises_error(self):
        """Test that too long phone raises ValueError."""
        with pytest.raises(ValueError, match="Phone must be 10 digits"):
            normalize_phone("555123456789012")

    def test_normalize_phone_no_digits_raises_error(self):
        """Test that phone with no digits raises ValueError."""
        with pytest.raises(ValueError, match="Phone must be 10 digits"):
            normalize_phone("abc-def-ghij")


class TestPhoneNormalizationIdempotence:
    """Property-based tests for phone normalization idempotence.

    **Validates: Requirements 6.10**
    **PBT: Property 6**
    """

    @pytest.mark.parametrize(
        "phone",
        [
            "5551234567",
            "555-123-4567",
            "(555) 123-4567",
            "555.123.4567",
            "1-555-123-4567",
            "+1 (555) 123-4567",
            "  555 123 4567  ",
        ],
    )
    def test_normalize_idempotence(self, phone):
        """Test that normalize(normalize(x)) == normalize(x).

        **Validates: Requirements 6.10**
        **PBT: Property 6**
        """
        first_normalize = normalize_phone(phone)
        second_normalize = normalize_phone(first_normalize)
        assert first_normalize == second_normalize

    @pytest.mark.parametrize(
        "phone",
        [
            "5551234567",
            "1234567890",
            "9876543210",
            "0000000000",
            "9999999999",
        ],
    )
    def test_normalized_phone_is_10_digits(self, phone):
        """Test that normalized phone is always 10 digits.

        **Validates: Requirements 6.10**
        """
        result = normalize_phone(phone)
        assert len(result) == 10
        assert result.isdigit()


class TestCustomerCreate:
    """Test suite for CustomerCreate schema."""

    def test_create_with_required_fields(self):
        """Test creating customer with only required fields."""
        customer = CustomerCreate(
            first_name="John",
            last_name="Doe",
            phone="5551234567",
        )
        assert customer.first_name == "John"
        assert customer.last_name == "Doe"
        assert customer.phone == "5551234567"
        assert customer.email is None
        assert customer.sms_opt_in is False
        assert customer.email_opt_in is False

    def test_create_with_all_fields(self):
        """Test creating customer with all fields."""
        customer = CustomerCreate(
            first_name="John",
            last_name="Doe",
            phone="555-123-4567",
            email="john.doe@example.com",
            lead_source=LeadSource.WEBSITE,
            lead_source_details={"campaign": "spring2024"},
            sms_opt_in=True,
            email_opt_in=True,
        )
        assert customer.first_name == "John"
        assert customer.last_name == "Doe"
        assert customer.phone == "5551234567"  # Normalized
        assert customer.email == "john.doe@example.com"
        assert customer.lead_source == LeadSource.WEBSITE
        assert customer.sms_opt_in is True

    def test_create_strips_whitespace_from_names(self):
        """Test that whitespace is stripped from names."""
        customer = CustomerCreate(
            first_name="  John  ",
            last_name="  Doe  ",
            phone="5551234567",
        )
        assert customer.first_name == "John"
        assert customer.last_name == "Doe"

    def test_create_normalizes_phone(self):
        """Test that phone is normalized."""
        customer = CustomerCreate(
            first_name="John",
            last_name="Doe",
            phone="(555) 123-4567",
        )
        assert customer.phone == "5551234567"

    def test_create_with_invalid_phone_raises_error(self):
        """Test that invalid phone raises validation error."""
        # Short phone fails min_length validation first
        with pytest.raises(ValueError):
            CustomerCreate(
                first_name="John",
                last_name="Doe",
                phone="123",
            )

    def test_create_with_invalid_phone_format_raises_error(self):
        """Test that phone with wrong digit count raises validation error."""
        # Phone with 10+ chars but not 10 digits fails our validator
        with pytest.raises(ValueError, match="Phone must be 10 digits"):
            CustomerCreate(
                first_name="John",
                last_name="Doe",
                phone="123-456-789",  # Only 9 digits
            )

    def test_create_with_invalid_email_raises_error(self):
        """Test that invalid email raises validation error."""
        with pytest.raises(ValueError):
            CustomerCreate(
                first_name="John",
                last_name="Doe",
                phone="5551234567",
                email="not-an-email",
            )

    def test_create_with_empty_first_name_raises_error(self):
        """Test that empty first name raises validation error."""
        with pytest.raises(ValueError):
            CustomerCreate(
                first_name="",
                last_name="Doe",
                phone="5551234567",
            )

    def test_create_with_empty_last_name_raises_error(self):
        """Test that empty last name raises validation error."""
        with pytest.raises(ValueError):
            CustomerCreate(
                first_name="John",
                last_name="",
                phone="5551234567",
            )


class TestCustomerUpdate:
    """Test suite for CustomerUpdate schema."""

    def test_update_with_no_fields(self):
        """Test creating update with no fields."""
        update = CustomerUpdate()
        assert update.first_name is None
        assert update.last_name is None
        assert update.phone is None

    def test_update_with_some_fields(self):
        """Test creating update with some fields."""
        update = CustomerUpdate(
            first_name="Jane",
            status=CustomerStatus.INACTIVE,
        )
        assert update.first_name == "Jane"
        assert update.status == CustomerStatus.INACTIVE
        assert update.last_name is None

    def test_update_normalizes_phone(self):
        """Test that phone is normalized when provided."""
        update = CustomerUpdate(phone="(555) 123-4567")
        assert update.phone == "5551234567"

    def test_update_with_none_phone(self):
        """Test that None phone stays None."""
        update = CustomerUpdate(phone=None)
        assert update.phone is None


class TestCustomerFlagsUpdate:
    """Test suite for CustomerFlagsUpdate schema."""

    def test_flags_update_all_none(self):
        """Test creating flags update with all None."""
        flags = CustomerFlagsUpdate()
        assert flags.is_priority is None
        assert flags.is_red_flag is None
        assert flags.is_slow_payer is None
        assert flags.is_new_customer is None

    def test_flags_update_with_values(self):
        """Test creating flags update with values."""
        flags = CustomerFlagsUpdate(
            is_priority=True,
            is_red_flag=False,
            is_slow_payer=True,
        )
        assert flags.is_priority is True
        assert flags.is_red_flag is False
        assert flags.is_slow_payer is True
        assert flags.is_new_customer is None


class TestServiceHistorySummary:
    """Test suite for ServiceHistorySummary schema."""

    def test_service_history_summary(self):
        """Test creating service history summary."""
        summary = ServiceHistorySummary(
            total_jobs=10,
            last_service_date=datetime(2024, 1, 15),
            total_revenue=1500.50,
        )
        assert summary.total_jobs == 10
        assert summary.last_service_date == datetime(2024, 1, 15)
        assert summary.total_revenue == 1500.50

    def test_service_history_summary_no_service(self):
        """Test creating service history summary with no service."""
        summary = ServiceHistorySummary(
            total_jobs=0,
            last_service_date=None,
            total_revenue=0.0,
        )
        assert summary.total_jobs == 0
        assert summary.last_service_date is None
        assert summary.total_revenue == 0.0

    def test_service_history_negative_jobs_raises_error(self):
        """Test that negative total_jobs raises error."""
        with pytest.raises(ValueError):
            ServiceHistorySummary(
                total_jobs=-1,
                total_revenue=0.0,
            )


class TestCustomerResponse:
    """Test suite for CustomerResponse schema."""

    def test_customer_response_from_dict(self):
        """Test creating customer response from dict."""
        data = {
            "id": uuid4(),
            "first_name": "John",
            "last_name": "Doe",
            "phone": "5551234567",
            "email": "john@example.com",
            "status": "active",
            "is_priority": False,
            "is_red_flag": False,
            "is_slow_payer": False,
            "is_new_customer": True,
            "sms_opt_in": False,
            "email_opt_in": False,
            "lead_source": "website",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        response = CustomerResponse(**data)
        assert response.first_name == "John"
        assert response.status == CustomerStatus.ACTIVE
        assert response.lead_source == LeadSource.WEBSITE

    def test_customer_response_converts_string_status(self):
        """Test that string status is converted to enum."""
        data = {
            "id": uuid4(),
            "first_name": "John",
            "last_name": "Doe",
            "phone": "5551234567",
            "status": "inactive",
            "is_priority": False,
            "is_red_flag": False,
            "is_slow_payer": False,
            "is_new_customer": True,
            "sms_opt_in": False,
            "email_opt_in": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        response = CustomerResponse(**data)
        assert response.status == CustomerStatus.INACTIVE


class TestCustomerListParams:
    """Test suite for CustomerListParams schema."""

    def test_list_params_defaults(self):
        """Test default values for list params."""
        params = CustomerListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.city is None
        assert params.status is None
        assert params.sort_by == "last_name"
        assert params.sort_order == "asc"

    def test_list_params_with_filters(self):
        """Test list params with filters."""
        params = CustomerListParams(
            page=2,
            page_size=50,
            city="Eden Prairie",
            status=CustomerStatus.ACTIVE,
            is_priority=True,
            search="john",
            sort_by="created_at",
            sort_order="desc",
        )
        assert params.page == 2
        assert params.page_size == 50
        assert params.city == "Eden Prairie"
        assert params.status == CustomerStatus.ACTIVE
        assert params.is_priority is True
        assert params.search == "john"
        assert params.sort_order == "desc"

    def test_list_params_page_size_max(self):
        """Test that page_size is limited to 100."""
        with pytest.raises(ValueError):
            CustomerListParams(page_size=101)

    def test_list_params_page_min(self):
        """Test that page must be at least 1."""
        with pytest.raises(ValueError):
            CustomerListParams(page=0)

    def test_list_params_invalid_sort_order(self):
        """Test that invalid sort_order raises error."""
        with pytest.raises(ValueError):
            CustomerListParams(sort_order="invalid")


class TestPaginatedCustomerResponse:
    """Test suite for PaginatedCustomerResponse schema."""

    def test_paginated_response(self):
        """Test creating paginated response."""
        response = PaginatedCustomerResponse(
            items=[],
            total=100,
            page=1,
            page_size=20,
            total_pages=5,
        )
        assert response.total == 100
        assert response.page == 1
        assert response.total_pages == 5


class TestBulkPreferencesUpdate:
    """Test suite for BulkPreferencesUpdate schema."""

    def test_bulk_update_with_ids(self):
        """Test creating bulk update with customer IDs."""
        ids = [uuid4() for _ in range(5)]
        update = BulkPreferencesUpdate(
            customer_ids=ids,
            sms_opt_in=True,
        )
        assert len(update.customer_ids) == 5
        assert update.sms_opt_in is True
        assert update.email_opt_in is None

    def test_bulk_update_empty_ids_raises_error(self):
        """Test that empty customer_ids raises error."""
        with pytest.raises(ValueError):
            BulkPreferencesUpdate(customer_ids=[])

    def test_bulk_update_too_many_ids_raises_error(self):
        """Test that more than 1000 IDs raises error."""
        ids = [uuid4() for _ in range(1001)]
        with pytest.raises(ValueError):
            BulkPreferencesUpdate(customer_ids=ids)


class TestBulkUpdateResponse:
    """Test suite for BulkUpdateResponse schema."""

    def test_bulk_response(self):
        """Test creating bulk update response."""
        response = BulkUpdateResponse(
            updated_count=95,
            failed_count=5,
            errors=[{"id": str(uuid4()), "error": "Not found"}],
        )
        assert response.updated_count == 95
        assert response.failed_count == 5
        assert len(response.errors) == 1


class TestPropertyCreate:
    """Test suite for PropertyCreate schema."""

    def test_create_with_required_fields(self):
        """Test creating property with only required fields."""
        prop = PropertyCreate(
            address="123 Main St",
            city="Eden Prairie",
        )
        assert prop.address == "123 Main St"
        assert prop.city == "Eden Prairie"
        assert prop.state == "MN"
        assert prop.zone_count is None
        assert prop.system_type == SystemType.STANDARD
        assert prop.property_type == PropertyType.RESIDENTIAL
        assert prop.is_primary is False
        assert prop.has_dogs is False

    def test_create_with_all_fields(self):
        """Test creating property with all fields."""
        prop = PropertyCreate(
            address="456 Oak Ave",
            city="Plymouth",
            state="MN",
            zip_code="55441",
            zone_count=12,
            system_type=SystemType.LAKE_PUMP,
            property_type=PropertyType.COMMERCIAL,
            is_primary=True,
            access_instructions="Use side gate",
            gate_code="1234",
            has_dogs=True,
            special_notes="Large property",
            latitude=44.9778,
            longitude=-93.2650,
        )
        assert prop.zone_count == 12
        assert prop.system_type == SystemType.LAKE_PUMP
        assert prop.property_type == PropertyType.COMMERCIAL
        assert prop.is_primary is True
        assert prop.has_dogs is True
        assert prop.latitude == 44.9778

    def test_create_strips_whitespace(self):
        """Test that whitespace is stripped from address and city."""
        prop = PropertyCreate(
            address="  123 Main St  ",
            city="  Eden Prairie  ",
        )
        assert prop.address == "123 Main St"
        assert prop.city == "Eden Prairie"


class TestZoneCountBounds:
    """Property-based tests for zone count validation.

    **Validates: Requirement 2.2**
    **PBT: Property 4**
    """

    @pytest.mark.parametrize("zone_count", [1, 2, 10, 25, 49, 50])
    def test_valid_zone_counts_accepted(self, zone_count):
        """Test that valid zone counts (1-50) are accepted.

        **Validates: Requirement 2.2**
        **PBT: Property 4**
        """
        prop = PropertyCreate(
            address="123 Main St",
            city="Eden Prairie",
            zone_count=zone_count,
        )
        assert prop.zone_count == zone_count

    @pytest.mark.parametrize("zone_count", [0, -1, -10, 51, 100, 1000])
    def test_invalid_zone_counts_rejected(self, zone_count):
        """Test that invalid zone counts are rejected.

        **Validates: Requirement 2.2**
        **PBT: Property 4**
        """
        with pytest.raises(ValueError):
            PropertyCreate(
                address="123 Main St",
                city="Eden Prairie",
                zone_count=zone_count,
            )

    def test_zone_count_none_is_valid(self):
        """Test that None zone_count is valid.

        **Validates: Requirement 2.2**
        **PBT: Property 4**
        """
        prop = PropertyCreate(
            address="123 Main St",
            city="Eden Prairie",
            zone_count=None,
        )
        assert prop.zone_count is None


class TestPropertyUpdate:
    """Test suite for PropertyUpdate schema."""

    def test_update_with_no_fields(self):
        """Test creating update with no fields."""
        update = PropertyUpdate()
        assert update.address is None
        assert update.city is None
        assert update.zone_count is None

    def test_update_with_some_fields(self):
        """Test creating update with some fields."""
        update = PropertyUpdate(
            address="789 New St",
            zone_count=15,
        )
        assert update.address == "789 New St"
        assert update.zone_count == 15
        assert update.city is None

    def test_update_zone_count_validation(self):
        """Test that zone count validation applies to updates."""
        with pytest.raises(ValueError):
            PropertyUpdate(zone_count=0)

        with pytest.raises(ValueError):
            PropertyUpdate(zone_count=51)


class TestPropertyResponse:
    """Test suite for PropertyResponse schema."""

    def test_property_response_from_dict(self):
        """Test creating property response from dict."""
        data = {
            "id": uuid4(),
            "customer_id": uuid4(),
            "address": "123 Main St",
            "city": "Eden Prairie",
            "state": "MN",
            "zip_code": "55344",
            "zone_count": 8,
            "system_type": "standard",
            "property_type": "residential",
            "is_primary": True,
            "access_instructions": None,
            "gate_code": None,
            "has_dogs": False,
            "special_notes": None,
            "latitude": None,
            "longitude": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        response = PropertyResponse(**data)
        assert response.address == "123 Main St"
        assert response.system_type == SystemType.STANDARD
        assert response.property_type == PropertyType.RESIDENTIAL

    def test_property_response_converts_string_enums(self):
        """Test that string enums are converted."""
        data = {
            "id": uuid4(),
            "customer_id": uuid4(),
            "address": "123 Main St",
            "city": "Eden Prairie",
            "state": "MN",
            "zone_count": 8,
            "system_type": "lake_pump",
            "property_type": "commercial",
            "is_primary": False,
            "has_dogs": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        response = PropertyResponse(**data)
        assert response.system_type == SystemType.LAKE_PUMP
        assert response.property_type == PropertyType.COMMERCIAL


class TestIsInServiceArea:
    """Test suite for service area validation."""

    def test_valid_service_area_cities(self):
        """Test that valid service area cities return True."""
        assert is_in_service_area("Eden Prairie") is True
        assert is_in_service_area("Plymouth") is True
        assert is_in_service_area("Maple Grove") is True
        assert is_in_service_area("Brooklyn Park") is True
        assert is_in_service_area("Rogers") is True

    def test_service_area_case_insensitive(self):
        """Test that service area check is case insensitive."""
        assert is_in_service_area("EDEN PRAIRIE") is True
        assert is_in_service_area("eden prairie") is True
        assert is_in_service_area("Eden prairie") is True

    def test_service_area_strips_whitespace(self):
        """Test that service area check strips whitespace."""
        assert is_in_service_area("  Eden Prairie  ") is True

    def test_invalid_service_area_cities(self):
        """Test that invalid cities return False."""
        assert is_in_service_area("Los Angeles") is False
        assert is_in_service_area("New York") is False
        assert is_in_service_area("Chicago") is False


class TestEnumValidation:
    """Test suite for enum validation in schemas."""

    def test_customer_status_enum_values(self):
        """Test CustomerStatus enum values are accepted."""
        for status in CustomerStatus:
            params = CustomerListParams(status=status)
            assert params.status == status

    def test_lead_source_enum_values(self):
        """Test LeadSource enum values are accepted."""
        for source in LeadSource:
            customer = CustomerCreate(
                first_name="John",
                last_name="Doe",
                phone="5551234567",
                lead_source=source,
            )
            assert customer.lead_source == source

    def test_system_type_enum_values(self):
        """Test SystemType enum values are accepted."""
        for sys_type in SystemType:
            prop = PropertyCreate(
                address="123 Main St",
                city="Eden Prairie",
                system_type=sys_type,
            )
            assert prop.system_type == sys_type

    def test_property_type_enum_values(self):
        """Test PropertyType enum values are accepted."""
        for prop_type in PropertyType:
            prop = PropertyCreate(
                address="123 Main St",
                city="Eden Prairie",
                property_type=prop_type,
            )
            assert prop.property_type == prop_type
