"""Align tier included_services descriptions with marketing copy.

The customer-facing website in the Grins_irrigation repo describes the
services as "Spring Start-Up", "Mid-Season Inspection & Tune Up",
"Fall Winterization", and "Monthly Monitoring Visits and Tune Ups". The
onboarding week picker surfaces these description strings, so they
must match what the customer was sold.

Internal job_type identifiers stay unchanged (spring_startup,
mid_season_inspection, fall_winterization, monthly_visit).

Revision ID: 20260414_100300
Revises: 20260414_100200
"""

import json
from collections.abc import Sequence
from typing import Any, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260414_100300"
down_revision: Union[str, None] = "20260414_100200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# New marketing-aligned label set
_SPRING_NEW = "Spring Start-Up"
_MID_SEASON_NEW = "Mid-Season Inspection & Tune Up"
_FALL_NEW = "Fall Winterization"
_MONTHLY_NEW = "Monthly Monitoring Visits & Tune Ups (May-Sep)"

# Previous descriptions (for downgrade)
_SPRING_OLD = "Spring system activation and inspection"
_MID_SEASON_OLD = "Mid-season system inspection and adjustment"
_FALL_OLD = "Fall system winterization and blowout"
_MONTHLY_OLD = "Monthly system check and adjustment (May-Sep)"


def _essential_services(spring: str, fall: str) -> list[dict[str, Any]]:
    return [
        {"service_type": "spring_startup", "frequency": "1x", "description": spring},
        {"service_type": "fall_winterization", "frequency": "1x", "description": fall},
    ]


def _professional_services(
    spring: str, mid: str, fall: str,
) -> list[dict[str, Any]]:
    return [
        {"service_type": "spring_startup", "frequency": "1x", "description": spring},
        {
            "service_type": "mid_season_inspection",
            "frequency": "1x",
            "description": mid,
        },
        {"service_type": "fall_winterization", "frequency": "1x", "description": fall},
    ]


def _premium_services(
    spring: str, monthly: str, fall: str,
) -> list[dict[str, Any]]:
    return [
        {"service_type": "spring_startup", "frequency": "1x", "description": spring},
        {"service_type": "monthly_visit", "frequency": "5x", "description": monthly},
        {"service_type": "fall_winterization", "frequency": "1x", "description": fall},
    ]


def _winterization_services(fall: str) -> list[dict[str, Any]]:
    return [
        {"service_type": "fall_winterization", "frequency": "1x", "description": fall},
    ]


def _apply(
    spring: str, mid: str, fall: str, monthly: str,
) -> None:
    conn = op.get_bind()

    by_slug: dict[str, list[dict[str, Any]]] = {
        "essential-residential": _essential_services(spring, fall),
        "essential-commercial": _essential_services(spring, fall),
        "professional-residential": _professional_services(spring, mid, fall),
        "professional-commercial": _professional_services(spring, mid, fall),
        "premium-residential": _premium_services(spring, monthly, fall),
        "premium-commercial": _premium_services(spring, monthly, fall),
        "winterization-only-residential": _winterization_services(fall),
        "winterization-only-commercial": _winterization_services(fall),
    }

    for slug, services in by_slug.items():
        conn.execute(
            sa.text(
                "UPDATE service_agreement_tiers "
                "SET included_services = CAST(:services AS json), "
                "    updated_at = NOW() "
                "WHERE slug = :slug"
            ),
            {"services": json.dumps(services), "slug": slug},
        )


def upgrade() -> None:
    _apply(_SPRING_NEW, _MID_SEASON_NEW, _FALL_NEW, _MONTHLY_NEW)


def downgrade() -> None:
    _apply(_SPRING_OLD, _MID_SEASON_OLD, _FALL_OLD, _MONTHLY_OLD)
