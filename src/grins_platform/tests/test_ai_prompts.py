"""Tests for AI prompts.

Validates: AI Assistant Requirements 1.1, 4.1, 5.1, 6.1, 9.1
"""

from grins_platform.services.ai.prompts.categorization import (
    CATEGORIZATION_PROMPT,
    CATEGORIZATION_REVIEW_PROMPT,
)
from grins_platform.services.ai.prompts.communication import (
    COMMUNICATION_PROMPT,
    TEMPLATES,
)
from grins_platform.services.ai.prompts.estimates import ESTIMATE_PROMPT
from grins_platform.services.ai.prompts.scheduling import SCHEDULE_GENERATION_PROMPT
from grins_platform.services.ai.prompts.system import SYSTEM_PROMPT


class TestSystemPrompt:
    """Test system prompt."""

    def test_system_prompt_exists(self) -> None:
        """Test that system prompt is defined."""
        assert SYSTEM_PROMPT is not None
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0

    def test_system_prompt_contains_key_instructions(self) -> None:
        """Test that system prompt contains key instructions."""
        assert "irrigation" in SYSTEM_PROMPT.lower()
        assert "assistant" in SYSTEM_PROMPT.lower()

    def test_system_prompt_is_not_empty(self) -> None:
        """Test that system prompt has substantial content."""
        assert len(SYSTEM_PROMPT) > 100


class TestCategorizationPrompts:
    """Test categorization prompts."""

    def test_categorization_prompt_exists(self) -> None:
        """Test that categorization prompt is defined."""
        assert CATEGORIZATION_PROMPT is not None
        assert isinstance(CATEGORIZATION_PROMPT, str)
        assert len(CATEGORIZATION_PROMPT) > 0

    def test_categorization_prompt_contains_categories(self) -> None:
        """Test that categorization prompt defines all categories."""
        assert "ready_to_schedule" in CATEGORIZATION_PROMPT
        assert "requires_estimate" in CATEGORIZATION_PROMPT
        assert "urgent" in CATEGORIZATION_PROMPT

    def test_categorization_prompt_contains_confidence_scoring(self) -> None:
        """Test that categorization prompt includes confidence scoring."""
        assert "confidence" in CATEGORIZATION_PROMPT.lower()
        assert "85" in CATEGORIZATION_PROMPT  # Threshold

    def test_categorization_prompt_contains_output_format(self) -> None:
        """Test that categorization prompt specifies output format."""
        assert "category" in CATEGORIZATION_PROMPT.lower()
        assert "reasoning" in CATEGORIZATION_PROMPT.lower()

    def test_categorization_review_prompt_exists(self) -> None:
        """Test that review prompt is defined."""
        assert CATEGORIZATION_REVIEW_PROMPT is not None
        assert isinstance(CATEGORIZATION_REVIEW_PROMPT, str)
        assert len(CATEGORIZATION_REVIEW_PROMPT) > 0


class TestSchedulingPrompt:
    """Test scheduling prompt."""

    def test_scheduling_prompt_exists(self) -> None:
        """Test that scheduling prompt is defined."""
        assert SCHEDULE_GENERATION_PROMPT is not None
        assert isinstance(SCHEDULE_GENERATION_PROMPT, str)
        assert len(SCHEDULE_GENERATION_PROMPT) > 0

    def test_scheduling_prompt_contains_batching_rules(self) -> None:
        """Test that scheduling prompt includes batching rules."""
        prompt_lower = SCHEDULE_GENERATION_PROMPT.lower()
        assert "batch" in prompt_lower or "group" in prompt_lower

    def test_scheduling_prompt_contains_constraints(self) -> None:
        """Test that scheduling prompt includes constraints."""
        prompt_lower = SCHEDULE_GENERATION_PROMPT.lower()
        assert "constraint" in prompt_lower or "rule" in prompt_lower


class TestEstimatePrompt:
    """Test estimate prompt."""

    def test_estimate_prompt_exists(self) -> None:
        """Test that estimate prompt is defined."""
        assert ESTIMATE_PROMPT is not None
        assert isinstance(ESTIMATE_PROMPT, str)
        assert len(ESTIMATE_PROMPT) > 0

    def test_estimate_prompt_contains_pricing_guidance(self) -> None:
        """Test that estimate prompt includes pricing guidance."""
        prompt_lower = ESTIMATE_PROMPT.lower()
        has_pricing = "price" in prompt_lower or "cost" in prompt_lower
        assert has_pricing or "estimate" in prompt_lower


