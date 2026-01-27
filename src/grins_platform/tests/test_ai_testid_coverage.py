"""Property-based tests for data-testid attribute coverage in AI components.

Property 15: Data-testid Attribute Coverage
All AI components must have required data-testid attributes for agent-browser testing.
"""

import re
from pathlib import Path

import pytest
from hypothesis import (
    given,
    strategies as st,
)

# Required data-testid attributes for each AI component
# These are the minimum required testids for agent-browser validation
REQUIRED_TESTIDS: dict[str, set[str]] = {
    "AILoadingState": {"ai-loading-state"},
    "AIErrorState": {"ai-error-state"},
    "AIStreamingText": {"ai-streaming-text"},
    "AIQueryChat": {
        "ai-chat-input",
        "ai-chat-submit",
        "ai-chat-clear",
    },
    "AIScheduleGenerator": {
        "ai-schedule-generator",
    },
    "AICategorization": {
        "ai-categorization",
        "approve-all-btn",
    },
    "AICommunicationDrafts": {
        "ai-communication-drafts",
    },
    "AIEstimateGenerator": {
        "ai-estimate-generator",
    },
    "MorningBriefing": {
        "morning-briefing",
        "greeting",
        "overnight-requests",
        "today-schedule",
        "pending-communications",
        "quick-actions",
    },
    "CommunicationsQueue": {
        "communications-queue",
        "message-filter",
        "message-search",
        "pending-messages",
        "send-all-btn",
    },
}


def extract_testids_from_file(file_path: Path) -> set[str]:
    """Extract all data-testid values from a TypeScript/TSX file."""
    content = file_path.read_text()

    # Match data-testid="value" or data-testid='value' or data-testid={`value`}
    patterns = [
        r'data-testid=["\']([^"\']+)["\']',
        r"data-testid=\{`([^`]+)`\}",
        r'data-testid=\{["\']([^"\']+)["\']\}',
    ]

    testids = set()
    for pattern in patterns:
        matches = re.findall(pattern, content)
        testids.update(matches)

    return testids


def get_component_file_path(component_name: str) -> Path:
    """Get the file path for a component."""
    frontend_dir = Path("frontend/src/features/ai/components")
    return frontend_dir / f"{component_name}.tsx"


@pytest.mark.unit
class TestDataTestidCoverage:
    """Test that all AI components have required data-testid attributes."""

    def test_all_components_have_required_testids(self) -> None:
        """Property 15: All AI components must have required data-testid attributes.

        This test verifies that each AI component file contains all the
        data-testid attributes required for agent-browser testing.

        Validates: Requirements 19.8
        """
        missing_testids: dict[str, set[str]] = {}

        for component_name, required_testids in REQUIRED_TESTIDS.items():
            file_path = get_component_file_path(component_name)

            if not file_path.exists():
                missing_testids[component_name] = required_testids
                continue

            actual_testids = extract_testids_from_file(file_path)
            missing = required_testids - actual_testids

            if missing:
                missing_testids[component_name] = missing

        # Assert no missing testids
        if missing_testids:
            error_msg = "Missing data-testid attributes:\n"
            for component, testids in missing_testids.items():
                error_msg += f"  {component}: {', '.join(sorted(testids))}\n"
            pytest.fail(error_msg)

    @given(
        component_name=st.sampled_from(list(REQUIRED_TESTIDS.keys())),
    )
    def test_component_testids_are_unique(self, component_name: str) -> None:
        """Property: Static data-testid values should be unique within a component.

        This property test verifies that each static data-testid value appears
        only once in a component file (no duplicates). Dynamic testids with
        template literals are allowed to repeat.
        """
        file_path = get_component_file_path(component_name)

        if not file_path.exists():
            pytest.skip(f"Component file not found: {file_path}")

        content = file_path.read_text()

        # Find all testid occurrences
        patterns = [
            r'data-testid=["\']([^"\']+)["\']',
            r"data-testid=\{`([^`]+)`\}",
            r'data-testid=\{["\']([^"\']+)["\']\}',
        ]

        all_testids: list[str] = []
        for pattern in patterns:
            matches = re.findall(pattern, content)
            all_testids.extend(matches)

        # Filter out dynamic testids (contain $ or {)
        static_testids = [
            tid for tid in all_testids if "$" not in tid and "{" not in tid
        ]

        # Check for duplicates in static testids only
        testid_counts: dict[str, int] = {}
        for testid in static_testids:
            testid_counts[testid] = testid_counts.get(testid, 0) + 1

        duplicates = {tid: count for tid, count in testid_counts.items() if count > 1}

        if duplicates:
            error_msg = f"Duplicate static data-testid values in {component_name}:\n"
            for testid, count in duplicates.items():
                error_msg += f"  '{testid}' appears {count} times\n"
            pytest.fail(error_msg)

    def test_testid_naming_convention(self) -> None:
        """Property: data-testid values should follow kebab-case naming convention.

        This test verifies that static data-testid values use kebab-case
        (lowercase with hyphens) for consistency. Dynamic testids with
        template literals are allowed.
        """
        invalid_testids: dict[str, list[str]] = {}

        for component_name in REQUIRED_TESTIDS:
            file_path = get_component_file_path(component_name)

            if not file_path.exists():
                continue

            actual_testids = extract_testids_from_file(file_path)

            # Check each testid follows kebab-case (skip dynamic ones with $)
            invalid = []
            for testid in actual_testids:
                # Skip dynamic testids (contain $ for template literals)
                if "$" in testid or "{" in testid:
                    continue

                # Valid kebab-case: lowercase letters, numbers, and hyphens only
                if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", testid):
                    invalid.append(testid)

            if invalid:
                invalid_testids[component_name] = invalid

        if invalid_testids:
            error_msg = "Invalid data-testid naming (should be kebab-case):\n"
            for component, testids in invalid_testids.items():
                error_msg += f"  {component}: {', '.join(testids)}\n"
            pytest.fail(error_msg)
