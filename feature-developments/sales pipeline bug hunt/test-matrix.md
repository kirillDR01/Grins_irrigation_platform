# Test Matrix — Sales Pipeline Walkthrough

Traces each requirement in `.kiro/specs/handoff-stage-walkthrough-pipeline/requirements.md`
to what was exercised live on
`grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app`.

| Legend | Meaning |
|---|---|
| ✅ | Verified pass in live UI |
| 🔶 | Verified pass in code review (not exercisable live without creating test data) |
| ❌ | Verified fail in live UI / code review — see `bugs.md` |
| — | Not applicable to this audit |

## Requirement 1 — Type System Extension

| AC | Result | Evidence |
|---|---|---|
| 1.1 Type_System exports all stage types/constants | 🔶 | `frontend/src/features/sales/types/pipeline.ts` has STAGES/STAGE_INDEX/etc. |
| 1.2 AGE_THRESHOLDS match spec values | 🔶 | Code matches 3/7, 4/10, 3/7, 999/999 |
| 1.3 All NowCard/Activity/Nudge types exported | 🔶 | Present |
| 1.4 Existing exports preserved | 🔶 | Unchanged |
| 1.5 `statusToStageKey('estimate_scheduled') → 'schedule_estimate'` | ✅ | Brooke at estimate_scheduled still shows step 1 active |
| 1.6 `statusToStageKey('closed_lost') → null` | ✅ | Testing Viktor at closed_lost hides stepper entirely |
| 1.7 SALES_STATUS_CONFIG.send_contract label = "Convert to Job" | ✅ | Header pill on Brooke's send_contract view reads "Convert to Job" |

## Requirement 2 — Age-in-Stage Computation

| AC | Result | Evidence |
|---|---|---|
| 2.1–2.4 freshMax/staleMax buckets | ✅ | Pipeline list shows ⚡ 7D chips (stale) on many rows, ● 1D (fresh) on Maria & Paul |
| 2.5 closed_won/closed_lost → fresh {0} | ✅ | No AgeChip on Brooke (closed_won) or Testing Viktor (closed_lost) in the list |
| 2.6 estimate_scheduled → schedule_estimate thresholds | ✅ | Estimate Scheduled rows show chips using schedule_estimate thresholds |
| 2.7 TODO(backend) comment present | 🔶 | `useStageAge.ts` has the comment |

## Requirement 3 — AgeChip Component

| AC | Result | Evidence |
|---|---|---|
| 3.1 Glyph `●` fresh, `⚡` stale/stuck | ✅ | Maria & Paul (1D) show ●; 7D rows show ⚡ |
| 3.2–3.4 Bucket color tokens | ✅ | 1D chips emerald; 7D chips amber |
| 3.5 aria-label format | 🔶 | Code has correct aria-label template |
| 3.6 minimum `1d` display | ✅ | Paul Doppmann shows 1D even though just created |
| 3.7 Not rendered for closed_won/closed_lost | ✅ | Confirmed both in list |

## Requirement 4 — Pipeline List Summary Cards

| AC | Result | Evidence |
|---|---|---|
| 4.1 Four cards: Needs Estimate / Pending Approval / Needs Follow-Up / Revenue | ✅ | `03-pipeline-list.png` |
| 4.2 Needs Estimate count + toggles statusFilter | ✅ | Count 13 → after click → filter chip shown (`22-needs-estimate-filter.png`) |
| 4.3 Pending Approval count + toggles filter | ✅ | Count 0; click works |
| 4.4 Needs Follow-Up = client-side stuck count | ✅ | Count 0; all rows are stale, not stuck |
| 4.5 Follow-Up click toggles stuckFilter | ✅ | `23-followup-filter.png` — stuck-only chip visible, zero rows |
| 4.6 WoW delta via localStorage | ✅ | Shows "— same as last week" |
| 4.7 Revenue Pipeline not clickable | ✅ | Card has no cursor-pointer; formatted $0 |
| 4.8 Needs Follow-Up has bg-amber-50 | ✅ | Card is yellow in screenshot |

## Requirement 5 — Pipeline List Table Redesign

| AC | Result | Evidence |
|---|---|---|
| 5.1 Six columns | ✅ | Customer, Phone, Job Type, Status, Last Contact, Actions |
| 5.2 No Address column; tooltip on name | 🔶 | Code uses `title={property_address}` (native tooltip). Hover not tested live. |
| 5.3 Status pill + AgeChip | ✅ | Both visible in status cell |
| 5.4 Override flag shows ⚠ | 🔶 | No override entries in this dev DB to verify live |
| 5.5 Action label per stage | ✅ | Schedule, Send, View job labels confirmed |
| 5.6 Secondary ghost ✕ button | ✅ | Rendered next to each action |
| 5.7 Row click → /sales/:id | ✅ | Clicking Brooke's row navigated to `/sales/5607f5ca-…` |
| 5.8 No action button for closed_lost | ✅ | Testing Viktor row only shows ✕ after being marked lost |

## Requirement 6 — Pipeline List Filtering

