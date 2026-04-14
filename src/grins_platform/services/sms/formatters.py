"""Customer-facing SMS formatting helpers.

Keeps date, time, time-window, and service-type rendering consistent
across outbound appointment SMS (confirmation, reschedule, cancellation)
so the customer sees ``"Monday, April 21 at 10:00 AM"`` everywhere
instead of ``"2026-04-21 10:00:00"`` in one place and ``"April 21, 2026
at 10:00 AM"`` in another.

Uses portable strftime tokens only — no ``%-d`` / ``%-I`` (those are
POSIX-only and crash on Windows dev boxes, bughunt M-11).

Validates: bughunt 2026-04-14 H-3, L-4, M-11.
"""

from __future__ import annotations

from datetime import date, time


def format_sms_date(d: date) -> str:
    """Render a date as ``"Monday, April 21"`` for customer-facing SMS.

    No trailing year — the SMS is always for an upcoming (or very
    recently past) appointment, and the short form reads more
    naturally. Stripping the leading zero on the day is done
    manually to stay portable across platforms.
    """
    weekday = d.strftime("%A")
    month = d.strftime("%B")
    day = str(d.day)
    return f"{weekday}, {month} {day}"


def format_sms_date_long(d: date) -> str:
    """Render a date as ``"Monday, April 21, 2026"`` for audit-heavy
    surfaces where the year matters (e.g. cancellation receipts)."""
    weekday = d.strftime("%A")
    month = d.strftime("%B")
    day = str(d.day)
    year = d.strftime("%Y")
    return f"{weekday}, {month} {day}, {year}"


def format_sms_time_12h(t: time | str | None) -> str:
    """Render a ``time`` as ``"10:00 AM"``.

    Accepts a ``datetime.time`` instance or its ``"HH:MM"`` / ``"HH:MM:SS"``
    string form — the SQLAlchemy ``Time`` column occasionally surfaces
    as a string in edge cases. Returns an empty string for falsy input
    so callers can compose templates conditionally without extra guards.
    """
    if t is None or t == "":
        return ""
    raw = str(t)[:5]
    if len(raw) < 5 or raw[2] != ":":
        return ""
    hour = int(raw[:2])
    minute = int(raw[3:5])
    suffix = "AM" if hour < 12 else "PM"
    hour_12 = hour % 12 or 12
    return f"{hour_12}:{minute:02d} {suffix}"


def format_sms_time_window(
    window_start: time | str | None,
    window_end: time | str | None,
) -> str:
    """Render a time window as ``" between 10:00 AM and 12:00 PM"`` (with
    leading space) for appending to a date phrase. Falls back to
    ``" at 10:00 AM"`` if only ``window_start`` is set, or an empty
    string if neither bound is present.
    """
    start = format_sms_time_12h(window_start) if window_start else ""
    end = format_sms_time_12h(window_end) if window_end else ""
    if start and end:
        return f" between {start} and {end}"
    if start:
        return f" at {start}"
    return ""


def format_job_type_display(job_type: str | None) -> str:
    """Render a ``jobs.job_type`` slug as a title-cased display name.

    Not a curated map — that's bughunt L-1 / L-8 (Sprint 7). This
    helper is the baseline used everywhere until a canonical map
    lands; it preserves today's behaviour (``"spring_startup"`` →
    ``"Spring Startup"``) without introducing a new divergence.
    """
    if not job_type:
        return ""
    return job_type.replace("_", " ").title()
