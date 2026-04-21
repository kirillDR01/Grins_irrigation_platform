#!/usr/bin/env bash
# .claude/statusline.sh
# Status line for Claude Code. Reads stdin JSON from the harness and prints
# a single line: "⎿ <branch> │ ctx <pct>% │ <repo>".
#
# Context heuristic: bytes(transcript) / 4 ≈ tokens; Opus 4.7 = 1M ctx window.
# Falls back gracefully when fields are missing / unreadable.

set -u

input="$(cat)"

cwd="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)"
transcript_path="$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)"

[ -z "$cwd" ] && cwd="$(pwd)"
repo_name="$(basename "$cwd")"

branch="$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "-")"

ctx_pct=""
if [ -n "$transcript_path" ] && [ -r "$transcript_path" ]; then
    bytes="$(wc -c <"$transcript_path" 2>/dev/null | tr -d ' ')"
    if [ -n "$bytes" ] && [ "$bytes" -gt 0 ] 2>/dev/null; then
        # 1_000_000 tokens * 4 bytes = 4_000_000 bytes full.
        # pct = bytes * 100 / 4_000_000 = bytes / 40000
        ctx_pct="$((bytes / 40000))"
    fi
fi

if [ -n "$ctx_pct" ]; then
    printf "⎿ %s │ ctx %s%% │ %s" "$branch" "$ctx_pct" "$repo_name"
else
    printf "⎿ %s │ %s" "$branch" "$repo_name"
fi
