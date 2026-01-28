"""Property-based tests for constraint validation.

Property 3: Constraint Validation
Test that parsed constraints are validated against known staff names.

Validates: Schedule AI Updates Requirements 4.7, 4.8
"""

import pytest
from hypothesis import (
    given,
    strategies as st,
)

from grins_platform.schemas.schedule_explanation import ParsedConstraint
from grins_platform.services.ai.constraint_parser import ConstraintParserService


@pytest.mark.unit
class TestConstraintValidationProperty:
    """Property-based tests for constraint validation."""

    @given(
        staff_name=st.text(min_size=1, max_size=50).filter(
            lambda x: x.strip() and x.isalnum(),
        ),
        known_staff=st.lists(
            st.text(min_size=1, max_size=50).filter(
                lambda x: x.strip() and x.isalnum(),
            ),
            min_size=1,
            max_size=10,
        ),
    )
    def test_valid_staff_name_has_no_errors(
        self,
        staff_name: str,
        known_staff: list[str],
    ) -> None:
        """Property: Valid staff names should not produce validation errors.

        Validates: Requirement 4.7 - Staff name validation
        """
        # Add the staff name to known staff
        known_staff_set = list({*known_staff, staff_name})

        # Create constraint with valid staff name
        constraint = ParsedConstraint(
            constraint_type="staff_time",
            description=f"{staff_name} unavailable before 10am",
            parameters={
                "staff_name": staff_name,
                "day_of_week": "Monday",
                "start_time": "10:00",
            },
            validation_errors=[],
        )

        # Create service instance (no session needed for validation)
        service = ConstraintParserService.__new__(ConstraintParserService)
        service.CONSTRAINT_TYPES = {
            "staff_time",
            "job_grouping",
            "staff_restriction",
            "geographic",
        }

        # Validate constraint
        service._validate_constraint(constraint, known_staff_set)

        # Property: Valid staff name should not produce errors
        assert len(constraint.validation_errors) == 0, (
            f"Valid staff name '{staff_name}' should not produce errors. "
            f"Errors: {constraint.validation_errors}"
        )

    @given(
        staff_name=st.text(min_size=1, max_size=50).filter(
            lambda x: x.strip() and x.isalnum(),
        ),
        known_staff=st.lists(
            st.text(min_size=1, max_size=50).filter(
                lambda x: x.strip() and x.isalnum(),
            ),
            min_size=1,
            max_size=10,
        ),
    )
    def test_unknown_staff_name_produces_error(
        self,
        staff_name: str,
        known_staff: list[str],
    ) -> None:
        """Property: Unknown staff names should produce validation errors.

        Validates: Requirement 4.8 - Unknown staff rejection
        """
        # Ensure staff name is NOT in known staff
        known_staff_set = [s for s in known_staff if s != staff_name]
        if not known_staff_set:
            known_staff_set = ["ValidStaff"]

        # Create constraint with unknown staff name
        constraint = ParsedConstraint(
            constraint_type="staff_time",
            description=f"{staff_name} unavailable before 10am",
            parameters={
                "staff_name": staff_name,
                "day_of_week": "Monday",
                "start_time": "10:00",
            },
            validation_errors=[],
        )

        # Create service instance
        service = ConstraintParserService.__new__(ConstraintParserService)
        service.CONSTRAINT_TYPES = {
            "staff_time",
            "job_grouping",
            "staff_restriction",
            "geographic",
        }

        # Validate constraint
        service._validate_constraint(constraint, known_staff_set)

        # Property: Unknown staff name should produce error
        assert len(constraint.validation_errors) > 0, (
            f"Unknown staff name '{staff_name}' should produce validation error"
        )
        assert any(
            "Unknown staff name" in error for error in constraint.validation_errors
        ), (
            f"Error should mention 'Unknown staff name'. "
            f"Errors: {constraint.validation_errors}"
        )

    @given(
        constraint_type=st.sampled_from(
            [
                "staff_time",
                "job_grouping",
                "staff_restriction",
                "geographic",
            ],
        ),
    )
    def test_valid_constraint_type_accepted(
        self,
        constraint_type: str,
    ) -> None:
        """Property: Valid constraint types should be accepted.

        Validates: Requirement 4.3-4.6 - Constraint type support
        """
        constraint = ParsedConstraint(
            constraint_type=constraint_type,
            description="Test constraint",
            parameters={},
            validation_errors=[],
        )

        service = ConstraintParserService.__new__(ConstraintParserService)
        service.CONSTRAINT_TYPES = {
            "staff_time",
            "job_grouping",
            "staff_restriction",
            "geographic",
        }

        service._validate_constraint(constraint, ["ValidStaff"])

        # Property: Valid constraint type should not produce type error
        type_errors = [
            e for e in constraint.validation_errors if "Unknown constraint type" in e
        ]
        assert len(type_errors) == 0, (
            f"Valid constraint type '{constraint_type}' should not produce "
            f"type error. Errors: {constraint.validation_errors}"
        )

    @given(
        invalid_type=st.text(min_size=1, max_size=50).filter(
            lambda x: x
            not in {
                "staff_time",
                "job_grouping",
                "staff_restriction",
                "geographic",
            },
        ),
    )
    def test_invalid_constraint_type_rejected(
        self,
        invalid_type: str,
    ) -> None:
        """Property: Invalid constraint types should be rejected.

        Validates: Requirement 4.2 - Constraint type validation
        """
        constraint = ParsedConstraint(
            constraint_type=invalid_type,
            description="Test constraint",
            parameters={},
            validation_errors=[],
        )

        service = ConstraintParserService.__new__(ConstraintParserService)
        service.CONSTRAINT_TYPES = {
            "staff_time",
            "job_grouping",
            "staff_restriction",
            "geographic",
        }

        service._validate_constraint(constraint, ["ValidStaff"])

        # Property: Invalid constraint type should produce error
        assert any(
            "Unknown constraint type" in error for error in constraint.validation_errors
        ), (
            f"Invalid constraint type '{invalid_type}' should produce error. "
            f"Errors: {constraint.validation_errors}"
        )

    def test_staff_time_requires_staff_name_and_day(self) -> None:
        """Property: staff_time constraints require staff_name and day_of_week.

        Validates: Requirement 4.3 - Staff time constraint parameters
        """
        # Missing both required parameters
        constraint = ParsedConstraint(
            constraint_type="staff_time",
            description="Test constraint",
            parameters={},
            validation_errors=[],
        )

        service = ConstraintParserService.__new__(ConstraintParserService)
        service.CONSTRAINT_TYPES = {
            "staff_time",
            "job_grouping",
            "staff_restriction",
            "geographic",
        }

        service._validate_constraint(constraint, ["ValidStaff"])

        # Should have error about missing parameters
        assert any(
            "Missing required parameters" in error
            for error in constraint.validation_errors
        ), f"Missing parameters should produce error: {constraint.validation_errors}"

    def test_job_grouping_requires_customer_names(self) -> None:
        """Property: job_grouping constraints require customer_names.

        Validates: Requirement 4.4 - Job grouping constraint parameters
        """
        constraint = ParsedConstraint(
            constraint_type="job_grouping",
            description="Test constraint",
            parameters={},
            validation_errors=[],
        )

        service = ConstraintParserService.__new__(ConstraintParserService)
        service.CONSTRAINT_TYPES = {
            "staff_time",
            "job_grouping",
            "staff_restriction",
            "geographic",
        }

        service._validate_constraint(constraint, ["ValidStaff"])

        # Should have error about missing customer_names
        assert any(
            "customer_names" in error for error in constraint.validation_errors
        ), (
            f"Missing customer_names should produce error: "
            f"{constraint.validation_errors}"
        )

    def test_staff_restriction_requires_staff_and_job_type(self) -> None:
        """Property: staff_restriction requires staff_name and job_type.

        Validates: Requirement 4.5 - Staff restriction constraint parameters
        """
        constraint = ParsedConstraint(
            constraint_type="staff_restriction",
            description="Test constraint",
            parameters={},
            validation_errors=[],
        )

        service = ConstraintParserService.__new__(ConstraintParserService)
        service.CONSTRAINT_TYPES = {
            "staff_time",
            "job_grouping",
            "staff_restriction",
            "geographic",
        }

        service._validate_constraint(constraint, ["ValidStaff"])

        # Should have error about missing parameters
        assert any(
            "Missing required parameters" in error
            for error in constraint.validation_errors
        ), f"Missing parameters should produce error: {constraint.validation_errors}"

    def test_geographic_requires_city(self) -> None:
        """Property: geographic constraints require city parameter.

        Validates: Requirement 4.6 - Geographic constraint parameters
        """
        constraint = ParsedConstraint(
            constraint_type="geographic",
            description="Test constraint",
            parameters={},
            validation_errors=[],
        )

        service = ConstraintParserService.__new__(ConstraintParserService)
        service.CONSTRAINT_TYPES = {
            "staff_time",
            "job_grouping",
            "staff_restriction",
            "geographic",
        }

        service._validate_constraint(constraint, ["ValidStaff"])

        # Should have error about missing city
        assert any("city" in error for error in constraint.validation_errors), (
            f"Missing city should produce error: {constraint.validation_errors}"
        )