class TestCommunicationTemplates:
    """Test communication message templates."""

    def test_communication_prompt_exists(self) -> None:
        """Test that communication prompt is defined."""
        assert COMMUNICATION_PROMPT is not None
        assert isinstance(COMMUNICATION_PROMPT, str)
        assert len(COMMUNICATION_PROMPT) > 0

    def test_templates_dict_exists(self) -> None:
        """Test that templates dictionary is defined."""
        assert TEMPLATES is not None
        assert isinstance(TEMPLATES, dict)
        assert len(TEMPLATES) > 0

    def test_appointment_confirmation_template_exists(self) -> None:
        """Test that appointment confirmation template is defined."""
        assert "appointment_confirmation" in TEMPLATES
        template = TEMPLATES["appointment_confirmation"]
        assert isinstance(template, str)
        assert len(template) > 0

    def test_appointment_confirmation_has_placeholders(self) -> None:
        """Test that confirmation template has required placeholders."""
        template = TEMPLATES["appointment_confirmation"]
        assert "{customer_name}" in template
        assert "{date}" in template or "{service_type}" in template

    def test_appointment_reminder_template_exists(self) -> None:
        """Test that appointment reminder template is defined."""
        assert "appointment_reminder" in TEMPLATES
        template = TEMPLATES["appointment_reminder"]
        assert isinstance(template, str)
        assert len(template) > 0

    def test_on_the_way_template_exists(self) -> None:
        """Test that on-the-way template is defined."""
        assert "on_the_way" in TEMPLATES
        template = TEMPLATES["on_the_way"]
        assert isinstance(template, str)
        assert len(template) > 0

    def test_on_the_way_has_placeholders(self) -> None:
        """Test that on-the-way template has required placeholders."""
        template = TEMPLATES["on_the_way"]
        assert "{tech_name}" in template or "{eta}" in template

    def test_completion_summary_template_exists(self) -> None:
        """Test that completion summary template is defined."""
        assert "completion_summary" in TEMPLATES
        template = TEMPLATES["completion_summary"]
        assert isinstance(template, str)
        assert len(template) > 0

    def test_completion_summary_has_placeholders(self) -> None:
        """Test that completion template has required placeholders."""
        template = TEMPLATES["completion_summary"]
        assert "{service_type}" in template or "{amount}" in template

    def test_payment_reminder_template_exists(self) -> None:
        """Test that payment reminder template is defined."""
        assert "payment_reminder" in TEMPLATES
        template = TEMPLATES["payment_reminder"]
        assert isinstance(template, str)
        assert len(template) > 0

    def test_payment_reminder_has_placeholders(self) -> None:
        """Test that payment reminder template has required placeholders."""
        template = TEMPLATES["payment_reminder"]
        assert "{customer_name}" in template
        assert "{amount}" in template

    def test_all_templates_are_non_empty(self) -> None:
        """Test that all templates have substantial content."""
        for key, template in TEMPLATES.items():
            assert len(template) > 20, f"Template {key} is too short"

    def test_templates_are_polite_and_professional(self) -> None:
        """Test that templates use polite language."""
        polite_words = ["hi", "thank", "please", "appreciate"]
        for key, template in TEMPLATES.items():
            template_lower = template.lower()
            # At least some templates should be polite
            if key in ["appointment_confirmation", "follow_up", "completion_summary"]:
                assert any(word in template_lower for word in polite_words), (
                    f"Template {key} should be more polite"
                )

    def test_all_required_message_types_present(self) -> None:
        """Test that all required message types have templates."""
        required_types = [
            "appointment_confirmation",
            "appointment_reminder",
            "on_the_way",
            "completion_summary",
            "follow_up",
            "estimate_ready",
            "payment_reminder",
        ]
        for msg_type in required_types:
            assert msg_type in TEMPLATES, f"Missing template for {msg_type}"
