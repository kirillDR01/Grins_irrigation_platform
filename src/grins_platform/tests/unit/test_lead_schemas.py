"""Tests for Lead Pydantic schemas.

This module tests the lead-related Pydantic schemas including
phone normalization, zip code validation, HTML sanitization,
honeypot field handling, enum validation, and max length constraints.

Validates: Requirement 1.2-1.7, 1.11
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.models.enums import LeadSituation, LeadStatus
from grins_platform.schemas.lead import (
    LeadResponse,
    LeadSubmission,
    LeadUpdate,
    strip_html_tags,
)

# =============================================================================
# strip_html_tags utility function tests
# =============================================================================


@pytest.mark.unit
class TestStripHtmlTags:
    """Test suite for the strip_html_tags utility function.

    Validates: Requirement 1.11, 12.4
    """

    def test_strips_script_tags(self) -> None:
        """Test stripping <script> tags from input."""
        result = strip_html_tags("<script>alert(1)</script>John")
        assert result == "alert(1)John"

    def test_strips_bold_tags(self) -> None:
        """Test stripping <b> tags from input."""
        result = strip_html_tags("<b>bold</b>")
        assert result == "bold"

    def test_strips_nested_tags(self) -> None:
        """Test stripping nested HTML tags."""
        result = strip_html_tags("<div><p>Hello</p></div>")
        assert result == "Hello"

    def test_strips_self_closing_tags(self) -> None:
        """Test stripping self-closing tags like <br/> and <img/>."""
        result = strip_html_tags("Hello<br/>World")
        assert result == "HelloWorld"

    def test_preserves_plain_text(self) -> None:
        """Test that plain text without HTML is preserved."""
        result = strip_html_tags("John Doe")
        assert result == "John Doe"

    def test_strips_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        result = strip_html_tags("  Hello World  ")
        assert result == "Hello World"

    def test_empty_string_returns_empty(self) -> None:
        """Test that empty string returns empty string."""
        result = strip_html_tags("")
        assert result == ""

    def test_only_tags_returns_empty(self) -> None:
        """Test that string with only tags returns empty string."""
        result = strip_html_tags("<div></div>")
        assert result == ""

    def test_strips_attributes_in_tags(self) -> None:
        """Test stripping tags with attributes."""
        result = strip_html_tags('<a href="http://evil.com">Click</a>')
        assert result == "Click"

    def test_idempotent(self) -> None:
        """Test that applying strip_html_tags twice gives same result."""
        text = "<b>Hello</b> <i>World</i>"
        first = strip_html_tags(text)
        second = strip_html_tags(first)
        assert first == second


# =============================================================================
# Phone normalization tests
# =============================================================================


@pytest.mark.unit
class TestPhoneNormalization:
    """Test suite for phone normalization in LeadSubmission.

    Validates: Requirement 1.2, 1.3
    """

    def _make_submission(self, phone: str) -> LeadSubmission:
        """Helper to create a LeadSubmission with a given phone."""
        return LeadSubmission(
            name="Test User",
            phone=phone,
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )

    def test_parentheses_format_normalized(self) -> None:
        """Test '(612) 555-0123' normalizes to '6125550123'."""
        sub = self._make_submission("(612) 555-0123")
        assert sub.phone == "6125550123"

    def test_dashes_format_normalized(self) -> None:
        """Test '612-555-0123' normalizes to '6125550123'."""
        sub = self._make_submission("612-555-0123")
        assert sub.phone == "6125550123"

    def test_plain_digits_preserved(self) -> None:
        """Test '6125550123' stays as '6125550123'."""
        sub = self._make_submission("6125550123")
        assert sub.phone == "6125550123"

    def test_dots_format_normalized(self) -> None:
        """Test '612.555.0123' normalizes to '6125550123'."""
        sub = self._make_submission("612.555.0123")
        assert sub.phone == "6125550123"

    def test_spaces_format_normalized(self) -> None:
        """Test '612 555 0123' normalizes to '6125550123'."""
        sub = self._make_submission("612 555 0123")
        assert sub.phone == "6125550123"

    def test_country_code_1_stripped(self) -> None:
        """Test '16125550123' (11 digits with leading 1) normalizes to '6125550123'."""
        sub = self._make_submission("16125550123")
        assert sub.phone == "6125550123"

    def test_country_code_plus_1_stripped(self) -> None:
        """Test '+1 (612) 555-0123' normalizes to '6125550123'."""
        sub = self._make_submission("+1 (612) 555-0123")
        assert sub.phone == "6125550123"


# =============================================================================
# Phone rejection tests
# =============================================================================


@pytest.mark.unit
class TestPhoneRejection:
    """Test suite for phone rejection in LeadSubmission.

    Validates: Requirement 1.3
    """

    def test_too_short_rejected(self) -> None:
        """Test that '123' (too short) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="123",
                zip_code="55424",
                situation=LeadSituation.NEW_SYSTEM,
            )
        errors = exc_info.value.errors()
        assert any("phone" in str(e["loc"]) for e in errors)

    def test_no_digits_rejected(self) -> None:
        """Test that 'abcdefghij' (no digits) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="abcdefghij",
                zip_code="55424",
                situation=LeadSituation.NEW_SYSTEM,
            )
        errors = exc_info.value.errors()
        assert any("phone" in str(e["loc"]) for e in errors)

    def test_eleven_digits_not_starting_with_1_rejected(self) -> None:
        """Test that 11 digits not starting with 1 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="26125550123",
                zip_code="55424",
                situation=LeadSituation.NEW_SYSTEM,
            )
        errors = exc_info.value.errors()
        assert any("phone" in str(e["loc"]) for e in errors)

    def test_nine_digits_rejected(self) -> None:
        """Test that 9 digits is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="612555012",
                zip_code="55424",
                situation=LeadSituation.NEW_SYSTEM,
            )
        errors = exc_info.value.errors()
        assert any("phone" in str(e["loc"]) for e in errors)


# =============================================================================
# Zip code validation tests
# =============================================================================


@pytest.mark.unit
class TestZipCodeValidation:
    """Test suite for zip code validation in LeadSubmission.

    Validates: Requirement 1.4
    """

    def test_valid_5_digit_zip(self) -> None:
        """Test '55424' is accepted and preserved."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )
        assert sub.zip_code == "55424"

    def test_3_digit_zip_rejected(self) -> None:
        """Test '554' (too short) is rejected by min_length constraint."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="6125550123",
                zip_code="554",
                situation=LeadSituation.NEW_SYSTEM,
            )
        errors = exc_info.value.errors()
        assert any("zip_code" in str(e["loc"]) for e in errors)

    def test_too_few_digits_rejected(self) -> None:
        """Test zip code with fewer than 5 digits is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="6125550123",
                zip_code="5542",
                situation=LeadSituation.NEW_SYSTEM,
            )
        errors = exc_info.value.errors()
        assert any("zip_code" in str(e["loc"]) for e in errors)

    def test_too_many_digits_rejected(self) -> None:
        """Test zip code with more than 5 digits is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="6125550123",
                zip_code="5542412345",
                situation=LeadSituation.NEW_SYSTEM,
            )
        errors = exc_info.value.errors()
        assert any("zip_code" in str(e["loc"]) for e in errors)

    def test_zip_with_dash_extension_rejected(self) -> None:
        """Test '55424-1234' (9 digits) is rejected — only 5 digits allowed."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="6125550123",
                zip_code="55424-1234",
                situation=LeadSituation.NEW_SYSTEM,
            )
        errors = exc_info.value.errors()
        assert any("zip_code" in str(e["loc"]) for e in errors)

    def test_non_numeric_zip_rejected(self) -> None:
        """Test non-numeric zip code is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="6125550123",
                zip_code="abcde",
                situation=LeadSituation.NEW_SYSTEM,
            )
        errors = exc_info.value.errors()
        assert any("zip_code" in str(e["loc"]) for e in errors)


# =============================================================================
# Situation enum validation tests
# =============================================================================


@pytest.mark.unit
class TestSituationEnumValidation:
    """Test suite for situation enum validation in LeadSubmission.

    Validates: Requirement 1.5
    """

    def test_new_system_accepted(self) -> None:
        """Test 'new_system' situation is accepted."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )
        assert sub.situation == LeadSituation.NEW_SYSTEM

    def test_upgrade_accepted(self) -> None:
        """Test 'upgrade' situation is accepted."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.UPGRADE,
        )
        assert sub.situation == LeadSituation.UPGRADE

    def test_repair_accepted(self) -> None:
        """Test 'repair' situation is accepted."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.REPAIR,
        )
        assert sub.situation == LeadSituation.REPAIR

    def test_exploring_accepted(self) -> None:
        """Test 'exploring' situation is accepted."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.EXPLORING,
        )
        assert sub.situation == LeadSituation.EXPLORING

    def test_all_valid_situations_accepted(self) -> None:
        """Test all LeadSituation enum values are accepted."""
        for situation in LeadSituation:
            sub = LeadSubmission(
                name="Test User",
                phone="6125550123",
                zip_code="55424",
                situation=situation,
            )
            assert sub.situation == situation

    def test_invalid_situation_rejected(self) -> None:
        """Test that an invalid situation value is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="6125550123",
                zip_code="55424",
                situation="invalid_situation",  # type: ignore[arg-type]
            )
        errors = exc_info.value.errors()
        assert any("situation" in str(e["loc"]) for e in errors)


