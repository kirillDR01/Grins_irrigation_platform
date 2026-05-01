"""Seed ``service_offerings`` from Viktor's price-list draft JSON.

Loads all 73 items from
``bughunt/2026-05-01-pricelist-seed-data.json`` (one row per item) and
INSERTs them with the new pricelist columns populated.

The migration is GATED on the ``VIKTOR_PRICELIST_CONFIRMED=true``
environment variable so production deploys cannot accidentally seed
unconfirmed defaults (V1 commercial mulch unit, V2 commercial backflow
$600, V3 commercial drip per_zone_range). Dev/staging may set the flag
freely.

Each item maps cleanly to the new pricelist columns:

* ``key`` → ``slug``
* ``name`` → ``name`` AND ``display_name``
* ``category`` (irrigation/landscaping) →
  ``ServiceCategory.installation`` / ``ServiceCategory.landscaping``.
* ``subcategory`` → ``subcategory``.
* ``customer_type`` → ``customer_type``.
* ``pricing_model`` → ``pricing_model`` (extended enum).
* ``source_text`` → ``source_text``.
* Every remaining field (price_min, price_max, unit, profile_factor,
  tiers, variants, etc.) is stuffed into ``pricing_rule`` JSONB so
  Phase 2/3 can layer Pydantic discriminated unions over the raw
  rule body without altering writes.

``includes_materials`` is auto-derived: ``True`` when
``pricing_model`` ends in ``_plus_materials`` else ``False``.

Revision ID: 20260504_130000
Revises: 20260504_120000
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "20260504_130000"
down_revision: str | None = "20260504_120000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_GATE_ENV = "VIKTOR_PRICELIST_CONFIRMED"
_STANDARD_FIELDS = frozenset(
    {
        "key",
        "name",
        "category",
        "subcategory",
        "customer_type",
        "pricing_model",
        "source_text",
    }
)
# seed.category → ServiceCategory.value
_CATEGORY_MAP = {
    "irrigation": "installation",
    "landscaping": "landscaping",
}


def _resolve_seed_path() -> Path:
    """Return the absolute path of the seed JSON.

    versions/ → migrations/ → grins_platform/ → src/ → <repo_root>/
    """
    here = Path(__file__).resolve()
    repo_root = here.parents[4]
    return repo_root / "bughunt" / "2026-05-01-pricelist-seed-data.json"


def _build_pricing_rule(item: dict[str, Any]) -> dict[str, Any]:
    """Return a dict of every non-standard field on the seed item."""
    return {k: v for k, v in item.items() if k not in _STANDARD_FIELDS}


def _slug_keys() -> list[str]:
    """Return every seed key — used by ``downgrade()``."""
    seed_path = _resolve_seed_path()
    if not seed_path.exists():
        return []
    with seed_path.open() as f:
        data = json.load(f)
    return [it["key"] for it in data.get("items", []) if it.get("key")]


def upgrade() -> None:
    """Insert the 73 seed rows into ``service_offerings``."""
    if os.getenv(_GATE_ENV) != "true":
        msg = (
            f"{_GATE_ENV} env var must be 'true' before this migration "
            "runs. Confirms V1 (commercial mulch per sq ft), "
            "V2 (commercial backflow $600), V3 (commercial drip "
            "per_zone_range) defaults applied in seed JSON. Dev / "
            "staging may set this freely."
        )
        raise RuntimeError(msg)

    seed_path = _resolve_seed_path()
    if not seed_path.exists():
        msg = f"Seed JSON missing at {seed_path}. Cannot run pricelist seed migration."
        raise RuntimeError(msg)

    with seed_path.open() as f:
        data = json.load(f)
    items = data.get("items", [])

    # Use raw INSERT with parameter binding via sa.text() so the JSONB
    # column casts cleanly without bulk_insert table reflection.
    insert_stmt = sa.text(
        """
        INSERT INTO service_offerings (
            id, name, category, pricing_model, description,
            staffing_required, buffer_minutes, lien_eligible,
            requires_prepay, is_active,
            slug, display_name, customer_type, subcategory,
            pricing_rule, includes_materials, source_text,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(), :name, :category, :pricing_model, NULL,
            1, 10, false,
            false, true,
            :slug, :display_name, :customer_type, :subcategory,
            CAST(:pricing_rule AS jsonb), :includes_materials, :source_text,
            now(), now()
        )
        """,
    )

    bind = op.get_bind()
    for item in items:
        seed_category = item.get("category", "")
        category_value = _CATEGORY_MAP.get(seed_category)
        if category_value is None:
            msg = (
                f"Unmapped seed category {seed_category!r} on "
                f"item {item.get('key')!r}. Update _CATEGORY_MAP."
            )
            raise RuntimeError(msg)

        pricing_model = item.get("pricing_model", "custom")
        includes_materials = bool(pricing_model.endswith("_plus_materials"))
        pricing_rule = _build_pricing_rule(item)

        bind.execute(
            insert_stmt,
            {
                "name": item["name"],
                "category": category_value,
                "pricing_model": pricing_model,
                "slug": item["key"],
                "display_name": item["name"],
                "customer_type": item.get("customer_type"),
                "subcategory": item.get("subcategory"),
                "pricing_rule": json.dumps(pricing_rule),
                "includes_materials": includes_materials,
                "source_text": item.get("source_text"),
            },
        )


def downgrade() -> None:
    """Delete every seeded row by slug."""
    keys = _slug_keys()
    if not keys:
        return
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM service_offerings WHERE slug = ANY(:slugs)",
        ),
        {"slugs": keys},
    )
