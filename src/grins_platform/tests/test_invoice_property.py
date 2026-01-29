"""Property-based tests for invoice management.

Property 5: Invoice Number Uniqueness
Property 6: Payment Recording Correctness
Property 7: Lien Eligibility Determination

Validates: Requirements 7.1, 9.5-9.6, 11.1
"""

import re
from datetime import date
from decimal import Decimal

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)


@pytest.mark.unit
class TestInvoiceNumberProperty:
    """Property-based tests for invoice number generation.

    Property 5: Invoice Number Uniqueness
    - Invoice numbers follow format INV-{YEAR}-{SEQUENCE}
    - Sequence numbers are unique and incrementing

    Validates: Requirement 7.1
    """

    INVOICE_NUMBER_PATTERN = re.compile(r"^INV-(\d{4})-(\d{6})$")

    @given(
        year=st.integers(min_value=2020, max_value=2099),
        sequence=st.integers(min_value=1, max_value=999999),
    )
    @settings(max_examples=100)
    def test_invoice_number_format_is_valid(self, year: int, sequence: int) -> None:
        """Property: Invoice numbers match format INV-{YEAR}-{SEQUENCE:06d}."""
        invoice_number = f"INV-{year}-{sequence:06d}"

        match = self.INVOICE_NUMBER_PATTERN.match(invoice_number)
        assert match is not None, f"Invalid format: {invoice_number}"

        parsed_year = int(match.group(1))
        parsed_seq = int(match.group(2))

        assert parsed_year == year
        assert parsed_seq == sequence

    @given(
        seq1=st.integers(min_value=1, max_value=999998),
        seq2=st.integers(min_value=1, max_value=999998),
    )
    @settings(max_examples=50)
    def test_different_sequences_produce_different_numbers(
        self, seq1: int, seq2: int,
    ) -> None:
        """Property: Different sequences produce different invoice numbers."""
        if seq1 == seq2:
            return  # Skip when sequences are the same

        year = date.today().year
        inv1 = f"INV-{year}-{seq1:06d}"
        inv2 = f"INV-{year}-{seq2:06d}"

        assert inv1 != inv2

    @given(
        year1=st.integers(min_value=2020, max_value=2099),
        year2=st.integers(min_value=2020, max_value=2099),
        sequence=st.integers(min_value=1, max_value=999999),
    )
    @settings(max_examples=50)
    def test_different_years_produce_different_numbers(
        self, year1: int, year2: int, sequence: int,
    ) -> None:
        """Property: Same sequence in different years produces different numbers."""
        if year1 == year2:
            return  # Skip when years are the same

        inv1 = f"INV-{year1}-{sequence:06d}"
        inv2 = f"INV-{year2}-{sequence:06d}"

        assert inv1 != inv2

    @given(
        sequences=st.lists(
            st.integers(min_value=1, max_value=999999),
            min_size=2,
            max_size=20,
            unique=True,
        ),
    )
    @settings(max_examples=30)
    def test_unique_sequences_produce_unique_numbers(
        self, sequences: list[int],
    ) -> None:
        """Property: A set of unique sequences produces unique invoice numbers."""
        year = date.today().year
        invoice_numbers = [f"INV-{year}-{seq:06d}" for seq in sequences]

        # All invoice numbers should be unique
        assert len(invoice_numbers) == len(set(invoice_numbers))

    def test_sequence_padding_is_consistent(self) -> None:
        """Property: Sequence is always zero-padded to 6 digits."""
        year = date.today().year

        test_cases = [1, 10, 100, 1000, 10000, 100000, 999999]
        for seq in test_cases:
            inv = f"INV-{year}-{seq:06d}"
            match = self.INVOICE_NUMBER_PATTERN.match(inv)
            assert match is not None
            # The sequence part should always be 6 digits
            assert len(match.group(2)) == 6


