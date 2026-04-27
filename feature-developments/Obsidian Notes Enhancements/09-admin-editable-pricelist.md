# 09 — Admin-editable price list (no code changes required)

**Request (paraphrased):**
> Admin should be able to adjust the overall price list — add or delete anything — somewhere in the CRM, without needing backend code changes.

**Status:** ❌ NOT IMPLEMENTED in UI · ✅ Backing DB + API already exist

---

## What exists today

- `ServiceOffering` model (`models/service_offering.py:23-166`) — fields include `base_price`, `price_per_zone`, `pricing_model` (flat / zone_based / hourly / custom), `category`, `is_active`.
- CRUD API: `GET/POST /api/v1/services`, `GET/PUT/DELETE /api/v1/services/{id}` (`api/v1/services.py:1-100`).
- Static reference document: `pricelist.md` (148 lines) — this is a markdown *doc*, not connected to the live data.
- Settings UI has `InvoiceDefaults.tsx` and `EstimateDefaults.tsx`, but neither is a service-catalog editor.

## What's missing

- No admin page in the frontend that CRUDs `ServiceOffering` rows. Admin has to hit the API directly.
- `pricelist.md` must be kept in sync manually with the DB (or deprecated).

## TODOs

- [ ] **TODO-09a** Build `frontend/src/pages/Settings/PriceList.tsx` (admin-only). Table of `ServiceOffering` rows with inline add/edit/archive.
- [ ] **TODO-09b** Wire the estimate line-item dropdown (#07) and any collect-payment quick picks (#06) to this same data source.
- [ ] **TODO-09c** Decide on `pricelist.md`: retire it, or auto-render from the DB into a read-only printable sheet. ❓
- [ ] **TODO-09d** Audit-log price changes (who changed what, when, old → new value). Important for contracts/invoices issued before a change.

## Clarification questions ❓

1. **Location in the UI:** own top-level "Settings → Price List" tab, or under an existing section (e.g. Admin Settings)?
2. **Categories vs flat list:** do you want grouping by category (Repair / Installation / Winterization etc.) or a flat searchable list?
3. **Effect on existing data:** if an admin deletes/archives a price, do existing estimates/invoices keep the old value? (Standard accounting answer: yes, snapshot at issue time. Confirm.)
