"""Unit tests for CustomerTag model.

Validates: Requirements 12.1, 12.2
"""

from __future__ import annotations

import uuid

import pytest

from grins_platform.models.customer_tag import CustomerTag


@pytest.mark.unit
class TestCustomerTagModel:
    """Tests for CustomerTag SQLAlchemy model."""

    def test_model_creation_with_defaults(self) -> None:
        """CustomerTag can be instantiated with required fields."""
        customer_id = uuid.uuid4()
        tag = CustomerTag(
            customer_id=customer_id,
            label="VIP",
            tone="neutral",
            source="manual",
        )
        assert tag.customer_id == customer_id
        assert tag.label == "VIP"
        assert tag.tone == "neutral"
        assert tag.source == "manual"

    def test_model_default_tone_column_default(self) -> None:
        """CustomerTag column default for tone is 'neutral'."""
        col = CustomerTag.__table__.c["tone"]
        # SQLAlchemy column-level default (applied on INSERT, not Python construction)
        assert col.default is not None
        assert col.default.arg == "neutral"

    def test_model_default_source_column_default(self) -> None:
        """CustomerTag column default for source is 'manual'."""
        col = CustomerTag.__table__.c["source"]
        assert col.default is not None
        assert col.default.arg == "manual"

    def test_model_all_valid_tones(self) -> None:
        """CustomerTag accepts all valid tone values."""
        valid_tones = ["neutral", "blue", "green", "amber", "violet"]
        for tone in valid_tones:
            tag = CustomerTag(
                customer_id=uuid.uuid4(),
                label="Test",
                tone=tone,
            )
            assert tag.tone == tone

    def test_model_all_valid_sources(self) -> None:
        """CustomerTag accepts both valid source values."""
        for source in ["manual", "system"]:
            tag = CustomerTag(
                customer_id=uuid.uuid4(),
                label="Test",
                source=source,
            )
            assert tag.source == source

    def test_model_label_max_length(self) -> None:
        """CustomerTag accepts label up to 32 characters."""
        label = "A" * 32
        tag = CustomerTag(
            customer_id=uuid.uuid4(),
            label=label,
        )
        assert tag.label == label

    def test_model_repr(self) -> None:
        """CustomerTag __repr__ includes key fields."""
        cid = uuid.uuid4()
        tag = CustomerTag(
            customer_id=cid,
            label="VIP",
            tone="blue",
        )
        r = repr(tag)
        assert "CustomerTag" in r
        assert "VIP" in r
        assert "blue" in r

    def test_model_tablename(self) -> None:
        """CustomerTag maps to customer_tags table."""
        assert CustomerTag.__tablename__ == "customer_tags"

    def test_model_table_args_constraints(self) -> None:
        """CustomerTag has unique constraint and check constraints."""
        constraint_names = {
            c.name for c in CustomerTag.__table_args__ if hasattr(c, "name") and c.name
        }
        assert "uq_customer_tags_customer_label" in constraint_names
        assert "ck_customer_tags_tone" in constraint_names
        assert "ck_customer_tags_source" in constraint_names

    def test_model_customer_id_indexed(self) -> None:
        """customer_id column has an index."""
        col = CustomerTag.__table__.c["customer_id"]
        assert col.index is True

    def test_model_created_at_has_server_default(self) -> None:
        """created_at column has a server_default."""
        col = CustomerTag.__table__.c["created_at"]
        assert col.server_default is not None

    def test_model_id_has_server_default(self) -> None:
        """id column has a server_default (gen_random_uuid)."""
        col = CustomerTag.__table__.c["id"]
        assert col.server_default is not None

    def test_model_customer_fk_cascade(self) -> None:
        """customer_id FK has ON DELETE CASCADE."""
        col = CustomerTag.__table__.c["customer_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert fk.ondelete == "CASCADE"
