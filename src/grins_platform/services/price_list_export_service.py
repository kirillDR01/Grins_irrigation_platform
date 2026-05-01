"""
PriceListExportService — auto-generate ``pricelist.md``.

Renders the current ``service_offerings`` table as a Markdown document
grouped by ``customer_type`` then by ``category``. The static
``pricelist.md`` at the repo root is retired in favour of this on-demand
export (umbrella plan Phase 2 / decision P8).

The service is read-only and stateless; cache invalidation is handled
upstream by the API layer (``ETag`` based on ``MAX(updated_at)``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.service_offering import ServiceOffering

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _format_currency(value: object) -> str:
    """Render a JSON-decoded number as ``$X.YY`` or pass through."""
    if isinstance(value, (int, float)):
        return f"${value:,.2f}"
    if isinstance(value, str):
        try:
            return f"${float(value):,.2f}"
        except ValueError:
            return value
    return "—"


def _flat_summary(rule: dict[str, object]) -> str | None:
    if "price" in rule:
        return _format_currency(rule["price"])
    return None


def _flat_range_summary(rule: dict[str, object]) -> str | None:
    if "price_min" in rule and "price_max" in rule:
        low = _format_currency(rule["price_min"])
        high = _format_currency(rule["price_max"])
        return f"{low} - {high}"
    return None


def _per_unit_summary(rule: dict[str, object]) -> str | None:
    if "price_per_unit" not in rule:
        return None
    unit = rule.get("unit", "unit")
    return f"{_format_currency(rule['price_per_unit'])} / {unit}"


def _per_unit_range_summary(rule: dict[str, object]) -> str | None:
    if "price_per_unit_min" not in rule:
        return None
    unit = rule.get("unit", "unit")
    low = _format_currency(rule["price_per_unit_min"])
    high = _format_currency(rule["price_per_unit_max"])
    return f"{low} - {high} / {unit}"


def _per_zone_range_summary(rule: dict[str, object]) -> str | None:
    if "price_per_zone_min" not in rule:
        return None
    low = _format_currency(rule["price_per_zone_min"])
    high = _format_currency(rule["price_per_zone_max"])
    return f"{low} - {high} / zone"


def _hourly_summary(rule: dict[str, object]) -> str | None:
    if "price_per_hour" not in rule:
        return None
    return f"{_format_currency(rule['price_per_hour'])} / hr"


def _conditional_fee_summary(rule: dict[str, object]) -> str | None:
    if "price" not in rule:
        return None
    waived = rule.get("waived_when", "on approval")
    return f"{_format_currency(rule['price'])} (waived {waived})"


_Summarizer = Callable[[dict[str, object]], "str | None"]

_MODEL_SUMMARIZERS: dict[str, _Summarizer] = {
    "flat": _flat_summary,
    "flat_plus_materials": _flat_summary,
    "flat_range": _flat_range_summary,
    "per_unit_flat": _per_unit_summary,
    "per_unit_flat_plus_materials": _per_unit_summary,
    "per_unit_range": _per_unit_range_summary,
    "per_zone_range": _per_zone_range_summary,
    "hourly": _hourly_summary,
    "conditional_fee": _conditional_fee_summary,
}


def _summarize_pricing_rule(model: str, rule: dict[str, object] | None) -> str:
    """One-line summary of a pricing_rule for the markdown table."""
    if rule is None:
        return "—"

    summarizer = _MODEL_SUMMARIZERS.get(model)
    if summarizer is not None:
        result = summarizer(rule)
        if result is not None:
            return result

    # Fallback: render up to the three first numeric keys.
    bits: list[str] = []
    for k, v in rule.items():
        if k == "range_anchors":
            continue
        if isinstance(v, (int, float)):
            bits.append(f"{k}={_format_currency(v)}")
        if len(bits) >= 3:
            break
    return ", ".join(bits) if bits else "see rule"


class PriceListExportService(LoggerMixin):
    """Render the current pricelist as a Markdown document."""

    DOMAIN = "service"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self._session = session

    async def export_to_markdown(self) -> str:
        """Return a Markdown document for ``pricelist.md``.

        The document is grouped by ``customer_type`` (residential first,
        commercial second, then ``unset``) and within each group by
        ``category`` ASC, then ``name`` ASC.

        Inactive rows are omitted. The cache key for the API layer is the
        last ``updated_at`` from the result set.
        """
        self.log_started("export_to_markdown")

        stmt = (
            select(ServiceOffering)
            .where(ServiceOffering.is_active.is_(True))
            .order_by(
                ServiceOffering.customer_type.asc(),
                ServiceOffering.category.asc(),
                ServiceOffering.name.asc(),
            )
        )
        result = await self._session.execute(stmt)
        offerings = list(result.scalars().all())

        if not offerings:
            self.log_completed("export_to_markdown", count=0)
            return self._render_empty()

        lines: list[str] = []
        lines.append("<!-- AUTO-GENERATED by PriceListExportService — do not edit. -->")
        lines.append(
            f"<!-- Generated at {datetime.now(timezone.utc).isoformat()} UTC -->"
        )
        lines.append("")
        lines.append("# Grin's Irrigation — Pricelist")
        lines.append("")

        # Group by customer_type → category.
        by_customer: dict[str, list[ServiceOffering]] = {}
        for o in offerings:
            ctype = o.customer_type or "unset"
            by_customer.setdefault(ctype, []).append(o)

        order = [
            ("residential", "Residential"),
            ("commercial", "Commercial"),
            ("unset", "Other"),
        ]
        for key, label in order:
            bucket = by_customer.get(key, [])
            if not bucket:
                continue
            lines.append(f"## {label}")
            lines.append("")
            by_category: dict[str, list[ServiceOffering]] = {}
            for o in bucket:
                by_category.setdefault(o.category, []).append(o)

            for category in sorted(by_category):
                lines.append(f"### {category.title()}")
                lines.append("")
                lines.append("| Service | Pricing model | Price | Materials |")
                lines.append("| --- | --- | --- | --- |")
                for o in by_category[category]:
                    name = o.display_name or o.name
                    price = _summarize_pricing_rule(o.pricing_model, o.pricing_rule)
                    materials = "yes" if o.includes_materials else "—"
                    lines.append(
                        f"| {name} | `{o.pricing_model}` | {price} | {materials} |"
                    )
                lines.append("")

        self.log_completed("export_to_markdown", count=len(offerings))
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _render_empty() -> str:
        """Render an empty-state document."""
        return (
            "<!-- AUTO-GENERATED — pricelist is empty. -->\n"
            "# Grin's Irrigation — Pricelist\n\n"
            "_No active offerings._\n"
        )