# =============================================================================
# Email validation tests
# =============================================================================


@pytest.mark.unit
class TestEmailValidation:
    """Test suite for email validation in LeadSubmission.

    Validates: Requirement 1.6
    """

    def test_none_email_accepted(self) -> None:
        """Test that None email (optional) is accepted."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            email=None,
        )
        assert sub.email is None

    def test_omitted_email_defaults_to_none(self) -> None:
        """Test that omitting email defaults to None."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )
        assert sub.email is None

    def test_valid_email_accepted(self) -> None:
        """Test that a valid email is accepted."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            email="john@example.com",
        )
        assert sub.email == "john@example.com"

    def test_invalid_email_rejected(self) -> None:
        """Test that an invalid email format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="6125550123",
                zip_code="55424",
                situation=LeadSituation.NEW_SYSTEM,
                email="not-an-email",
            )
        errors = exc_info.value.errors()
        assert any("email" in str(e["loc"]) for e in errors)

    def test_email_missing_domain_rejected(self) -> None:
        """Test that email without domain is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="6125550123",
                zip_code="55424",
                situation=LeadSituation.NEW_SYSTEM,
                email="john@",
            )
        errors = exc_info.value.errors()
        assert any("email" in str(e["loc"]) for e in errors)


# =============================================================================
# HTML tag stripping in name and notes
# =============================================================================


@pytest.mark.unit
class TestHtmlSanitization:
    """Test suite for HTML tag stripping in name and notes fields.

    Validates: Requirement 1.11
    """

    def test_name_script_tags_stripped(self) -> None:
        """Test '<script>alert(1)</script>John' → 'alert(1)John' in name."""
        sub = LeadSubmission(
            name="<script>alert(1)</script>John",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )
        assert sub.name == "alert(1)John"

    def test_name_bold_tags_stripped(self) -> None:
        """Test '<b>bold</b>' → 'bold' in name."""
        sub = LeadSubmission(
            name="<b>bold</b>",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )
        assert sub.name == "bold"

    def test_name_plain_text_preserved(self) -> None:
        """Test plain text name is preserved."""
        sub = LeadSubmission(
            name="John Doe",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )
        assert sub.name == "John Doe"

    def test_notes_html_stripped(self) -> None:
        """Test HTML tags are stripped from notes."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            notes="<p>My backyard is <b>large</b></p>",
        )
        assert sub.notes == "My backyard is large"

    def test_notes_none_preserved(self) -> None:
        """Test that None notes remain None."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            notes=None,
        )
        assert sub.notes is None

    def test_notes_only_tags_becomes_none(self) -> None:
        """Test that notes with only HTML tags become None."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            notes="<div></div>",
        )
        assert sub.notes is None

    def test_lead_update_notes_html_stripped(self) -> None:
        """Test HTML tags are stripped from notes in LeadUpdate."""
        update = LeadUpdate(
            notes="<script>evil</script>Clean notes",
        )
        assert update.notes == "evilClean notes"

    def test_lead_update_notes_none_preserved(self) -> None:
        """Test that None notes in LeadUpdate remain None."""
        update = LeadUpdate(notes=None)
        assert update.notes is None