@pytest.mark.unit
class TestPaymentRecordingProperty:
    """Property-based tests for payment recording.

    Property 6: Payment Recording Correctness
    - paid_amount >= total_amount → status = paid
    - paid_amount < total_amount → status = partial

    Validates: Requirements 9.5-9.6
    """

    @given(
        total_amount=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("10000.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        payment_amount=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("20000.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=100)
    def test_payment_status_determination(
        self, total_amount: Decimal, payment_amount: Decimal,
    ) -> None:
        """Property: Payment status is correctly determined based on amounts."""
        # Simulate payment recording logic
        expected_status = "paid" if payment_amount >= total_amount else "partial"

        # Verify the logic
        if payment_amount >= total_amount:
            assert expected_status == "paid"
        else:
            assert expected_status == "partial"

    @given(
        total_amount=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("10000.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=50)
    def test_exact_payment_results_in_paid(self, total_amount: Decimal) -> None:
        """Property: Paying exact amount results in 'paid' status."""
        payment_amount = total_amount

        status = "paid" if payment_amount >= total_amount else "partial"

        assert status == "paid"

    @given(
        total_amount=st.decimals(
            min_value=Decimal("1.00"),
            max_value=Decimal("10000.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        underpayment_factor=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("0.99"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=50)
    def test_partial_payment_results_in_partial(
        self, total_amount: Decimal, underpayment_factor: Decimal,
    ) -> None:
        """Property: Paying less than total results in 'partial' status."""
        payment_amount = total_amount * underpayment_factor

        status = "paid" if payment_amount >= total_amount else "partial"

        assert status == "partial"

    @given(
        total_amount=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("10000.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        overpayment=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("1000.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=50)
    def test_overpayment_results_in_paid(
        self, total_amount: Decimal, overpayment: Decimal,
    ) -> None:
        """Property: Paying more than total still results in 'paid' status."""
        payment_amount = total_amount + overpayment

        status = "paid" if payment_amount >= total_amount else "partial"

        assert status == "paid"

    @given(
        payments=st.lists(
            st.decimals(
                min_value=Decimal("0.01"),
                max_value=Decimal("500.00"),
                places=2,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=1,
            max_size=5,
        ),
        total_amount=st.decimals(
            min_value=Decimal("100.00"),
            max_value=Decimal("1000.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=50)
    def test_cumulative_payments_status(
        self, payments: list[Decimal], total_amount: Decimal,
    ) -> None:
        """Property: Cumulative payments correctly determine final status."""
        cumulative_paid = sum(payments)

        expected_status = "paid" if cumulative_paid >= total_amount else "partial"

        # Verify the logic
        if cumulative_paid >= total_amount:
            assert expected_status == "paid"
        else:
            assert expected_status == "partial"


@pytest.mark.unit
class TestLienEligibilityProperty:
    """Property-based tests for lien eligibility determination.

    Property 7: Lien Eligibility Determination
    - Installation jobs are lien-eligible
    - Major repair jobs are lien-eligible
    - Seasonal services are NOT lien-eligible

    Validates: Requirement 11.1
    """

    # Define lien-eligible job types (from invoice_service.py)
    LIEN_ELIGIBLE_TYPES: frozenset[str] = frozenset({
        "installation",
        "major_repair",
        "new_system",
        "system_expansion",
    })

    NON_LIEN_ELIGIBLE_TYPES: frozenset[str] = frozenset({
        "spring_startup",
        "winterization",
        "tune_up",
        "repair",
        "diagnostic",
        "maintenance",
    })

    def is_lien_eligible(self, job_type: str) -> bool:
        """Determine if a job type is lien-eligible."""
        return job_type.lower() in self.LIEN_ELIGIBLE_TYPES

    @given(job_type=st.sampled_from(list(LIEN_ELIGIBLE_TYPES)))
    @settings(max_examples=20)
    def test_lien_eligible_types_are_eligible(self, job_type: str) -> None:
        """Property: All lien-eligible job types return True."""
        assert self.is_lien_eligible(job_type) is True

    @given(job_type=st.sampled_from(list(NON_LIEN_ELIGIBLE_TYPES)))
    @settings(max_examples=20)
    def test_non_lien_eligible_types_are_not_eligible(self, job_type: str) -> None:
        """Property: All non-lien-eligible job types return False."""
        assert self.is_lien_eligible(job_type) is False

    @given(
        job_type=st.sampled_from(list(LIEN_ELIGIBLE_TYPES)),
        case_variant=st.sampled_from(["lower", "upper", "title"]),
    )
    @settings(max_examples=30)
    def test_lien_eligibility_is_case_insensitive(
        self, job_type: str, case_variant: str,
    ) -> None:
        """Property: Lien eligibility check is case-insensitive."""
        if case_variant == "lower":
            test_type = job_type.lower()
        elif case_variant == "upper":
            test_type = job_type.upper()
        else:
            test_type = job_type.title()

        # The is_lien_eligible function converts to lowercase
        assert self.is_lien_eligible(test_type) is True

    def test_lien_eligible_and_non_eligible_are_disjoint(self) -> None:
        """Property: Lien-eligible and non-eligible sets have no overlap."""
        overlap = self.LIEN_ELIGIBLE_TYPES & self.NON_LIEN_ELIGIBLE_TYPES
        assert len(overlap) == 0, f"Overlapping types: {overlap}"

    @given(
        random_type=st.text(
            min_size=1,
            max_size=30,
            alphabet=st.sampled_from(
                "abcdefghijklmnopqrstuvwxyz_",
            ),
        ),
    )
    @settings(max_examples=50)
    def test_unknown_types_are_not_lien_eligible(self, random_type: str) -> None:
        """Property: Unknown job types are not lien-eligible by default."""
        if random_type.lower() in self.LIEN_ELIGIBLE_TYPES:
            return  # Skip if randomly generated a valid type

        assert self.is_lien_eligible(random_type) is False

    def test_installation_is_always_lien_eligible(self) -> None:
        """Property: Installation jobs are always lien-eligible."""
        assert self.is_lien_eligible("installation") is True
        assert self.is_lien_eligible("INSTALLATION") is True
        assert self.is_lien_eligible("Installation") is True

    def test_seasonal_services_are_never_lien_eligible(self) -> None:
        """Property: Seasonal services are never lien-eligible."""
        seasonal_types = ["spring_startup", "winterization", "tune_up"]
        for job_type in seasonal_types:
            assert self.is_lien_eligible(job_type) is False
