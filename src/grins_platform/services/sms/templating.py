"""SMS template rendering with safe merge-field substitution.

Uses Python's str.format_map with a SafeDict that returns empty string
for missing keys — no Jinja, no conditionals, no loops.
"""

from __future__ import annotations


class SafeDict(dict[str, str]):
    """Dict subclass that returns empty string for missing keys."""

    def __missing__(self, key: str) -> str:
        return ""


def render_template(body: str, context: dict[str, str]) -> str:
    """Render merge fields in *body* using *context*.

    ``{first_name}`` style placeholders are replaced with values from
    *context*.  Missing keys silently resolve to ``""``.
    Malformed format strings are returned as-is.
    """
    try:
        return body.format_map(SafeDict(context))
    except (ValueError, KeyError):
        return body
