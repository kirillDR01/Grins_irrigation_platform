"""Tests for SQLAlchemy models."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from grins_platform.models import (
    Customer,
    CustomerStatus,
    LeadSource,
    Property,
    PropertyType,
    SystemType,
)


class TestCustomerStatus:
    """Test suite for CustomerStatus enum."""

    def test_active_value(self) -> None:
        """Test active status value."""
        assert CustomerStatus.ACTIVE.value == "active"

    def test_inactive_value(self) -> None:
        """Test inactive status value."""
        assert CustomerStatus.INACTIVE.value == "inactive"

    def test_enum_from_string(self) -> None:
        """Test creating enum from string value."""
        assert CustomerStatus("active") == CustomerStatus.ACTIVE
        assert CustomerStatus("inactive") == CustomerStatus.INACTIVE


class TestLeadSource:
    """Test suite for LeadSource enum."""

    def test_all_values(self) -> None:
        """Test all lead source values."""
        assert LeadSource.WEBSITE.value == "website"
        assert LeadSource.GOOGLE.value == "google"
        assert LeadSource.REFERRAL.value == "referral"
        assert LeadSource.AD.value == "ad"
        assert LeadSource.WORD_OF_MOUTH.value == "word_of_mouth"


class TestSystemType:
    """Test suite for SystemType enum."""

    def test_standard_value(self) -> None:
        """Test standard system type value."""
        assert SystemType.STANDARD.value == "standard"

    def test_lake_pump_value(self) -> None:
        """Test lake pump system type value."""
        assert SystemType.LAKE_PUMP.value == "lake_pump"


class TestPropertyType:
    """Test suite for PropertyType enum."""

    def test_residential_value(self) -> None:
        """Test residential property type value."""
        assert PropertyType.RESIDENTIAL.value == "residential"

    def test_commercial_value(self) -> None:
        """Test commercial property type value."""
        assert PropertyType.COMMERCIAL.value == "commercial"


class TestCustomerModel:
    """Test suite for Customer model."""

    def test_customer_tablename(self) -> None:
        """Test customer table name."""
        assert Customer.__tablename__ == "customers"

    def test_customer_full_name(self) -> None:
        """Test full_name property."""
        customer = Customer()
        customer.first_name = "John"
        customer.last_name = "Doe"
        assert customer.full_name == "John Doe"

    def test_customer_status_enum_property(self) -> None:
        """Test status_enum property."""
        customer = Customer()
        customer.status = "active"
        assert customer.status_enum == CustomerStatus.ACTIVE

        customer.status = "inactive"
        assert customer.status_enum == CustomerStatus.INACTIVE

    def test_customer_lead_source_enum_property(self) -> None:
        """Test lead_source_enum property."""
        customer = Customer()
        customer.lead_source = None
        assert customer.lead_source_enum is None

        customer.lead_source = "website"
        assert customer.lead_source_enum == LeadSource.WEBSITE

    def test_customer_soft_delete(self) -> None:
        """Test soft_delete method."""
        customer = Customer()
        customer.is_deleted = False
        customer.deleted_at = None

        customer.soft_delete()

        assert customer.is_deleted is True
        assert customer.deleted_at is not None
        assert isinstance(customer.deleted_at, datetime)

    def test_customer_restore(self) -> None:
        """Test restore method."""
        customer = Customer()
        customer.is_deleted = True
        customer.deleted_at = datetime.now()

        customer.restore()

        assert customer.is_deleted is False
        assert customer.deleted_at is None

    def test_customer_update_communication_preferences_sms(self) -> None:
        """Test updating SMS opt-in preference."""
        customer = Customer()
        customer.sms_opt_in = False
        customer.email_opt_in = False
        customer.communication_preferences_updated_at = None

        customer.update_communication_preferences(sms_opt_in=True)

        assert customer.sms_opt_in is True
        assert customer.email_opt_in is False
        assert customer.communication_preferences_updated_at is not None

    def test_customer_update_communication_preferences_email(self) -> None:
        """Test updating email opt-in preference."""
        customer = Customer()
        customer.sms_opt_in = False
        customer.email_opt_in = False
        customer.communication_preferences_updated_at = None

        customer.update_communication_preferences(email_opt_in=True)

        assert customer.sms_opt_in is False
        assert customer.email_opt_in is True
        assert customer.communication_preferences_updated_at is not None

    def test_customer_update_communication_preferences_no_change(self) -> None:
        """Test that timestamp is not updated when no change occurs."""
        customer = Customer()
        customer.sms_opt_in = True
        customer.email_opt_in = True
        customer.communication_preferences_updated_at = None

        # Same values - no change
        customer.update_communication_preferences(sms_opt_in=True, email_opt_in=True)

        assert customer.communication_preferences_updated_at is None

    def test_customer_repr(self) -> None:
        """Test customer string representation."""
        customer = Customer()
        customer.id = UUID("12345678-1234-5678-1234-567812345678")
        customer.first_name = "John"
        customer.last_name = "Doe"
        customer.phone = "5551234567"
        customer.status = "active"

        repr_str = repr(customer)
        assert "Customer" in repr_str
        assert "John Doe" in repr_str
        assert "5551234567" in repr_str
        assert "active" in repr_str


class TestPropertyModel:
    """Test suite for Property model."""

    def test_property_tablename(self) -> None:
        """Test property table name."""
        assert Property.__tablename__ == "properties"

    def test_property_system_type_enum_property(self) -> None:
        """Test system_type_enum property."""
        prop = Property()
        prop.system_type = "standard"
        assert prop.system_type_enum == SystemType.STANDARD

        prop.system_type = "lake_pump"
        assert prop.system_type_enum == SystemType.LAKE_PUMP

    def test_property_property_type_enum_property(self) -> None:
        """Test property_type_enum property."""
        prop = Property()
        prop.property_type = "residential"
        assert prop.property_type_enum == PropertyType.RESIDENTIAL

        prop.property_type = "commercial"
        assert prop.property_type_enum == PropertyType.COMMERCIAL

    def test_property_full_address_without_zip(self) -> None:
        """Test full_address property without zip code."""
        prop = Property()
        prop.address = "123 Main St"
        prop.city = "Eden Prairie"
        prop.state = "MN"
        prop.zip_code = None

        assert prop.full_address == "123 Main St, Eden Prairie, MN"

    def test_property_full_address_with_zip(self) -> None:
        """Test full_address property with zip code."""
        prop = Property()
        prop.address = "123 Main St"
        prop.city = "Eden Prairie"
        prop.state = "MN"
        prop.zip_code = "55344"

        assert prop.full_address == "123 Main St, Eden Prairie, MN, 55344"

    def test_property_has_coordinates_true(self) -> None:
        """Test has_coordinates when coordinates are set."""
        prop = Property()
        prop.latitude = Decimal("44.8547")
        prop.longitude = Decimal("-93.4708")

        assert prop.has_coordinates is True

    def test_property_has_coordinates_false_no_lat(self) -> None:
        """Test has_coordinates when latitude is missing."""
        prop = Property()
        prop.latitude = None
        prop.longitude = Decimal("-93.4708")

        assert prop.has_coordinates is False

    def test_property_has_coordinates_false_no_lon(self) -> None:
        """Test has_coordinates when longitude is missing."""
        prop = Property()
        prop.latitude = Decimal("44.8547")
        prop.longitude = None

        assert prop.has_coordinates is False

    def test_property_has_coordinates_false_both_missing(self) -> None:
        """Test has_coordinates when both coordinates are missing."""
        prop = Property()
        prop.latitude = None
        prop.longitude = None

        assert prop.has_coordinates is False

    def test_property_repr(self) -> None:
        """Test property string representation."""
        prop = Property()
        prop.id = UUID("12345678-1234-5678-1234-567812345678")
        prop.address = "123 Main St"
        prop.city = "Eden Prairie"
        prop.zone_count = 8

        repr_str = repr(prop)
        assert "Property" in repr_str
        assert "123 Main St" in repr_str
        assert "Eden Prairie" in repr_str
        assert "8" in repr_str
