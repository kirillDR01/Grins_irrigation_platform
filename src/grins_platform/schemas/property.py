"""
Property Pydantic schemas for request/response validation.

This module defines all Pydantic schemas for property-related API operations,
including creation, updates, and responses.

Validates: Requirement 2.2, 2.3, 2.4, 2.8-2.11
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from grins_platform.models.enums import PropertyType, SystemType

# Service area cities for Twin Cities metro
SERVICE_AREA_CITIES: set[str] = {
    "eden prairie",
    "plymouth",
    "maple grove",
    "brooklyn park",
    "rogers",
    "minnetonka",
    "wayzata",
    "hopkins",
    "st. louis park",
    "golden valley",
    "new hope",
    "crystal",
    "robbinsdale",
    "champlin",
    "corcoran",
    "medina",
    "orono",
    "minnetrista",
    "bloomington",
    "edina",
    "richfield",
    "brooklyn center",
    "fridley",
    "columbia heights",
    "st. anthony",
    "roseville",
    "lauderdale",
    "falcon heights",
    "maplewood",
    "north st. paul",
    "oakdale",
    "woodbury",
    "cottage grove",
    "south st. paul",
    "west st. paul",
    "mendota heights",
    "eagan",
    "burnsville",
    "savage",
    "prior lake",
    "shakopee",
    "chanhassen",
    "chaska",
    "victoria",
    "excelsior",
    "shorewood",
    "tonka bay",
    "deephaven",
    "woodland",
    "greenwood",
    "long lake",
    "hamel",
    "osseo",
    "dayton",
    "anoka",
    "ramsey",
    "andover",
    "ham lake",
    "blaine",
    "coon rapids",
    "spring lake park",
    "mounds view",
    "shoreview",
    "arden hills",
    "new brighton",
    "st. paul",
    "minneapolis",
}


def is_in_service_area(city: str) -> bool:
    """Check if a city is within the service area.

    Args:
        city: City name to check

    Returns:
        True if city is in service area, False otherwise
    """
    return city.lower().strip() in SERVICE_AREA_CITIES


class PropertyCreate(BaseModel):
    """Schema for creating a new property.

    Validates: Requirement 2.2, 2.3, 2.4, 2.8-2.11
    """

    address: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Street address",
    )
    city: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="City name",
    )
    state: str = Field(
        default="MN",
        max_length=50,
        description="State abbreviation (default: MN)",
    )
    zip_code: str | None = Field(
        default=None,
        max_length=20,
        description="ZIP code",
    )
    zone_count: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="Number of irrigation zones (1-50)",
    )
    system_type: SystemType = Field(
        default=SystemType.STANDARD,
        description="Type of irrigation system",
    )
    property_type: PropertyType = Field(
        default=PropertyType.RESIDENTIAL,
        description="Type of property",
    )
    is_primary: bool = Field(
        default=False,
        description="Whether this is the customer's primary property",
    )
    access_instructions: str | None = Field(
        default=None,
        description="Special entry instructions",
    )
    gate_code: str | None = Field(
        default=None,
        max_length=50,
        description="Gate access code",
    )
    has_dogs: bool = Field(
        default=False,
        description="Safety flag for field technicians",
    )
    special_notes: str | None = Field(
        default=None,
        description="Additional notes about the property",
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="GPS latitude for route optimization",
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="GPS longitude for route optimization",
    )

    @field_validator("address", "city")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace."""
        return v.strip()

    @field_validator("city")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def validate_city(cls, v: str) -> str:
        """Validate city format.

        Note: We don't reject cities outside service area, but the service
        layer may log a warning. This allows flexibility for edge cases.

        Validates: Requirement 2.11
        """
        # Just ensure it's properly formatted
        return v.strip()


class PropertyUpdate(BaseModel):
    """Schema for updating an existing property.

    All fields are optional - only provided fields will be updated.

    Validates: Requirement 2.2, 2.3, 2.4, 2.8-2.11
    """

    address: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Street address",
    )
    city: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="City name",
    )
    state: str | None = Field(
        default=None,
        max_length=50,
        description="State abbreviation",
    )
    zip_code: str | None = Field(
        default=None,
        max_length=20,
        description="ZIP code",
    )
    zone_count: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="Number of irrigation zones (1-50)",
    )
    system_type: SystemType | None = Field(
        default=None,
        description="Type of irrigation system",
    )
    property_type: PropertyType | None = Field(
        default=None,
        description="Type of property",
    )
    access_instructions: str | None = Field(
        default=None,
        description="Special entry instructions",
    )
    gate_code: str | None = Field(
        default=None,
        max_length=50,
        description="Gate access code",
    )
    has_dogs: bool | None = Field(
        default=None,
        description="Safety flag for field technicians",
    )
    special_notes: str | None = Field(
        default=None,
        description="Additional notes about the property",
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="GPS latitude for route optimization",
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="GPS longitude for route optimization",
    )

    @field_validator("address", "city")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        """Strip leading/trailing whitespace if provided."""
        if v is None:
            return None
        return v.strip()


class PropertyResponse(BaseModel):
    """Schema for property response data.

    Validates: Requirement 2.5
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique property identifier")
    customer_id: UUID = Field(..., description="Owning customer's ID")
    address: str = Field(..., description="Street address")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State abbreviation")
    zip_code: str | None = Field(default=None, description="ZIP code")
    zone_count: int | None = Field(
        default=None,
        description="Number of irrigation zones",
    )
    system_type: SystemType = Field(..., description="Type of irrigation system")
    property_type: PropertyType = Field(..., description="Type of property")
    is_primary: bool = Field(..., description="Primary property flag")
    access_instructions: str | None = Field(
        default=None,
        description="Special entry instructions",
    )
    gate_code: str | None = Field(default=None, description="Gate access code")
    has_dogs: bool = Field(..., description="Safety flag for dogs")
    special_notes: str | None = Field(
        default=None,
        description="Additional notes",
    )
    latitude: float | None = Field(default=None, description="GPS latitude")
    longitude: float | None = Field(default=None, description="GPS longitude")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last update timestamp")

    @field_validator("system_type", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_system_type(cls, v: str | SystemType) -> SystemType:
        """Convert string system_type to enum if needed."""
        if isinstance(v, str):
            return SystemType(v)
        return v  # type: ignore[return-value,unreachable]

    @field_validator("property_type", mode="before")  # type: ignore[misc,untyped-decorator]
    @classmethod
    def convert_property_type(cls, v: str | PropertyType) -> PropertyType:
        """Convert string property_type to enum if needed."""
        if isinstance(v, str):
            return PropertyType(v)
        return v  # type: ignore[return-value,unreachable]
