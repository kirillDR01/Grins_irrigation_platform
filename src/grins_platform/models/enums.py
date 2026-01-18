"""
Enum types for customer management models.

This module defines all enum types used in the customer management feature,
ensuring type safety and consistent values across the application.

Validates: Requirement 1.12, 2.3, 2.4
"""

from enum import Enum


class CustomerStatus(str, Enum):
    """Customer status enumeration.

    Validates: Requirement 1.12
    """

    ACTIVE = "active"
    INACTIVE = "inactive"


class LeadSource(str, Enum):
    """Lead source enumeration for marketing attribution.

    Validates: Requirement 1.9
    """

    WEBSITE = "website"
    GOOGLE = "google"
    REFERRAL = "referral"
    AD = "ad"
    WORD_OF_MOUTH = "word_of_mouth"


class SystemType(str, Enum):
    """Irrigation system type enumeration.

    Validates: Requirement 2.3
    """

    STANDARD = "standard"
    LAKE_PUMP = "lake_pump"


class PropertyType(str, Enum):
    """Property type enumeration.

    Validates: Requirement 2.4
    """

    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
