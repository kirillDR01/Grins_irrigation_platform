"""Unit tests for DuplicateDetectionService and CustomerMergeService.

Tests scoring algorithm with various signal combinations, merge blockers
(dual Stripe subscriptions), reassignment logic, and soft-delete.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 6.4, 6.5, 6.7
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.exceptions import CustomerNotFoundError, MergeConflictError
from grins_platform.schemas.customer_merge import MergeFieldSelection
from grins_platform.services.customer_merge_service import (
    _REASSIGN_TABLES,
    CustomerMergeService,
)
from grins_platform.services.duplicate_detection_service import (
    MAX_SCORE,
    WEIGHT_ADDRESS,
    WEIGHT_EMAIL,
    WEIGHT_NAME,
    WEIGHT_PHONE,
    DuplicateDetectionService,
    _normalize_address,
    _normalize_email,
    _normalize_name,
    _normalize_phone,
    jaro_winkler_similarity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_customer(
    *,
    customer_id=None,
    first_name="John",
    last_name="Doe",
    phone="6125551234",
    email=None,
    address=None,
    zip_code=None,
    has_property=True,
):
    c = MagicMock()
    c.id = customer_id or uuid4()
    c.first_name = first_name
    c.last_name = last_name
    c.phone = phone
    c.email = email
    c.is_deleted = False
    c.deleted_at = None
    c.merged_into_customer_id = None
    c.lead_source = None
    c.internal_notes = None
    c.is_priority = False
    c.is_red_flag = False
    c.is_slow_payer = False
    c.sms_opt_in = False
    c.email_opt_in = False

    if has_property and address:
        prop = MagicMock()
        prop.is_primary = True
        prop.address = address
        prop.zip_code = zip_code
        c.properties = [prop]
    else:
        c.properties = []
    return c


# ===========================================================================
# DuplicateDetectionService — Scoring Algorithm
# ===========================================================================


class TestDuplicateScoring:
    """Tests for compute_score with various signal combinations."""

    svc = DuplicateDetectionService()

    @pytest.mark.unit
    def test_phone_match_scores_60(self):
        a = _mock_customer(phone="6125551234")
        b = _mock_customer(phone="6125551234")
        score, signals = self.svc.compute_score(a, b)
        assert signals.get("phone") is True
        assert score >= WEIGHT_PHONE

    @pytest.mark.unit
    def test_email_match_scores_50(self):
        a = _mock_customer(phone="6125551111", email="test@example.com")
        b = _mock_customer(phone="6125552222", email="TEST@Example.COM")
        score, signals = self.svc.compute_score(a, b)
        assert signals.get("email") is True
        assert score >= WEIGHT_EMAIL

    @pytest.mark.unit
    def test_name_similarity_scores_25(self):
        a = _mock_customer(
            first_name="John",
            last_name="Smith",
            phone=None,
            has_property=False,
        )
        b = _mock_customer(
            first_name="John",
            last_name="Smith",
            phone=None,
            has_property=False,
        )
        score, signals = self.svc.compute_score(a, b)
        assert "name_similarity" in signals
        assert score >= WEIGHT_NAME

    @pytest.mark.unit
    def test_address_match_scores_20(self):
        a = _mock_customer(phone=None, address="123 Main Street", zip_code="55401")
        b = _mock_customer(phone=None, address="123 Main St", zip_code="55401")
        score, signals = self.svc.compute_score(a, b)
        assert signals.get("address") is True
        assert score >= WEIGHT_ADDRESS

    @pytest.mark.unit
    def test_zip_last_name_match_scores_10(self):
        a = _mock_customer(
            first_name="Alice",
            last_name="Johnson",
            phone=None,
            address="100 Oak Ave",
            zip_code="55401",
        )
        b = _mock_customer(
            first_name="Bob",
            last_name="Johnson",
            phone=None,
            address="200 Elm Dr",
            zip_code="55401",
        )
        _score, signals = self.svc.compute_score(a, b)
        assert signals.get("zip_last_name") is True

    @pytest.mark.unit
    def test_no_signals_scores_zero(self):
        a = _mock_customer(
            first_name="Aaa",
            last_name="Bbb",
            phone=None,
            has_property=False,
        )
        b = _mock_customer(
            first_name="Xxx",
            last_name="Yyy",
            phone=None,
            has_property=False,
        )
        score, signals = self.svc.compute_score(a, b)
        assert score == 0
        assert len(signals) == 0

    @pytest.mark.unit
    def test_all_signals_capped_at_100(self):
        a = _mock_customer(
            first_name="John",
            last_name="Doe",
            phone="6125551234",
            email="john@test.com",
            address="123 Main St",
            zip_code="55401",
        )
        b = _mock_customer(
            first_name="John",
            last_name="Doe",
            phone="6125551234",
            email="john@test.com",
            address="123 Main St",
            zip_code="55401",
        )
        score, _ = self.svc.compute_score(a, b)
        assert score == MAX_SCORE

    @pytest.mark.unit
    def test_phone_plus_email_combined(self):
        a = _mock_customer(phone="6125551234", email="a@b.com")
        b = _mock_customer(phone="6125551234", email="a@b.com")
        score, signals = self.svc.compute_score(a, b)
        # Both signals fire; score capped at MAX_SCORE
        assert signals.get("phone") is True
        assert signals.get("email") is True
        assert score == MAX_SCORE

    @pytest.mark.unit
    def test_none_phone_no_match(self):
        a = _mock_customer(phone=None, has_property=False)
        b = _mock_customer(phone=None, has_property=False)
        # Different names to avoid name signal
        a.first_name = "Aaa"
        a.last_name = "Bbb"
        b.first_name = "Xxx"
        b.last_name = "Yyy"
        _score, signals = self.svc.compute_score(a, b)
        assert "phone" not in signals

    @pytest.mark.unit
    def test_dissimilar_names_no_name_signal(self):
        a = _mock_customer(
            first_name="Alice",
            last_name="Wonderland",
            phone=None,
            has_property=False,
        )
        b = _mock_customer(
            first_name="Zephyr",
            last_name="Quantum",
            phone=None,
            has_property=False,
        )
        _score, signals = self.svc.compute_score(a, b)
        assert "name_similarity" not in signals


# ===========================================================================
# Normalization helpers
# ===========================================================================


class TestNormalization:
    @pytest.mark.unit
    def test_normalize_email_lowercases(self):
        assert _normalize_email("FOO@BAR.COM") == "foo@bar.com"

    @pytest.mark.unit
    def test_normalize_email_none(self):
        assert _normalize_email(None) is None

    @pytest.mark.unit
    def test_normalize_phone_e164(self):
        result = _normalize_phone("6125551234")
        assert result is not None
        assert result.startswith("+")

    @pytest.mark.unit
    def test_normalize_phone_none(self):
        assert _normalize_phone(None) is None

    @pytest.mark.unit
    def test_normalize_address_abbreviations(self):
        assert _normalize_address("123 Main Street") == "123 main st"

    @pytest.mark.unit
    def test_normalize_address_none(self):
        assert _normalize_address(None) is None

    @pytest.mark.unit
    def test_normalize_name_strips_accents(self):
        assert _normalize_name("José") == "jose"

    @pytest.mark.unit
    def test_jaro_winkler_identical(self):
        assert jaro_winkler_similarity("hello", "hello") == 1.0

    @pytest.mark.unit
    def test_jaro_winkler_empty(self):
        assert jaro_winkler_similarity("", "hello") == 0.0


# ===========================================================================
# CustomerMergeService — Blockers
# ===========================================================================


class TestMergeBlockers:
    """Tests for check_merge_blockers (dual Stripe subscriptions)."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_blockers_when_no_subscriptions(self):
        svc = CustomerMergeService()
        db = AsyncMock()
        db.execute.return_value = MagicMock(all=MagicMock(return_value=[]))

        blockers = await svc.check_merge_blockers(db, uuid4(), uuid4())
        assert blockers == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_blockers_when_one_subscription(self):
        svc = CustomerMergeService()
        db = AsyncMock()
        row = MagicMock()
        db.execute.return_value = MagicMock(all=MagicMock(return_value=[row]))

        blockers = await svc.check_merge_blockers(db, uuid4(), uuid4())
        assert blockers == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_blocker_when_both_have_subscriptions(self):
        svc = CustomerMergeService()
        db = AsyncMock()
        db.execute.return_value = MagicMock(
            all=MagicMock(return_value=[MagicMock(), MagicMock()]),
        )

        blockers = await svc.check_merge_blockers(db, uuid4(), uuid4())
        assert len(blockers) == 1
        assert "Stripe" in blockers[0]


