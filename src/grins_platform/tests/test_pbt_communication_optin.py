"""Property-based tests for communication opt-in defaults.

This module contains property-based tests verifying that new customers
always default to opted-out for both SMS and email communications.

**Validates: Requirements 5.1, 5.2**
**PBT: Property 5**
"""

from __future__ import annotations

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import LeadSource
from grins_platform.schemas.customer import CustomerCreate


# Custom strategies for generating valid customer data
def valid_name_strategy() -> st.SearchStrategy[str]:
    """Generate valid customer names (1-100 chars, non-empty after strip)."""
    return st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N", "Zs"),
            whitelist_characters="-'.",
        ),
        min_size=1,
        max_size=100,
    ).filter(lambda x: len(x.strip()) > 0)


def valid_phone_strategy() -> st.SearchStrategy[str]:
    """Generate valid 10-digit phone numbers in various formats."""
    # Generate exactly 10 digits
    digits = st.text(
        alphabet="0123456789",
        min_size=10,
        max_size=10,
    )

    # Optionally format with common separators
    return digits.map(lambda d: d)  # Return raw digits for simplicity


def valid_email_strategy() -> st.SearchStrategy[str | None]:
    """Generate valid email addresses or None."""
    # Simple valid email pattern
    local_part = st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1,
        max_size=20,
    ).filter(lambda x: len(x) > 0)

    domain = st.sampled_from([
        "example.com",
        "test.org",
        "email.net",
        "company.io",
    ])

    email = st.builds(
        lambda local, dom: f"{local}@{dom}",
        local_part,
        domain,
    )

    return st.one_of(st.none(), email)


def lead_source_strategy() -> st.SearchStrategy[LeadSource | None]:
    """Generate valid lead source values or None."""
    return st.one_of(
        st.none(),
        st.sampled_from(list(LeadSource)),
    )