# =============================================================================
# Honeypot field tests
# =============================================================================


@pytest.mark.unit
class TestHoneypotField:
    """Test suite for honeypot field acceptance in LeadSubmission.

    Validates: Requirement 2.1, 2.2
    """

    def test_empty_string_honeypot_accepted(self) -> None:
        """Test that website='' (empty string) is accepted."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            website="",
        )
        assert sub.website == ""

    def test_none_honeypot_accepted(self) -> None:
        """Test that website=None is accepted."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            website=None,
        )
        assert sub.website is None

    def test_omitted_honeypot_defaults_to_none(self) -> None:
        """Test that omitting website defaults to None."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )
        assert sub.website is None

    def test_filled_honeypot_accepted_at_schema_level(self) -> None:
        """Test that a filled honeypot is accepted by the schema.

        Note: The schema accepts any value — bot detection is handled
        at the service layer, not the schema layer.
        """
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            website="http://spam.com",
        )
        assert sub.website == "http://spam.com"


# =============================================================================
# Max length constraint tests
# =============================================================================


@pytest.mark.unit
class TestMaxLengthConstraints:
    """Test suite for max length constraints in LeadSubmission.

    Validates: Requirement 1.7, 4.2
    """

    def test_name_over_200_chars_rejected(self) -> None:
        """Test that name exceeding 200 characters is rejected."""
        long_name = "A" * 201
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name=long_name,
                phone="6125550123",
                zip_code="55424",
                situation=LeadSituation.NEW_SYSTEM,
            )
        errors = exc_info.value.errors()
        assert any("name" in str(e["loc"]) for e in errors)

    def test_name_exactly_200_chars_accepted(self) -> None:
        """Test that name at exactly 200 characters is accepted."""
        name_200 = "A" * 200
        sub = LeadSubmission(
            name=name_200,
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )
        assert len(sub.name) == 200

    def test_notes_over_1000_chars_rejected(self) -> None:
        """Test that notes exceeding 1000 characters is rejected."""
        long_notes = "A" * 1001
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="6125550123",
                zip_code="55424",
                situation=LeadSituation.NEW_SYSTEM,
                notes=long_notes,
            )
        errors = exc_info.value.errors()
        assert any("notes" in str(e["loc"]) for e in errors)

    def test_notes_exactly_1000_chars_accepted(self) -> None:
        """Test that notes at exactly 1000 characters is accepted."""
        notes_1000 = "A" * 1000
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            notes=notes_1000,
        )
        assert sub.notes == notes_1000

    def test_source_site_over_100_chars_rejected(self) -> None:
        """Test that source_site exceeding 100 characters is rejected."""
        long_source = "A" * 101
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="Test User",
                phone="6125550123",
                zip_code="55424",
                situation=LeadSituation.NEW_SYSTEM,
                source_site=long_source,
            )
        errors = exc_info.value.errors()
        assert any("source_site" in str(e["loc"]) for e in errors)

    def test_empty_name_rejected(self) -> None:
        """Test that empty name is rejected (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            LeadSubmission(
                name="",
                phone="6125550123",
                zip_code="55424",
                situation=LeadSituation.NEW_SYSTEM,
            )
        errors = exc_info.value.errors()
        assert any("name" in str(e["loc"]) for e in errors)


# =============================================================================
# LeadResponse enum converter tests
# =============================================================================


@pytest.mark.unit
class TestLeadResponseEnumConverters:
    """Test suite for LeadResponse enum converters.

    Validates: Requirement 5.8
    """

    def _make_lead_data(self, **overrides: object) -> dict[str, object]:
        """Helper to create valid lead response data."""
        defaults: dict[str, object] = {
            "id": uuid4(),
            "name": "Test User",
            "phone": "6125550123",
            "email": None,
            "zip_code": "55424",
            "situation": LeadSituation.NEW_SYSTEM,
            "notes": None,
            "source_site": "residential",
            "status": LeadStatus.NEW,
            "assigned_to": None,
            "customer_id": None,
            "contacted_at": None,
            "converted_at": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        defaults.update(overrides)
        return defaults

    def test_status_string_converted_to_enum(self) -> None:
        """Test that string status is converted to LeadStatus enum."""
        data = self._make_lead_data(status="new")
        response = LeadResponse(**data)
        assert response.status == LeadStatus.NEW
        assert isinstance(response.status, LeadStatus)

    def test_status_enum_preserved(self) -> None:
        """Test that LeadStatus enum is preserved as-is."""
        data = self._make_lead_data(status=LeadStatus.CONTACTED)
        response = LeadResponse(**data)
        assert response.status == LeadStatus.CONTACTED

    def test_situation_string_converted_to_enum(self) -> None:
        """Test that string situation is converted to LeadSituation enum."""
        data = self._make_lead_data(situation="repair")
        response = LeadResponse(**data)
        assert response.situation == LeadSituation.REPAIR
        assert isinstance(response.situation, LeadSituation)

    def test_situation_enum_preserved(self) -> None:
        """Test that LeadSituation enum is preserved as-is."""
        data = self._make_lead_data(situation=LeadSituation.EXPLORING)
        response = LeadResponse(**data)
        assert response.situation == LeadSituation.EXPLORING

    def test_all_status_strings_convert(self) -> None:
        """Test that all LeadStatus string values convert correctly."""
        for status in LeadStatus:
            data = self._make_lead_data(status=status.value)
            response = LeadResponse(**data)
            assert response.status == status

    def test_all_situation_strings_convert(self) -> None:
        """Test that all LeadSituation string values convert correctly."""
        for situation in LeadSituation:
            data = self._make_lead_data(situation=situation.value)
            response = LeadResponse(**data)
            assert response.situation == situation

    def test_invalid_status_string_rejected(self) -> None:
        """Test that an invalid status string raises ValueError."""
        data = self._make_lead_data(status="invalid_status")
        with pytest.raises((ValidationError, ValueError)):
            LeadResponse(**data)

    def test_invalid_situation_string_rejected(self) -> None:
        """Test that an invalid situation string raises ValueError."""
        data = self._make_lead_data(situation="invalid_situation")
        with pytest.raises((ValidationError, ValueError)):
            LeadResponse(**data)


# =============================================================================
# Default values tests
# =============================================================================


@pytest.mark.unit
class TestDefaultValues:
    """Test suite for default values in LeadSubmission.

    Validates: Requirement 1.8
    """

    def test_source_site_defaults_to_residential(self) -> None:
        """Test that source_site defaults to 'residential'."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )
        assert sub.source_site == "residential"

    def test_source_site_can_be_overridden(self) -> None:
        """Test that source_site can be set to a custom value."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
            source_site="commercial",
        )
        assert sub.source_site == "commercial"

    def test_email_defaults_to_none(self) -> None:
        """Test that email defaults to None."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )
        assert sub.email is None

    def test_notes_defaults_to_none(self) -> None:
        """Test that notes defaults to None."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )
        assert sub.notes is None

    def test_website_defaults_to_none(self) -> None:
        """Test that website (honeypot) defaults to None."""
        sub = LeadSubmission(
            name="Test User",
            phone="6125550123",
            zip_code="55424",
            situation=LeadSituation.NEW_SYSTEM,
        )
        assert sub.website is None