# ===========================================================================
# CustomerMergeService — Execute Merge
# ===========================================================================


class TestExecuteMerge:
    """Tests for execute_merge: reassignment, soft-delete, audit log."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_merge_reassigns_all_tables(self):
        primary_id, duplicate_id = uuid4(), uuid4()
        primary = _mock_customer(customer_id=primary_id)
        duplicate = _mock_customer(customer_id=duplicate_id)
        svc = CustomerMergeService()
        db = AsyncMock()

        with (
            patch.object(svc, "_get_customer", side_effect=[primary, duplicate]),
            patch.object(svc, "check_merge_blockers", return_value=[]),
        ):
            await svc.execute_merge(db, primary_id, duplicate_id, [], uuid4())

        reassign_calls = [
            c
            for c in db.execute.call_args_list
            if hasattr(c[0][0], "text") and "SET customer_id" in str(c[0][0].text)
        ]
        assert len(reassign_calls) == len(_REASSIGN_TABLES)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_merge_soft_deletes_duplicate(self):
        primary_id, duplicate_id = uuid4(), uuid4()
        primary = _mock_customer(customer_id=primary_id)
        duplicate = _mock_customer(customer_id=duplicate_id)
        svc = CustomerMergeService()
        db = AsyncMock()

        with (
            patch.object(svc, "_get_customer", side_effect=[primary, duplicate]),
            patch.object(svc, "check_merge_blockers", return_value=[]),
        ):
            await svc.execute_merge(db, primary_id, duplicate_id, [], uuid4())

        assert duplicate.merged_into_customer_id == primary_id
        assert duplicate.is_deleted is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_merge_writes_audit_log(self):
        primary_id, duplicate_id, admin_id = uuid4(), uuid4(), uuid4()
        primary = _mock_customer(customer_id=primary_id)
        duplicate = _mock_customer(customer_id=duplicate_id)
        svc = CustomerMergeService()
        db = AsyncMock()

        with (
            patch.object(svc, "_get_customer", side_effect=[primary, duplicate]),
            patch.object(svc, "check_merge_blockers", return_value=[]),
        ):
            await svc.execute_merge(
                db,
                primary_id,
                duplicate_id,
                [],
                admin_id=admin_id,
            )

        audit_entries = [
            c[0][0]
            for c in db.add.call_args_list
            if hasattr(c[0][0], "action") and c[0][0].action == "customer_merge"
        ]
        assert len(audit_entries) == 1
        assert audit_entries[0].resource_id == primary_id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_merge_raises_on_blocker(self):
        svc = CustomerMergeService()
        db = AsyncMock()
        primary = _mock_customer()
        duplicate = _mock_customer()

        with (
            patch.object(svc, "_get_customer", side_effect=[primary, duplicate]),
            patch.object(
                svc,
                "check_merge_blockers",
                return_value=["Both customers have active Stripe subscriptions."],
            ),
            pytest.raises(MergeConflictError),
        ):
            await svc.execute_merge(db, uuid4(), uuid4(), [])

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_merge_applies_field_selections(self):
        primary_id, duplicate_id = uuid4(), uuid4()
        primary = _mock_customer(
            customer_id=primary_id,
            first_name="Alice",
            last_name="Smith",
        )
        duplicate = _mock_customer(
            customer_id=duplicate_id,
            first_name="Bob",
            last_name="Jones",
        )
        selections = [MergeFieldSelection(field_name="first_name", source="b")]
        svc = CustomerMergeService()
        db = AsyncMock()

        with (
            patch.object(svc, "_get_customer", side_effect=[primary, duplicate]),
            patch.object(svc, "check_merge_blockers", return_value=[]),
        ):
            await svc.execute_merge(
                db,
                primary_id,
                duplicate_id,
                selections,
                uuid4(),
            )

        assert primary.first_name == "Bob"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_merge_defaults_nonempty_value(self):
        """When no field selection, non-empty duplicate value fills empty primary."""
        primary_id, duplicate_id = uuid4(), uuid4()
        primary = _mock_customer(customer_id=primary_id, email=None)
        duplicate = _mock_customer(customer_id=duplicate_id, email="dup@test.com")
        svc = CustomerMergeService()
        db = AsyncMock()

        with (
            patch.object(svc, "_get_customer", side_effect=[primary, duplicate]),
            patch.object(svc, "check_merge_blockers", return_value=[]),
        ):
            await svc.execute_merge(db, primary_id, duplicate_id, [], uuid4())

        assert primary.email == "dup@test.com"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_merge_customer_not_found(self):
        svc = CustomerMergeService()
        db = AsyncMock()

        with (
            patch.object(
                svc,
                "_get_customer",
                side_effect=CustomerNotFoundError(uuid4()),
            ),
            pytest.raises(CustomerNotFoundError),
        ):
            await svc.execute_merge(db, uuid4(), uuid4(), [])
