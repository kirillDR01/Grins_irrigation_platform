# Cluster C — Job Creation + SignWell Removal E2E

End-to-end verification scripts for the 8 in-scope items of Cluster C
(see `.agents/plans/cluster-c-job-creation-and-signwell-removal.md`).

Each phase script captures numbered screenshots under
`e2e-screenshots/cluster-c/<phase>/`. The runner aborts on the first
failure so the cluster cannot sign off with a partial pass.

## Hard rules

- **SMS only to `+19527373312`. Email only to `kirillrakitinsecond@gmail.com`.** The scripts here exercise UI + DB only; no real SMS or email is sent. The allowlist is still enforced because the same scripts can be re-run under prod credentials and that is where the recipient must match the operator's real contact info (per `feedback_test_recipients_prod_safety` memory).
- **Dev or local only.** `_lib.sh::require_cluster_c_env` refuses anything else.
- Operator must remain reachable at the allowlisted phone + inbox during the run in case a follow-up E2E (e.g. CallRail SMS confirmation) is added later.

## Files

| File | Purpose |
| --- | --- |
| `_lib.sh` | Shared helpers (`ab`, `psql_q`, `login_admin`, `assert_appointment_status`, `assert_job_category`). Refuses to run unless the recipient allowlist matches and ENVIRONMENT is dev or local. |
| `01-create-job-modal.sh` | Phase A. Opens a `send_contract` sales entry, opens the new CreateJobModal, edits, submits, asserts the Job's `category=ready_to_schedule`. |
| `02-needs-estimate-badge-clears.sh` | Phase B. Verifies the "Estimate Needed" badge does NOT render on a Job born from a closed-won sales entry. |
| `03-tech-view-confirmed-only.sh` | Phase C. Asserts the tech-mobile schedule renders only `CONFIRMED` appointments. |
| `04-job-search-global.sh` | Phase D. Asserts the legacy feature-local search input is gone and `<GlobalSearch scope="job">` navigates to JobDetail on click. |
| `05-signwell-removed.sh` | Phase E. Asserts `/api/v1/webhooks/signwell` returns 404, no SignWell iframe on sales detail, legacy copy gone, convert succeeds without a signwell_document_id. |
| `06-scope-renamed-notes.sh` | Phase F. Asserts the AppointmentModal ScopeMaterialsCard label reads "Notes". |
| `run-all.sh` | Sequenced runner — 01 → 06, abort on first failure. |

## How to run

```bash
# 1. Set environment.
export ENVIRONMENT=dev
export BASE="http://localhost:5173"       # or the dev Vercel/Railway frontend URL
export API_BASE="http://localhost:8000"   # or the dev Railway backend URL
export DATABASE_URL="postgresql://..."    # dev DB

# 2. Admin creds.
export E2E_USER=admin
export E2E_PASS=admin123

# 3. Single phase (during iteration):
bash e2e/cluster-c/04-job-search-global.sh

# 4. Full sweep (sign-off):
bash e2e/cluster-c/run-all.sh
```

Screenshots are written to `e2e-screenshots/cluster-c/<phase>/NN-name.png` so the operator can review and archive the trail.

## Preconditions / Seed data

- Phase A needs at least one sales entry in `send_contract` stage on dev.
- Phase B reuses the job created in Phase A (or any ready_to_schedule job born from a closed_won sales entry).
- Phase C needs at least one technician staff row and three appointments on the same date with statuses SCHEDULED, CONFIRMED, CANCELLED — the script SKIPs (exit 0) if the precondition is unmet.
- Phase D needs at least one job in the DB.
- Phase E asserts the SignWell webhook route is gone (deterministic) and optionally exercises convert_to_job against an entry without a signwell_document_id.
- Phase F needs at least one appointment to open in the schedule list view.

If a precondition is unmet, the script prints `SKIP: …` and exits 0 — the runner continues to the next phase.

## Cleanup

The scripts do not create permanent dev data outside of what the user already exercises via the CreateJobModal in Phase A. Each Phase A run produces one new Job + flips one sales entry to `closed_won`. Re-runs require seeding a fresh `send_contract` entry before each run.
