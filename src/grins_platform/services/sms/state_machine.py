"""Campaign recipient state machine with orphan recovery.

Defines the explicit ``pending → sending → sent/failed/cancelled`` state
machine that prevents double-sends on worker crashes.  The state machine
is the **sole** double-send protection — CallRail's Idempotency-Key
header is inconclusive.

Validates: Requirement 28 (S13)
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class RecipientState(str, Enum):
    """Allowed delivery states for a campaign recipient."""

    pending = "pending"
    sending = "sending"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"


class InvalidStateTransitionError(Exception):
    """Raised when a forbidden state transition is attempted."""

    def __init__(
        self,
        from_state: RecipientState,
        to_state: RecipientState,
    ) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid state transition from '{from_state.value}' to '{to_state.value}'",
        )


# Allowed transitions: from_state → {to_states}
_ALLOWED_TRANSITIONS: dict[
    RecipientState,
    frozenset[RecipientState],
] = {
    RecipientState.pending: frozenset(
        {RecipientState.sending, RecipientState.cancelled},
    ),
    RecipientState.sending: frozenset(
        {
            RecipientState.sent,
            RecipientState.failed,
            RecipientState.cancelled,
        },
    ),
    RecipientState.sent: frozenset(),  # terminal
    RecipientState.failed: frozenset(
        {RecipientState.pending},
    ),  # manual retry
    RecipientState.cancelled: frozenset(),  # terminal
}


def transition(
    from_state: RecipientState,
    to_state: RecipientState,
) -> RecipientState:
    """Validate and return *to_state* if the transition is allowed.

    Raises:
        InvalidStateTransitionError: If the transition is forbidden.
    """
    if to_state not in _ALLOWED_TRANSITIONS[from_state]:
        raise InvalidStateTransitionError(from_state, to_state)
    return to_state


_ORPHAN_RECOVERY_SQL = text(
    "UPDATE campaign_recipients "
    "SET delivery_status = 'failed', "
    "    error_message = 'worker_interrupted' "
    "WHERE delivery_status = 'sending' "
    "  AND sending_started_at < now() - interval '5 minutes'",
)


async def orphan_recovery_query(session: AsyncSession) -> int:
    """Mark stuck ``sending`` recipients as ``failed``.

    Returns the number of rows recovered.
    """
    result = await session.execute(_ORPHAN_RECOVERY_SQL)
    return result.rowcount  # type: ignore[no-any-return]
