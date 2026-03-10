"""Property test for suppression list enforcement.

Property 10: Suppression List Enforcement
For any customer on the suppression list, Email_Service never sends
COMMERCIAL email; suppression entry never auto-removed.

Validates: Requirements 67.5, 67.7
"""

from __future__ import annotations

import pytest
from hypothesis import (
    assume,
    given,
    settings,
    strategies as st,
)

from grins_platform.services.email_config import EmailSettings
from grins_platform.services.email_service import EmailService

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

emails = st.from_regex(r"[a-z]{1,10}@[a-z]{1,8}\.(com|org|net)", fullmatch=True)


def _settings() -> EmailSettings:
    return EmailSettings(
        email_api_key="test-key",
        company_physical_address="123 Main St, Minneapolis, MN 55401",
        stripe_customer_portal_url="https://billing.stripe.com/test",
    )


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSuppressionListEnforcement:
    """Property 10 — suppressed emails never receive commercial email,
    and suppression entries are never auto-removed."""

    @given(email=emails)
    @settings(max_examples=50)
    def test_suppressed_email_blocked_for_commercial(self, email: str) -> None:
        """Any email on suppression list is blocked (Req 67.5)."""
        svc = EmailService(settings=_settings())
        suppressed = {email}
        assert (
            svc.check_suppression_and_opt_in(
                email,
                email_opt_in=True,
                suppressed_emails=suppressed,
            )
            is False
        )

    @given(email=emails)
    @settings(max_examples=50)
    def test_suppressed_email_blocked_case_insensitive(self, email: str) -> None:
        """Suppression check is case-insensitive (Req 67.5)."""
        svc = EmailService(settings=_settings())
        suppressed = {email.upper()}
        assert (
            svc.check_suppression_and_opt_in(
                email.lower(),
                email_opt_in=True,
                suppressed_emails=suppressed,
            )
            is False
        )

    @given(
        suppressed_email=emails,
        other_email=emails,
    )
    @settings(max_examples=50)
    def test_non_suppressed_email_allowed_when_opted_in(
        self,
        suppressed_email: str,
        other_email: str,
    ) -> None:
        """Emails NOT on suppression list pass when opted in (Req 67.5)."""
        assume(suppressed_email.lower() != other_email.lower())
        svc = EmailService(settings=_settings())
        suppressed = {suppressed_email}
        assert (
            svc.check_suppression_and_opt_in(
                other_email,
                email_opt_in=True,
                suppressed_emails=suppressed,
            )
            is True
        )

    @given(email=emails, extra_emails=st.lists(emails, min_size=0, max_size=10))
    @settings(max_examples=50)
    def test_suppression_set_never_shrinks(
        self,
        email: str,
        extra_emails: list[str],
    ) -> None:
        """Suppression set is never auto-reduced (Req 67.7).

        After multiple check calls the set retains all entries.
        """
        svc = EmailService(settings=_settings())
        suppressed = {email, *extra_emails}
        original_size = len(suppressed)

        # Perform several checks — set must not lose entries
        for e in suppressed:
            svc.check_suppression_and_opt_in(
                e,
                email_opt_in=True,
                suppressed_emails=suppressed,
            )

        assert len(suppressed) == original_size
