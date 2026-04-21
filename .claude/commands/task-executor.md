---
description: Loop through unchecked tasks in a Kiro spec, stopping automatically at 60% context usage.
argument-hint: <spec-name>
---

You are about to execute tasks from a Kiro spec in a **loop** with a **60% context-usage safety valve**. You fire this command once and it works through tasks until either (a) all checkboxes are checked, (b) context usage reaches 60%, or (c) a task fails or conflicts with steering. No mid-run confirmation is required.

## Argument

The user invoked `/task-executor` with argument: `$ARGUMENTS`

Treat `$ARGUMENTS` as the spec folder name under `.kiro/specs/`. Strip surrounding quotes or whitespace. If `$ARGUMENTS` is empty, stop and tell the user: "Usage: /task-executor <spec-name>. Example: /task-executor internal-notes-simplification."

## One-time setup (run once per invocation, before the loop)

### Step 1 — Load steering documents

Use Glob on `.kiro/steering/*.md` to list every steering file, then Read each one. Do not skip any. These are the project's standing rules — code standards, patterns, testing, devlog, quality gates — and they constrain every task that follows.

### Step 2 — Load the target spec

Read these three files:

- `.kiro/specs/$ARGUMENTS/requirements.md`
- `.kiro/specs/$ARGUMENTS/design.md`
- `.kiro/specs/$ARGUMENTS/tasks.md`

If any is missing, stop and report which one. Do not proceed against a partial spec.

## Task loop

Enter the loop. Repeat Steps 3 → 8 until one of the exit conditions fires.

### Step 3 — Context-usage safety check (before every task)

Run this bash snippet to estimate current context usage from the session transcript:

```bash
# Pick the largest jsonl modified in the last 5 minutes — this is the active
# session, avoiding tiny concurrent-session transcripts that could otherwise
# confuse `ls -t`.
latest=$(find "$HOME/.claude/projects" -maxdepth 3 -name "*.jsonl" -type f -mmin -5 2>/dev/null \
    | while read -r f; do printf "%s\t%s\n" "$(wc -c <"$f" | tr -d ' ')" "$f"; done \
    | sort -rn | head -1 | cut -f2-)
if [ -n "$latest" ]; then
    bytes=$(wc -c <"$latest" 2>/dev/null | tr -d ' ')
    pct=$((bytes / 40000))
    echo "ctx_pct=$pct"
else
    echo "ctx_pct=0"
fi
```

Parse the `ctx_pct=N` value.

- **If `N >= 60`**: STOP THE LOOP immediately. Go to Step 9 and set the outcome to `"hit context gate at N%"`. Do not start another task. Do not try to squeeze one more in.
- **If `N < 60`** or the command failed / returned nothing: continue to Step 4.

The heuristic is `transcript-bytes / 4 ≈ tokens` against Opus 4.7's 1M context window. It's approximate — the gate is intentionally conservative.

### Step 4 — Find the next unchecked task

Re-read `.kiro/specs/$ARGUMENTS/tasks.md` (it may have been edited since the previous iteration). Scan top-to-bottom and find the first `- [ ]` checkbox. Record its task number, description, and phase heading.

If **no unchecked checkboxes remain**, STOP THE LOOP. Go to Step 9 with outcome `"all tasks complete"`.

### Step 5 — Reconcile task against steering + requirements + design

Cross-check the task against:

- The steering docs from Step 1 (code standards, testing expectations, any quality gates).
- The relevant requirement(s) in `requirements.md`.
- The relevant section(s) in `design.md`.

If you find a genuine conflict (task contradicts steering, or requirement/design has changed since the task was written), STOP THE LOOP. Go to Step 9 with outcome `"halted on conflict at task X.Y"` and surface the conflict.

Do not paper over conflicts. Surface them.

### Step 6 — Execute the task

Implement the task. Follow the steering docs strictly. Keep commits scoped to this task.

**Subagent delegation (mandatory) — protect context:**

- If you need to read more than ~3 files to understand current state, delegate to `Agent(subagent_type="Explore", ...)` with a focused question and ask for a short report (≤300 words). Do not dump raw search results into this context.
- If you need to trace a call site or pattern across the repo, that is an Explore task — not an inline Grep.
- If you need an implementation plan for a non-trivial change, delegate to `Agent(subagent_type="Plan", ...)`.
- Inline Read/Grep/Glob is fine for the specific files you are about to edit and their direct imports. Use subagents for everything broader.

This rule is what makes the 60% gate workable: main-context bytes are dominated by steering + spec + actual edits, not by raw exploration output.

### Step 7 — Mark the task complete

When implementation is done and any verification required by the task (tests, lint, typecheck) passes:

- Use Edit on `tasks.md` to change the task's `- [ ]` to `- [x]`.
- Do not change any other checkbox on the same edit.

If verification **failed**, STOP THE LOOP. Go to Step 9 with outcome `"halted on failure at task X.Y"`. Do not mark the checkbox complete when verification failed.

### Step 8 — Loop back

Emit **one short line** to the user: `Completed task X.Y — <short description>. Looping back.` Do not write a full report per task; the final report at Step 9 is where detail goes.

Return to Step 3. Do not skip the context check.

## End-of-loop

### Step 9 — Final report

End with a concise summary:

1. **Outcome** — one of:
   - `"all tasks complete"`
   - `"hit context gate at N%"`
   - `"halted on failure at task X.Y"`
   - `"halted on conflict at task X.Y"`
2. **Tasks executed this run** — numbered list of `task X.Y — <description>`.
3. **Files changed this run** — aggregated across all tasks.
4. **Verification run this run** — what passed (e.g., "backend ruff + mypy + unit tests green").
5. **Next unchecked task** — if the outcome wasn't `"all tasks complete"`, which task is next.
6. **Recommended next action:**
   - Outcome = `"all tasks complete"` → "Spec is done. Commit when ready."
   - Outcome = `"hit context gate at N%"` → "Run `/clear`, then re-invoke `/task-executor $ARGUMENTS` to resume from the next unchecked task."
   - Outcome = `"halted on failure"` or `"halted on conflict"` → "Inspect the failure/conflict, fix manually or update the spec, then re-invoke `/task-executor $ARGUMENTS`."

## Hard rules for this run

- Do not ask for user confirmation between steps or between tasks. Run end-to-end.
- Do not commit or push unless the steering docs or spec explicitly require it. Staging and committing are separate user decisions.
- Do not modify `main`, and do not modify branches other than the currently checked-out branch unless the task explicitly instructs otherwise.
- Do not skip Step 1. Steering must be loaded even if you think you know the rules.
- Do not skip Step 3. The context gate is the primary mitigation against context rot; bypassing it is a regression of the agreed design.
- Do not mark a checkbox complete if verification failed.
- Keep narration between tasks minimal (one line per task at Step 8). The final report at Step 9 is the important output.
