"""Unified Recipient value object for all SMS sends.

Normalizes customers, leads, and ad-hoc phones into a single frozen
dataclass, eliminating source-specific branching in send paths.

Validates: Requirements 4.1, 4.2, 4.3, 4.4
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from uuid import UUID

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer
    from grins_platform.models.lead import Lead

SourceType = Literal["customer", "lead", "ad_hoc"]


@dataclass(frozen=True)
class Recipient:
    """Unified target for all SMS sends."""

    phone: str  # E.164
    source_type: SourceType
    customer_id: UUID | None = None
    lead_id: UUID | None = None
    first_name: str | None = None
    last_name: str | None = None

    @classmethod
    def from_customer(cls, customer: Customer) -> Recipient:
        """Create a Recipient from a Customer model."""
        return cls(
            phone=customer.phone,
            source_type="customer",
            customer_id=customer.id,
            first_name=customer.first_name,
            last_name=customer.last_name,
        )

    @classmethod
    def from_lead(cls, lead: Lead) -> Recipient:
        """Create a Recipient from a Lead model.

        Splits Lead.name into first/last name (first token vs rest).
        """
        parts = lead.name.strip().split(None, 1)
        first_name = parts[0] if parts else None
        last_name = parts[1] if len(parts) > 1 else None
        return cls(
            phone=lead.phone,
            source_type="lead",
            lead_id=lead.id,
            first_name=first_name,
            last_name=last_name,
        )

    @classmethod
    def from_adhoc(
        cls,
        phone: str,
        lead_id: UUID | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> Recipient:
        """Create a Recipient from an ad-hoc phone (ghost lead).

        ``lead_id`` is None at preview time (no ghost lead has been
        created yet) and is a real UUID at send time.
        """
        return cls(
            phone=phone,
            source_type="ad_hoc",
            lead_id=lead_id,
            first_name=first_name,
            last_name=last_name,
        )
