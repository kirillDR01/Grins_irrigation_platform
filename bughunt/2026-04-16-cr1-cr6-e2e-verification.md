# CR-1..CR-6 E2E verification — 2026-04-16 (dev deployment)

Deployment verified against:

- **Backend:** Railway `Grins-dev` deployment `bc90a75f-50d2-450c-8d4c-ecf56ceb68c6` (commit `5ecf3b7`, status `SUCCESS`).
- **Frontend:** Vercel `grins-irrigation-platform` deployment `dpl_9nMBtAtWjyMktEnbV2Bgrbw4mn8W` (commit `5ecf3b7`, state `READY`).

Base URLs used:

- API: https://grins-dev-dev.up.railway.app
- FE:  https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app

Auth: admin/admin123 (per `Testing Procedure/00-preflight.md`).

## What was exercised live

| CR | Surface | Probe | Result |
|---|---|---|---|
| CR-5 | `GET /api/v1/invoices/lien-candidates` | `curl -H Auth … ?days_past_due=60&min_amount=500` | `200 []` — endpoint live, zero rows match on dev DB. |
| CR-5 | `POST /api/v1/invoices/mass-notify {notification_type:"lien_eligible"}` | `curl` | `400` with `detail.error="lien_eligible_deprecated"` + `replacement.{list,send}` pointers. |
| CR-5 | FE `/invoices?tab=lien-review` | agent-browser | Tab renders and is selected; empty-state copy "No customers in the lien review queue." See `cr5-lien-tab.png`. |
| CR-5 | FE Mass Notify dialog | agent-browser → open dropdown | Dropdown lists only **Past Due** + **Due Soon** — `lien_eligible` is gone. See `cr5-mass-notify-no-lien.png`. |
| CR-6 | `POST /api/v1/leads/{id}/convert` with duplicate phone, `force=false` | curl | `409` with `detail.error="duplicate_found"`, `detail.phone="9527373312"`, `detail.duplicates=[{Kirill Rakitin customer record}]`. |
| CR-6 | FE `/leads` | agent-browser | List loads and renders. See `cr6-leads.png`. The 409 conflict modal flow itself is covered by FE tests; live exercise deferred to avoid creating throwaway customers against dev. |

## What was NOT exercised live on dev

| CR | Why skipped on live dev |
|---|---|
| CR-1 | `apply_schedule` against a shared dev DB would promote real jobs to DRAFT on the selected date; test coverage at unit + integration already passes. |
| CR-2 | Needs an appointment transition + job-started click; state setup against shared DB considered high-risk for this pass. |
| CR-3 | Requires a real CallRail inbound SMS replay. Unit + functional coverage asserts the empty `auto_reply` short-circuit. |
| CR-4 | Stripe webhook-driven. Unit tests cover all four `billing_reason` branches including the new `subscription_update` / `manual` paths. |
| CR-6 `force=true` | `customer_service.create_customer` has its own phone-uniqueness check that would return 400 before the dedup override has a chance to land. Covered by BE unit + functional tests. |

## Safety notes

- No real SMS was dispatched during this verification pass (only one read-only `GET /lien-candidates`, which returned empty).
- No real email was dispatched (only the `/convert` 409 path, which raises before any customer is created).
- The test lead created for the CR-6 probe (`6c03bcce-e38c-41b4-add3-b2b658196878`) was deleted immediately after the 409 was captured.

## Screenshots

- `cr5-lien-tab.png` — Lien Review tab selected on /invoices, empty state.
- `cr5-mass-notify-no-lien.png` — Mass Notify dialog dropdown showing only Past Due + Due Soon.
- `cr6-leads.png` — Leads page rendered against live dev deployment.
