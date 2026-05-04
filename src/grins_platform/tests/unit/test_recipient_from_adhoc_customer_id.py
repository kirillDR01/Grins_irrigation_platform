"""Bug #1 — recipient construction strategy regression guard.

Per the plan's resolved strategy (master-plan-run-findings 2026-05-04
Phase 3): ``Recipient.from_adhoc`` is intentionally NOT extended with a
``customer_id`` kwarg. Calling that ``from_adhoc`` factory with a
customer FK would conflate semantics (a customer-keyed send is not
"ad hoc"). Instead, ``SMSService.send_automated_message`` dispatches
the right ``Recipient`` construction directly.

These tests pin both halves of that contract:

1. ``Recipient.from_adhoc(phone=...)`` legacy path returns a Recipient
   with both FKs None — regression guard for the ad-hoc fallback path
   used by callers without a Lead/Customer in scope.
2. Direct ``Recipient(...)`` construction (the pattern used by the
   new dispatch in ``send_automated_message``) carries customer_id /
   lead_id correctly.

Validates: ``.agents/plans/master-plan-run-findings-bug-resolution-2026-05-04.md``
Phase 3 / Task 3.7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from grins_platform.services.sms.recipient import Recipient

pytestmark = pytest.mark.unit


class TestRecipientFromAdhocLegacy:
    def test_phone_only_returns_recipient_with_no_fks(self) -> None:
        r = Recipient.from_adhoc(phone="+19527373312")
        assert r.phone == "+19527373312"
        assert r.source_type == "ad_hoc"
        assert r.customer_id is None
        assert r.lead_id is None

    def test_optional_lead_id_passes_through(self) -> None:
        """Existing kwarg ``lead_id`` (ghost-lead support) still works."""
        lid = uuid4()
        r = Recipient.from_adhoc(phone="+19527373312", lead_id=lid)
        assert r.lead_id == lid
        assert r.customer_id is None
        assert r.source_type == "ad_hoc"


class TestRecipientDirectConstruction:
    """Mirror the construction patterns used by send_automated_message."""

    def test_customer_keyed_construction_carries_fk(self) -> None:
        cid = uuid4()
        r = Recipient(
            phone="+19527373312",
            source_type="customer",
            customer_id=cid,
        )
        assert r.customer_id == cid
        assert r.lead_id is None
        assert r.source_type == "customer"

    def test_lead_keyed_construction_carries_fk(self) -> None:
        lid = uuid4()
        r = Recipient(
            phone="+19527373312",
            source_type="lead",
            lead_id=lid,
        )
        assert r.lead_id == lid
        assert r.customer_id is None
        assert r.source_type == "lead"
