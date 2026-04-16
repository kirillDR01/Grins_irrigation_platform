"""Unit tests for :mod:`grins_platform.models.enums`.

H-4 (bughunt 2026-04-16): pin the :class:`PaymentMethod` membership so
``credit_card``, ``ach``, and ``other`` are present while the legacy
``stripe`` value is preserved untouched (existing rows must still
validate against the enum).
"""

from __future__ import annotations

from grins_platform.models.enums import PaymentMethod


def test_payment_method_has_credit_card_ach_other_and_retains_legacy() -> None:
    """All eight values must be members of :class:`PaymentMethod`.

    The H-4 fix extends the enum; it does NOT remove the legacy
    ``stripe`` member because historical invoices still carry that
    value in the database.
    """
    values = {m.value for m in PaymentMethod}

    expected = {
        "cash",
        "check",
        "venmo",
        "zelle",
        "stripe",
        "credit_card",
        "ach",
        "other",
    }

    assert values == expected, (
        f"PaymentMethod membership drift: missing={expected - values}, "
        f"unexpected={values - expected}"
    )


def test_payment_method_stripe_retained_for_legacy_rows() -> None:
    """``stripe`` must remain a valid enum member.

    The H-4 decision rejected any data migration that would rewrite
    historical rows, so the value stays in the enum. If this test ever
    fails, confirm with the product owner before removing.
    """
    assert PaymentMethod.STRIPE.value == "stripe"


def test_payment_method_new_spec_values_available() -> None:
    """The three newly-added spec values must be addressable as members."""
    assert PaymentMethod.CREDIT_CARD.value == "credit_card"
    assert PaymentMethod.ACH.value == "ach"
    assert PaymentMethod.OTHER.value == "other"