@pytest.mark.unit
class TestCommunicationOptInDefaults:
    """Property-based tests for communication opt-in defaults.

    **Validates: Requirements 5.1, 5.2**
    **PBT: Property 5**

    Property 5: Communication Opt-In Default
    For any newly created customer C, C.sms_opt_in = false AND C.email_opt_in = false
    """

    @given(
        first_name=valid_name_strategy(),
        last_name=valid_name_strategy(),
        phone=valid_phone_strategy(),
    )
    @settings(max_examples=100, deadline=None)
    def test_new_customer_defaults_to_opted_out_for_sms(
        self,
        first_name: str,
        last_name: str,
        phone: str,
    ) -> None:
        """Test that new customers default to opted-out for SMS.

        **Validates: Requirement 5.1**
        **PBT: Property 5**

        For any valid customer creation data without explicit sms_opt_in,
        the resulting customer should have sms_opt_in = False.
        """
        customer = CustomerCreate(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
        )

        assert customer.sms_opt_in is False, (
            f"Expected sms_opt_in=False for new customer, "
            f"got sms_opt_in={customer.sms_opt_in}"
        )

    @given(
        first_name=valid_name_strategy(),
        last_name=valid_name_strategy(),
        phone=valid_phone_strategy(),
    )
    @settings(max_examples=100, deadline=None)
    def test_new_customer_defaults_to_opted_out_for_email(
        self,
        first_name: str,
        last_name: str,
        phone: str,
    ) -> None:
        """Test that new customers default to opted-out for email.

        **Validates: Requirement 5.2**
        **PBT: Property 5**

        For any valid customer creation data without explicit email_opt_in,
        the resulting customer should have email_opt_in = False.
        """
        customer = CustomerCreate(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
        )

        assert customer.email_opt_in is False, (
            f"Expected email_opt_in=False for new customer, "
            f"got email_opt_in={customer.email_opt_in}"
        )

    @given(
        first_name=valid_name_strategy(),
        last_name=valid_name_strategy(),
        phone=valid_phone_strategy(),
        email=valid_email_strategy(),
        lead_source=lead_source_strategy(),
    )
    @settings(max_examples=100, deadline=None)
    def test_new_customer_defaults_to_opted_out_for_both_sms_and_email(
        self,
        first_name: str,
        last_name: str,
        phone: str,
        email: str | None,
        lead_source: LeadSource | None,
    ) -> None:
        """Test that new customers default to opted-out for both SMS and email.

        **Validates: Requirements 5.1, 5.2**
        **PBT: Property 5**

        For any valid customer creation data (with various optional fields)
        without explicit opt-in settings, both sms_opt_in and email_opt_in
        should default to False.
        """
        customer = CustomerCreate(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            lead_source=lead_source,
        )

        assert customer.sms_opt_in is False, (
            f"Expected sms_opt_in=False for new customer with "
            f"email={email}, lead_source={lead_source}, "
            f"got sms_opt_in={customer.sms_opt_in}"
        )
        assert customer.email_opt_in is False, (
            f"Expected email_opt_in=False for new customer with "
            f"email={email}, lead_source={lead_source}, "
            f"got email_opt_in={customer.email_opt_in}"
        )

    @given(
        first_name=valid_name_strategy(),
        last_name=valid_name_strategy(),
        phone=valid_phone_strategy(),
    )
    @settings(max_examples=50, deadline=None)
    def test_explicit_opt_in_true_is_respected(
        self,
        first_name: str,
        last_name: str,
        phone: str,
    ) -> None:
        """Test that explicit opt-in=True is respected when provided.

        **Validates: Requirements 5.3, 5.4**

        When a customer explicitly sets opt-in to True, that value
        should be preserved (not overridden by defaults).
        """
        customer = CustomerCreate(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            sms_opt_in=True,
            email_opt_in=True,
        )

        assert customer.sms_opt_in is True, (
            f"Expected sms_opt_in=True when explicitly set, "
            f"got sms_opt_in={customer.sms_opt_in}"
        )
        assert customer.email_opt_in is True, (
            f"Expected email_opt_in=True when explicitly set, "
            f"got email_opt_in={customer.email_opt_in}"
        )

    @given(
        first_name=valid_name_strategy(),
        last_name=valid_name_strategy(),
        phone=valid_phone_strategy(),
    )
    @settings(max_examples=50, deadline=None)
    def test_explicit_opt_in_false_is_respected(
        self,
        first_name: str,
        last_name: str,
        phone: str,
    ) -> None:
        """Test that explicit opt-in=False is respected when provided.

        **Validates: Requirements 5.3, 5.4**

        When a customer explicitly sets opt-in to False, that value
        should be preserved (same as default, but explicitly set).
        """
        customer = CustomerCreate(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            sms_opt_in=False,
            email_opt_in=False,
        )

        assert customer.sms_opt_in is False, (
            f"Expected sms_opt_in=False when explicitly set, "
            f"got sms_opt_in={customer.sms_opt_in}"
        )
        assert customer.email_opt_in is False, (
            f"Expected email_opt_in=False when explicitly set, "
            f"got email_opt_in={customer.email_opt_in}"
        )

    @given(
        first_name=valid_name_strategy(),
        last_name=valid_name_strategy(),
        phone=valid_phone_strategy(),
        sms_opt_in=st.booleans(),
        email_opt_in=st.booleans(),
    )
    @settings(max_examples=100, deadline=None)
    def test_opt_in_values_are_independent(
        self,
        first_name: str,
        last_name: str,
        phone: str,
        sms_opt_in: bool,
        email_opt_in: bool,
    ) -> None:
        """Test that SMS and email opt-in values are independent.

        **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

        Setting one opt-in value should not affect the other.
        Each preference should be stored independently.
        """
        customer = CustomerCreate(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            sms_opt_in=sms_opt_in,
            email_opt_in=email_opt_in,
        )

        assert customer.sms_opt_in == sms_opt_in, (
            f"Expected sms_opt_in={sms_opt_in}, "
            f"got sms_opt_in={customer.sms_opt_in}"
        )
        assert customer.email_opt_in == email_opt_in, (
            f"Expected email_opt_in={email_opt_in}, "
            f"got email_opt_in={customer.email_opt_in}"
        )
