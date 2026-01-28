"""Property-based tests for schema validation.

This module contains property-based tests using Hypothesis for testing
phone normalization idempotence and zone count bounds validation.

**PBT: Property 4, Property 6**
"""

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)
from pydantic import ValidationError

from grins_platform.schemas.customer import normalize_phone
from grins_platform.schemas.property import PropertyCreate

# =============================================================================
# Phone Normalization Property Tests (Property 6)
# =============================================================================


@pytest.mark.unit
class TestPhoneNormalizationPBT:
    """Property-based tests for phone normalization idempotence.

    **Validates: Requirements 6.10**
    **PBT: Property 6**

    Property 6 states: For any phone string P, normalize(normalize(P)) = normalize(P)
    This ensures that phone normalization is idempotent - applying it multiple
    times produces the same result as applying it once.
    """

    @given(
        st.text(
            alphabet=st.sampled_from("0123456789"),
            min_size=10,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_normalize_idempotence_10_digit(self, phone: str) -> None:
        """Test that normalize(normalize(x)) == normalize(x) for 10-digit phones.

        **Validates: Requirements 6.10**
        **PBT: Property 6**

        This test generates random 10-digit phone numbers and verifies that
        normalizing them twice produces the same result as normalizing once.
        """
        first_normalize = normalize_phone(phone)
        second_normalize = normalize_phone(first_normalize)
        assert first_normalize == second_normalize

    @given(
        st.text(
            alphabet=st.sampled_from("0123456789"),
            min_size=10,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_normalize_idempotence_11_digit_with_country_code(
        self,
        phone_suffix: str,
    ) -> None:
        """Test idempotence for 11-digit phones starting with country code 1.

        **Validates: Requirements 6.10**
        **PBT: Property 6**

        This test generates random 10-digit phone numbers and prepends '1'
        (US country code) to verify normalization idempotence.
        """
        # Prepend country code to create 11-digit phone
        phone = "1" + phone_suffix
        first_normalize = normalize_phone(phone)
        second_normalize = normalize_phone(first_normalize)
        assert first_normalize == second_normalize

    @given(
        st.text(
            alphabet=st.sampled_from("0123456789"),
            min_size=10,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_normalized_phone_is_always_10_digits(self, phone: str) -> None:
        """Test that normalized phone is always exactly 10 digits.

        **Validates: Requirements 6.10**
        **PBT: Property 6**

        This test verifies that the output of normalize_phone is always
        a 10-digit string containing only numeric characters.
        """
        result = normalize_phone(phone)
        assert len(result) == 10
        assert result.isdigit()

    @given(
        st.text(
            alphabet=st.sampled_from("0123456789"),
            min_size=10,
            max_size=10,
        ),
        st.lists(
            st.sampled_from(["-", " ", ".", "(", ")", "+"]),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_normalize_idempotence_with_formatting(
        self,
        digits: str,
        separators: list[str],
    ) -> None:
        """Test idempotence with various formatting characters.

        **Validates: Requirements 6.10**
        **PBT: Property 6**

        This test generates phone numbers with random formatting characters
        (dashes, spaces, dots, parentheses) and verifies that normalization
        is idempotent regardless of the input format.
        """
        # Insert separators at random positions
        formatted_phone = digits
        for sep in separators:
            if len(formatted_phone) > 1:
                pos = len(formatted_phone) // 2
                formatted_phone = formatted_phone[:pos] + sep + formatted_phone[pos:]

        first_normalize = normalize_phone(formatted_phone)
        second_normalize = normalize_phone(first_normalize)
        assert first_normalize == second_normalize

    @given(
        st.text(
            alphabet=st.sampled_from("0123456789"),
            min_size=10,
            max_size=10,
        ),
        st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=9),
                st.sampled_from(["-", " ", ".", "(", ")", "+"]),
            ),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(max_examples=200)
    def test_normalize_idempotence_mixed_format(
        self,
        digits: str,
        insertions: list[tuple[int, str]],
    ) -> None:
        """Test idempotence with mixed format phone strings.

        **Validates: Requirements 6.10**
        **PBT: Property 6**

        This test generates phone strings with a mix of digits and formatting
        characters by inserting separators at various positions.
        """
        # Build formatted phone by inserting separators
        phone = digits
        for pos, sep in sorted(insertions, reverse=True):
            # Clamp position to valid range
            insert_pos = min(pos, len(phone))
            phone = phone[:insert_pos] + sep + phone[insert_pos:]

        first_normalize = normalize_phone(phone)
        second_normalize = normalize_phone(first_normalize)
        assert first_normalize == second_normalize


# =============================================================================
# Zone Count Bounds Property Tests (Property 4)
# =============================================================================


@pytest.mark.unit
class TestZoneCountBoundsPBT:
    """Property-based tests for zone count validation.

    **Validates: Requirement 2.2**
    **PBT: Property 4**

    Property 4 states: For any property P, P.zone_count is null OR
    (1 ≤ P.zone_count ≤ 50)

    This ensures that zone counts are always within the valid range
    for irrigation systems.
    """

    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=100)
    def test_valid_zone_counts_accepted(self, zone_count: int) -> None:
        """Test that all values in valid range (1-50) are accepted.

        **Validates: Requirement 2.2**
        **PBT: Property 4**

        This test generates random integers in the range [1, 50] and
        verifies that PropertyCreate accepts them as valid zone counts.
        """
        prop = PropertyCreate(
            address="123 Test St",
            city="Eden Prairie",
            zone_count=zone_count,
        )
        assert prop.zone_count == zone_count

    @given(st.integers(max_value=0))
    @settings(max_examples=50)
    def test_zone_counts_below_minimum_rejected(self, zone_count: int) -> None:
        """Test that values below minimum (< 1) are rejected.

        **Validates: Requirement 2.2**
        **PBT: Property 4**

        This test generates random integers <= 0 and verifies that
        PropertyCreate rejects them with a validation error.
        """
        with pytest.raises(ValidationError):
            PropertyCreate(
                address="123 Test St",
                city="Eden Prairie",
                zone_count=zone_count,
            )

    @given(st.integers(min_value=51))
    @settings(max_examples=50)
    def test_zone_counts_above_maximum_rejected(self, zone_count: int) -> None:
        """Test that values above maximum (> 50) are rejected.

        **Validates: Requirement 2.2**
        **PBT: Property 4**

        This test generates random integers >= 51 and verifies that
        PropertyCreate rejects them with a validation error.
        """
        with pytest.raises(ValidationError):
            PropertyCreate(
                address="123 Test St",
                city="Eden Prairie",
                zone_count=zone_count,
            )

    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=100)
    def test_zone_count_preserved_after_creation(self, zone_count: int) -> None:
        """Test that zone count value is preserved exactly after creation.

        **Validates: Requirement 2.2**
        **PBT: Property 4**

        This test verifies that the zone count value stored in the
        PropertyCreate schema is exactly the same as the input value.
        """
        prop = PropertyCreate(
            address="123 Test St",
            city="Eden Prairie",
            zone_count=zone_count,
        )
        # Verify the value is preserved exactly
        assert prop.zone_count == zone_count
        assert isinstance(prop.zone_count, int)

    def test_zone_count_none_is_valid(self) -> None:
        """Test that None zone_count is valid (optional field).

        **Validates: Requirement 2.2**
        **PBT: Property 4**

        Property 4 allows zone_count to be null, so this test verifies
        that PropertyCreate accepts None as a valid value.
        """
        prop = PropertyCreate(
            address="123 Test St",
            city="Eden Prairie",
            zone_count=None,
        )
        assert prop.zone_count is None

    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=50)
    def test_zone_count_boundary_values(self, zone_count: int) -> None:
        """Test zone count at and near boundaries.

        **Validates: Requirement 2.2**
        **PBT: Property 4**

        This test specifically focuses on boundary values to ensure
        the validation correctly handles edge cases.
        """
        # Test the generated value
        prop = PropertyCreate(
            address="123 Test St",
            city="Eden Prairie",
            zone_count=zone_count,
        )
        assert prop.zone_count is not None
        assert 1 <= prop.zone_count <= 50

    def test_zone_count_exact_boundaries(self) -> None:
        """Test exact boundary values (1 and 50).

        **Validates: Requirement 2.2**
        **PBT: Property 4**

        This test explicitly verifies that the exact boundary values
        (1 and 50) are accepted.
        """
        # Test minimum boundary
        prop_min = PropertyCreate(
            address="123 Test St",
            city="Eden Prairie",
            zone_count=1,
        )
        assert prop_min.zone_count == 1

        # Test maximum boundary
        prop_max = PropertyCreate(
            address="123 Test St",
            city="Eden Prairie",
            zone_count=50,
        )
        assert prop_max.zone_count == 50

    def test_zone_count_just_outside_boundaries(self) -> None:
        """Test values just outside boundaries (0 and 51).

        **Validates: Requirement 2.2**
        **PBT: Property 4**

        This test explicitly verifies that values just outside the
        valid range (0 and 51) are rejected.
        """
        # Test just below minimum
        with pytest.raises(ValidationError):
            PropertyCreate(
                address="123 Test St",
                city="Eden Prairie",
                zone_count=0,
            )

        # Test just above maximum
        with pytest.raises(ValidationError):
            PropertyCreate(
                address="123 Test St",
                city="Eden Prairie",
                zone_count=51,
            )
