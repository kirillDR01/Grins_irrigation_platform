#!/usr/bin/env bash
# .claude/hooks/precompact-dump.sh
# PreCompact hook: dumps session-resume state to .claude/session-resume.md
# before the harness compacts the conversation. Intended for recovering from
# context rot: open a fresh session and read session-resume.md to continue.

set -u

input="$(cat)"

cwd="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)"
transcript_path="$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null)"
trigger="$(printf '%s' "$input" | jq -r '.trigger // "unknown"' 2>/dev/null)"

[ -z "$cwd" ] && cwd="$(pwd)"

resume_file="$cwd/.claude/session-resume.md"
mkdir -p "$(dirname "$resume_file")"

branch="$(git -C "$cwd" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "-")"
head="$(git -C "$cwd" rev-parse --short HEAD 2>/dev/null || echo "-")"
status_output="$(git -C "$cwd" status --short 2>/dev/null || echo "")"

last_user_msg=""
if [ -n "$transcript_path" ] && [ -r "$transcript_path" ]; then
    # JSONL transcript — extract the most recent user message text.
    # Tolerate variations: content may be a string or an array of blocks.
    last_user_msg="$(tac "$transcript_path" 2>/dev/null \
        | jq -r 'select(.type == "user") | (.message.content // .content) | if type == "array" then map(.text // "") | join("\n") else . end' 2>/dev/null \
        | awk 'NF { print; exit }' || true)"
fi

active_spec="-"
if [ -n "$transcript_path" ] && [ -r "$transcript_path" ]; then
    spec_match="$(grep -oE '/task-executor[[:space:]]+[a-zA-Z0-9_-]+' "$transcript_path" 2>/dev/null | tail -n1 | awk '{print $2}' || true)"
    [ -n "$spec_match" ] && active_spec="$spec_match"
fi

timestamp="$(date -u +'%Y-%m-%d %H:%M:%S UTC')"

{
    printf "# Session Resume — auto-dumped by PreCompact hook\n\n"
    printf "**When:** %s\n" "$timestamp"
    printf "**Trigger:** %s\n" "$trigger"
    printf "**Branch:** %s @ %s\n" "$branch" "$head"
    printf "**Active spec:** %s\n\n" "$active_spec"
    printf "## Last user message\n\n"
    printf '```\n'
    if [ -n "$last_user_msg" ]; then
        printf '%s\n' "$last_user_msg"
    else
        printf '(no user message captured)\n'
    fi
    printf '```\n\n'
    printf "## Modified files\n\n"
    printf '```\n'
    if [ -n "$status_output" ]; then
        printf '%s\n' "$status_output"
    else
        printf '(clean working tree)\n'
    fi
    printf '```\n\n'
    printf -- "---\n\n"
    printf "To resume: start a fresh Claude Code session and run \`@.claude/session-resume.md\`\n"
    printf "to load this state. If an active spec is recorded, resume with \`/task-executor %s\`.\n" "$active_spec"
} > "$resume_file"

# Emit a systemMessage so the user sees the dump happened.
printf '{"systemMessage": "Session state dumped to .claude/session-resume.md"}\n'
exit 0
