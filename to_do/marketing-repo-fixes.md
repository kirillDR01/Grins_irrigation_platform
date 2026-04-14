# Marketing-repo follow-ups (cross-repo, filed from bughunt 2026-04-14)

These items are **NOT** fixable in this repo (grins_irrigation_platform) — they live in the separate marketing site (`Grins_irrigation`). E-BUG-B was observed when filling the "Get Your Free Quote" form on the marketing dev site and seeing no CRM record, no network error, and no success banner.

Filed: 2026-04-14.
Owner: whoever maintains `Grins_irrigation`.

---

## 1. Check `VITE_API_BASE_URL` on Vercel (preview + production)

On the marketing-site Vercel project, confirm that `VITE_API_BASE_URL`:

- **Preview scope** → points to `https://grins-dev-dev.up.railway.app`
- **Production scope** → points to the production Railway URL (TBD)

A misconfigured preview deploy hitting the prod backend (or vice versa) is the most common cause of "form posts to nothing."

## 2. Surface fetch errors in the quote-form handler

Today the form submit path appears to silently swallow errors — there's no toast, no inline error banner, no `console.error`, no form-field highlight. Users assume it worked and leave.

Desired behavior:

- On any 4xx/5xx from `/api/v1/leads`: show an inline toast with a user-friendly message ("We couldn't submit your request — please call us at [phone]") and preserve the form state so the customer doesn't retype.
- On a network failure (fetch rejection): same UX, different copy ("Network error — please try again").
- Always `console.error(error)` for local-debug triage.

## 3. Add a success banner / redirect on 201

Currently nothing visible happens after the server returns 201. Add:

- A success banner with a confirmation message ("Thanks — we'll reach out within one business day"), OR
- A redirect to a `/thank-you` page.

Pick whichever matches the rest of the marketing site's UX.

## 4. Log the backend's `X-Request-ID` on submit

The CRM backend now echoes an `X-Request-ID` header on every response (see `grins_platform/app.py` middleware). In the form's submit handler:

```ts
const response = await fetch(`${apiBaseUrl}/api/v1/leads`, { ... });
const requestId = response.headers.get("x-request-id");
console.log("[lead-submit] X-Request-ID:", requestId, "status:", response.status);
```

This lets us correlate a specific user report (screenshot of console) with a specific backend log line in Railway.

## 5. CORS sanity

The backend's `CORS_ORIGINS` env currently includes `https://grins-irrigation-*-kirilldr01s-projects.vercel.app`. Verify the wildcard matches the actual Vercel preview URL the marketing site publishes. If the marketing site ever moves to a new Vercel project slug, update the backend `CORS_ORIGINS`.

---

When the marketing-repo owner picks these up, the smoke script at `scripts/smoke/test_public_lead.sh` can be run from CI against the dev Railway URL to catch regressions.