| AC | Result | Evidence |
|---|---|---|
| 6.1 Summary card click toggles status filter | ✅ | Needs Estimate click filtered to 13 rows |
| 6.2 Follow-Up click toggles stuck filter | ✅ | Works |
| 6.3 Status filter chip with Clear | ✅ | "Schedule Estimate" chip + Clear |
| 6.4 Stuck filter chip "⚡ STUCK ENTRIES ONLY" | ✅ | Exact wording uppercased |
| 6.5 Both filters active simultaneously | 🔶 | Not exercised (would need both pending_approval and stuck to exist) — code supports it |
| 6.6 Clear removes all + resets page | ✅ | Clear clicked, filter chip disappeared |

## Requirement 7 — StageStepper Component

| AC | Result | Evidence |
|---|---|---|
| 7.1 5 steps, 3 phase labels | ✅ | Plan / Sign / Close visible across all stage screenshots |
| 7.2 done state (emerald ✓) | ✅ | Visible after advancing past a step |
| 7.3 active state (slate-900) | ✅ | Current step shows slate-900 circle |
| 7.4 waiting state (dashed amber pulse) | ✅ | Screenshot `09-pending-approval.png` — step 3 has dashed amber border |
| 7.5 future state (outlined slate-300) | ✅ | Steps beyond current are outlined |
| 7.6 "⋯ change stage manually" → onOverrideClick | ❌ | **Bug #5** — callback fires but nothing is rendered |
| 7.7 "✕ Mark Lost" → onMarkLost | ✅ | Works; also see **Bug #11** (doesn't disable in closed_won) |
| 7.8 Calendar badge under step 1 when visit scheduled | ✅ | After "Schedule visit" click, a "📅 Scheduled" badge appears under step 1 |
| 7.9 waiting pulse respects prefers-reduced-motion | 🔶 | CSS uses `motion-safe:animate-pulse` |

## Requirement 8 — NowCard Component

| AC | Result | Evidence |
|---|---|---|
| 8.1 Left-border tone accent | ✅ | Sky/amber/emerald borders visible across screenshots |
| 8.2 Pill with correct tone/label | ✅ | "Your move"/"Waiting on customer"/"Complete" all seen |
| 8.3 title uses text-wrap: pretty | 🔶 | Inline style present |
| 8.4 body copy sanitized HTML | 🔶 | `sanitizeCopy` regex in code; `<em>`/`<b>` render |
| 8.5 action variants (primary/outline/ghost/danger/locked) | ✅ | All five variants observed; locked shows disabled + lock icon |
| 8.6 delegate onAction to host | 🔶 | Code does exactly this |
| 8.7 lockBanner renders when set | ✅ | "No estimate PDF yet. …" banner visible on send_estimate empty state |

## Requirement 9 — nowContent Pure Function

| AC | Result | Evidence |
|---|---|---|
| 9.1 Signature | 🔶 | `nowContent.ts` matches spec |
| 9.2 schedule_estimate variation | ✅ | Screenshot `05-plan-stage-brooke.png` |
| 9.3 send_estimate (empty) variation | ✅ | Screenshot `07-advanced-to-send-estimate.png` |
| 9.4 send_estimate (ready, has email) | 🔶 | Code checks `hasCustomerEmail`; not exercised live |
| 9.5 send_estimate (ready, no email) | 🔶 | Code path present; not exercised |
| 9.6 pending_approval | ✅ | Screenshot `09-pending-approval.png` — BUT see **Bug #6** (AutoNudgeSchedule missing) |
| 9.7 send_contract (no agreement) | ✅ | Screenshot `10-send-contract.png` — locked Convert button visible |
| 9.8 send_contract (agreement uploaded) | 🔶 | Would require `document_type === 'contract'` to unlock; see **Bug #9** |
| 9.9 closed_won | ✅ | Screenshot `14-closed-won.png` |
| 9.10 round-trip determinism | 🔶 | Pure function; property-based test in `nowContent.test.ts` |

## Requirement 10 — NowCard Dropzone

| AC | Result | Evidence |
|---|---|---|
| 10.1–10.2 empty state + drag-over styling | 🔶 | Dashed border visible; drag-over not simulated |
| 10.3 PDF drop calls onFileDrop | ❌ | Handler exists but is TODO stub — **Bug #8** |
| 10.4 Non-PDF rejected with "PDF only" toast | 🔶 | Code present; not exercised live |
| 10.5 Filled state renders filename | 🔶 | Code path; no real upload tested |
| 10.6 Input accepts application/pdf only | 🔶 | `accept="application/pdf"` in code |

## Requirement 11 — AutoNudgeSchedule Component

| AC | Result | Evidence |
|---|---|---|
| 11.1–11.5 Row states / next marker / loop | ❌ | **Bug #6** — component never mounts because `estimateSentAt` isn't passed |
| 11.6 Paused state | ❌ | Same — host never passes `nudgesPaused` |

## Requirement 12 — ActivityStrip Component

| AC | Result | Evidence |
|---|---|---|
| 12.1 Horizontal row w/ `·` separators | ✅ | Visible on every stage after first transition |
| 12.2–12.4 Tone classes | 🔶 | Events generated have tones `done`/`neutral` |
| 12.5 Glyph per kind | ✅ | 🆕 / 📅 / ✉ / ✅ / 🛠 observed progressively on Brooke's walkthrough |
| 12.6 Returns null when empty | 🔶 | Code does so |

