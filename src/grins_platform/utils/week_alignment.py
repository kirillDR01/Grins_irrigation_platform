"""Week alignment utility for Monday-Sunday week ranges.

Validates: CRM2 Requirements 20.1, 20.2, 20.3
"""

from __future__ import annotations

from datetime import date, timedelta


def align_to_week(d: date) -> tuple[date, date]:
    """Return the Monday-Sunday range containing the given date.

    Args:
        d: Any date within the desired week.

    Returns:
        Tuple of (monday, sunday) for the week containing *d*.
    """
    monday = d - timedelta(days=d.weekday())  # weekday(): Mon=0
    sunday = monday + timedelta(days=6)
    return monday, sunday
