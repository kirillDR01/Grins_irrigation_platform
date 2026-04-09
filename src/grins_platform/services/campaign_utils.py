"""Shared utilities for campaign message composition."""
from __future__ import annotations

from typing import Any


def render_poll_block(poll_options: list[dict[str, Any]] | None) -> str:
    """Build the text block appended to a poll campaign's SMS body.

    Mirrors frontend renderPollOptionsBlock() exactly.
    """
    if not poll_options:
        return ""
    lines = [
        f"{opt.get('key', '?')}. {opt.get('label') or '(no label)'}"
        for opt in poll_options
    ]
    keys = ", ".join(str(opt.get("key", "?")) for opt in poll_options)
    return f"\n\nReply with {keys}:\n" + "\n".join(lines) + "\n\n"