## Requirement 13 — Stage Walkthrough Layout

| AC | Result | Evidence |
|---|---|---|
| 13.1 StageStepper between header and NowCard | ✅ | All SalesDetail screenshots confirm |
| 13.2 NowCard between Stepper and ActivityStrip | ✅ | Confirmed |
| 13.3 ActivityStrip between NowCard and Documents | ✅ | Confirmed |
| 13.4 StatusActionButton NOT in header | ✅ | Header only has status pill + Change stage combobox + Email/Sign buttons |
| 13.5 closed_lost shows banner, hides walkthrough | ✅ | Screenshot `20-closed-lost-banner.png` |

## Requirement 14 — Week-Of Picker

| AC | Result | Evidence |
|---|---|---|
| 14.1 5 week chips starting at Monday | ✅ | Apr 20 / 27 / May 4 / 11 / 18 visible |
| 14.2 "+ pick date…" opens Popover+Calendar | ❌ | **Bug #4** — chip is a no-op |
| 14.3 Selected chip styling | ✅ | Apr 27 turned black after click |
| 14.4 Persist to localStorage per entryId | ✅ | Apr 27 selection survived transition to closed_won (title reads "targeted for Apr 27") |
| 14.5 Helper note present | ✅ | "Used only as a target — pin the exact day + crew later in the Jobs tab." visible |

## Requirement 15 — Click-Handler Wiring

| AC | Result | Evidence |
|---|---|---|
| 15.1 schedule_visit → open schedule modal | ❌ | **Bug #2** — calls advance.mutate instead |
| 15.2 send_estimate_email → send mutation | 🔶 | Not exercised (requires a real estimate PDF); code wires `emailSign.mutateAsync` |
| 15.3 convert_to_job → open convert modal | 🔶 | Code calls `convertToJob.mutate` directly (no modal) — possible minor spec deviation, not exercised live |
| 15.4 view_job → /jobs/{job_id} | ❌ | **Bug #7** — uses signwell_document_id |
| 15.5 view_customer → /customers/{id} | ✅ | Screenshot `16-view-customer.png` |
| 15.6 jump_to_schedule → /schedule | ✅ | Screenshot `15-jump-to-schedule.png` |
| 15.7 mark_declined → decline modal | 🔶 | Code opens no modal; directly calls `markLost.mutate` — possible spec deviation |
| 15.8 skip_advance → pending_approval | ❌ | **Bug #1** — user-reported failure |
| 15.9 mark_approved_manual → send_contract | ✅ | Worked on Brooke via override |
| 15.10 Stubbed actions show "Not wired yet — TODO" | ✅ | Confirmed for Resend, Pause |

## Requirement 16 — Test IDs and Accessibility

| AC | Result | Evidence |
|---|---|---|
| 16.1–16.5 Test IDs on major components | 🔶 | All present in code; some exercised via agent-browser |
| 16.6 AgeChip aria-label | 🔶 | Code has aria-label |
| 16.7 NowCard title text-wrap: pretty | 🔶 | Inline style present |
| 16.8 waiting animation respects prefers-reduced-motion | 🔶 | CSS classes present |

## Requirement 17 — No New Dependencies / No Backend Changes

| AC | Result | Evidence |
|---|---|---|
| 17.1 No new npm deps | 🔶 | `package.json` untouched |
| 17.2 No DB migrations / API changes | 🔶 | No migration files committed with this feature |
| 17.3 Existing hooks unchanged | 🔶 | `useSalesPipeline.ts` unchanged |
| 17.4 Stubbed endpoints → toast + TODO | ✅ | Confirmed for Resend/Pause |
| 17.5 updated_at fallback + TODO | 🔶 | Present in `useStageAge.ts` |
| 17.6 localStorage Week-Of + TODO | ✅ | Persistence verified live |

---

## Stages Exercised End-to-End

| Stage | Walkthrough Verified? | Notes |
|---|---|---|
| Plan (schedule_estimate) | ✅ | Brooke — step 1 active, NowCard rendered correctly; Schedule visit advances (bug #2) |
| Plan (estimate_scheduled) | ✅ | Brooke — after click, stepper shows "📅 Scheduled" badge under step 1 |
| Sign (send_estimate) | ✅ | Brooke + Testing Viktor — dropzone + lock banner render; Skip button fails (bug #1) |
| Approve (pending_approval) | ✅ | Brooke (via manual override) — waiting pill, 4 actions, dashed amber step 3; missing AutoNudgeSchedule (bug #6) |
| Close (send_contract) | ✅ | Brooke — dropzone + week-of picker + locked Convert; pick date chip fails (bug #4) |
| Close (closed_won) | ✅ | Brooke — Complete pill, View Job (bug #7) / Customer (ok) / Schedule (ok); Mark Lost still visible (bug #11) |
| Close (closed_lost) | ✅ | Testing Viktor via Mark Lost — banner displayed, walkthrough hidden |
