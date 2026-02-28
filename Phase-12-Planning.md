# Phase 12 Planning — Future Features

## Biometric Login (WebAuthn / Face ID / Fingerprint)

### Overview

Support biometric authentication (Face ID, Touch ID, Windows Hello, Android biometrics) for staff login using the Web Authentication API (WebAuthn). This leverages the device's built-in biometric hardware rather than building custom face recognition.

### Why This Matters for Grins

- Field techs (Vas, Dad, Steven, Vitallik) use phones with dirty/wet hands — typing passwords is slow and frustrating
- Face ID / fingerprint unlock is instant and already familiar to every smartphone user
- No camera processing, no ML models, no privacy concerns — the biometric never leaves the device
- Works offline (the cryptographic key lives on the device)
- Supported on all modern browsers and mobile devices

### How It Works

1. **Registration**: User logs in with username/password once, then enrolls their device biometric. This creates a public/private key pair — private key stays on the device, public key is stored on the backend.
2. **Login**: Browser prompts for biometric (Face ID, fingerprint, etc.). If verified, the device signs a server-issued challenge with the private key.
3. **Verification**: Backend verifies the signature against the stored public key and issues a JWT as usual.

### Backend Changes (FastAPI)

- New `webauthn_credentials` table linked to staff/users:
  - `id` (UUID, PK)
  - `user_id` (FK → users)
  - `credential_id` (bytes, unique) — identifier for the credential
  - `public_key` (bytes) — stored public key
  - `sign_count` (int) — replay attack protection counter
  - `device_name` (str) — friendly name like "Viktor's iPhone"
  - `created_at`, `last_used_at` (timestamps)

- Two new API endpoints:
  - `POST /api/v1/auth/webauthn/register-options` — generate registration challenge (requires existing auth)
  - `POST /api/v1/auth/webauthn/register` — store credential after biometric enrollment
  - `POST /api/v1/auth/webauthn/login-options` — generate authentication challenge (no auth required)
  - `POST /api/v1/auth/webauthn/login` — verify assertion, issue JWT

- Library: `py_webauthn` — handles all FIDO2/WebAuthn cryptography

### Frontend Changes (React)

- New "Sign in with Face ID / Fingerprint" button on login page
- Registration flow: Settings page → "Add Biometric Login" → calls `navigator.credentials.create()`
- Login flow: Click biometric button → calls `navigator.credentials.get()` → sends assertion to backend → receives JWT
- Graceful fallback: if WebAuthn isn't available (old browser, desktop without biometric), button is hidden and username/password remains the only option
- Device management UI: list enrolled devices, remove old ones

### Authentication Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│                   LOGIN PAGE                         │
│                                                     │
│   ┌─────────────────────────────────────────────┐   │
│   │  Username: [____________]                    │   │
│   │  Password: [____________]                    │   │
│   │                                             │   │
│   │  [  Sign In  ]                              │   │
│   │                                             │   │
│   │  ── or ──                                   │   │
│   │                                             │   │
│   │  [ 🔐 Sign in with Face ID / Fingerprint ] │   │
│   └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
   Username/Password          WebAuthn Flow
   (existing flow)       ┌──────────────────┐
         │               │ Browser prompts   │
         │               │ for biometric     │
         │               │ (Face ID, etc.)   │
         │               └────────┬─────────┘
         │                        │
         │                        ▼
         │               ┌──────────────────┐
         │               │ Device signs      │
         │               │ challenge with    │
         │               │ private key       │
         │               └────────┬─────────┘
         │                        │
         ▼                        ▼
   ┌──────────────────────────────────────┐
   │  Backend verifies → Issues JWT       │
   └──────────────────────────────────────┘
```

### What We Explicitly Avoid

- **Custom face recognition** (camera capture → ML model → matching) — massive scope, privacy nightmare, unreliable in field conditions (sunlight, hats, sunglasses, dirty faces)
- **Third-party biometric services** — expensive, overkill for a small team of 5-6 people
- **Storing biometric data on the server** — WebAuthn only stores public keys, never biometric templates

### Effort Estimate

| Component | Estimate |
|-----------|----------|
| Backend: `py_webauthn` integration + endpoints | 1 day |
| Backend: DB migration + credential management | 0.5 day |
| Frontend: Login page biometric button + flow | 0.5 day |
| Frontend: Settings page device enrollment UI | 0.5 day |
| Testing + E2E validation | 0.5 day |
| **Total** | **~3 days** |

### Dependencies

- `py_webauthn` Python library
- HTTPS required (WebAuthn won't work over HTTP, but production already uses HTTPS)
- Relying Party ID configuration (domain name — `grins-platform-production.up.railway.app` or custom domain)

### Considerations

- WebAuthn credentials are domain-bound — if the backend domain changes, all enrolled credentials break (users re-enroll)
- Each device needs separate enrollment (Viktor's phone ≠ Viktor's laptop)
- Should keep username/password as fallback — biometric is convenience, not a replacement
- Consider allowing multiple credentials per user (phone + laptop)

### Priority

Medium — nice quality-of-life improvement for field staff, but not blocking any business operations. Best implemented after core features are stable and deployed.

---

## Field Quote & Invoice Generator (Tablet POS System)

### Overview

A tablet-optimized, step-by-step wizard that allows field technicians to generate professional estimates or invoices on-site at a customer's property. The tech pulls out their tablet, walks through a guided flow to select services from the full price catalog, adjusts pricing as needed, and either collects payment immediately (invoice) or sends an estimate to the customer via email or SMS — all without leaving the field.

This is essentially a **point-of-sale (POS) system** purpose-built for irrigation and landscaping field work.

### Why This Matters for Grins

- **Close deals on-site** — customer sees a professional estimate immediately, no "we'll get back to you" delay that loses jobs
- **Eliminate manual quoting** — no more writing prices on paper, driving home, typing it into the system, then emailing
- **Collect payment in the field** — for completed repairs, mark as paid with cash/check/Venmo/Zelle right there
- **Consistent pricing** — techs pull from the official price list, not from memory (avoids undercharging or misquoting)
- **Professional appearance** — branded PDF estimate/invoice builds customer confidence
- **Faster cash flow** — invoice immediately instead of days later, collect on-site when possible
- **Complete audit trail** — every quote and invoice is tracked in the system from the moment of creation

### What Already Exists in the Platform

Before building, it's important to understand what we can leverage:

| Component | Status | Details |
|-----------|--------|---------|
| **Invoice model** | Exists | Full model with line items (JSONB), statuses, payment methods, lien tracking |
| **Invoice API** | Exists | CRUD, send, payment recording, reminders, lien workflow |
| **Invoice UI components** | Exists | `InvoiceForm.tsx`, `InvoiceDetail.tsx`, `PaymentDialog.tsx`, `InvoiceList.tsx` |
| **Service offerings model** | Exists | Categories, pricing models (flat/zone/hourly/custom), but only ~5 categories — not the full price list |
| **SMS via Twilio** | Exists | Full integration with opt-in, deduplication, delivery tracking |
| **JWT auth + roles** | Exists | Staff can already log in from any device |
| **Job model with quotes** | Exists | `quoted_amount`, `final_amount`, `payment_collected_on_site` fields |
| **AI estimate generation** | Exists | GPT-powered estimate tool with similar job lookup |
| **PDF generation** | Missing | No PDF library installed, no templates |
| **Email sending** | Missing | No SMTP/email service configured |
| **Estimate as first-class entity** | Missing | Estimates are just a field on jobs, not their own model |
| **Service catalog with full price list** | Missing | DB has sparse service offerings, full price list is only in markdown |
| **Stripe/card payment processing** | Missing | Enum value exists but no actual integration |
| **Signature capture** | Missing | No e-signature capability |

### User Journey — The 6-Step Wizard

The wizard is a full-screen, tablet-optimized stepper flow accessible from the admin dashboard sidebar navigation. Designed for large touch targets, minimal typing, and fast completion.

#### Pre-Step: Customer Association (Optional)

Before entering the wizard, the tech can optionally associate the quote with a customer:
- **Search existing customers** — type-ahead search by name, address, or phone
- **Quick-add new customer** — minimal form: name, phone, email, address
- **Skip for now** — generate a generic quote and associate a customer later

This is optional because sometimes a tech is giving a neighbor a quick estimate and doesn't want to create a customer record yet.

#### Step 1: Start New Quote

A single screen with one prominent button:

```
┌─────────────────────────────────────────────┐
│                                             │
│         GRINS IRRIGATION & LANDSCAPING      │
│                                             │
│    ┌───────────────────────────────────┐    │
│    │                                   │    │
│    │     [ + New Quote / Invoice ]     │    │
│    │                                   │    │
│    └───────────────────────────────────┘    │
│                                             │
│    Recent Quotes:                           │
│    ● EST-2026-0042 — Johnson, 2/7/26       │
│    ● INV-2026-0089 — Smith, 2/6/26         │
│    ● EST-2026-0041 — Peterson, 2/5/26      │
│                                             │
└─────────────────────────────────────────────┘
```

**Key decision**: The tech does NOT choose "estimate" vs "invoice" here. They just start building line items. The output type is chosen at the very end (Step 6) because the service selection process is identical, and the tech might change their mind.

Below the button, show recent quotes/invoices created by this tech for quick reference or duplication.

#### Step 2: Select Service Category

A grid of category cards, each with an icon, name, and count of services within. Two columns on tablet, three on desktop.

```
┌──────────────────────────────────────────────┐
│  ← Back                        Step 2 of 6   │
│                                              │
│  SELECT SERVICE CATEGORY                     │
│                                              │
│  ┌───────────────┐  ┌───────────────┐       │
│  │ 💧            │  │ 🔧            │       │
│  │ Irrigation    │  │ Maintenance   │       │
│  │ Installation  │  │ & Repair      │       │
│  │ (3 services)  │  │ (12 services) │       │
│  └───────────────┘  └───────────────┘       │
│                                              │
│  ┌───────────────┐  ┌───────────────┐       │
│  │ 🚗            │  │ 📦            │       │
│  │ Service Fees  │  │ Annual        │       │
│  │ & Travel      │  │ Packages      │       │
│  │ (4 services)  │  │ (3 packages)  │       │
│  └───────────────┘  └───────────────┘       │
│                                              │
│  ┌───────────────┐  ┌───────────────┐       │
│  │ 🌿            │  │ 🧱            │       │
│  │ Landscape     │  │ Hardscaping   │       │
│  │ Design &      │  │               │       │
│  │ Installation  │  │ (6 services)  │       │
│  │ (8 services)  │  │               │       │
│  └───────────────┘  └───────────────┘       │
│                                              │
│  ┌───────────────┐  ┌───────────────┐       │
│  │ ✂️            │  │ 🪨            │       │
│  │ Edging        │  │ Mulch &       │       │
│  │ Installation  │  │ Decorative    │       │
│  │ (5 services)  │  │ Rock          │       │
│  └───────────────┘  │ (7 materials) │       │
│                      └───────────────┘       │
│                                              │
│  ┌───────────────┐  ┌───────────────┐       │
│  │ 🏗️            │  │ 🌳            │       │
│  │ Grading &     │  │ Tree &        │       │
│  │ Soil Prep     │  │ Debris        │       │
│  │ (9 services)  │  │ Removal       │       │
│  └───────────────┘  │ (8 services)  │       │
│                      └───────────────┘       │
│                                              │
│  ┌───────────────┐                           │
│  │ ❄️            │                           │
│  │ Winter        │                           │
│  │ Services      │                           │
│  │ (5 services)  │                           │
│  └───────────────┘                           │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ 🛒 Cart: 0 items         $0.00      │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

**Service Categories** (mapped from price list):

| # | Category | Service Count | Icon |
|---|----------|--------------|------|
| 1 | Irrigation Installation | 3 | Water droplet |
| 2 | Maintenance & Repair | 12 | Wrench |
| 3 | Service Fees & Travel | 4 | Truck |
| 4 | Annual Packages | 3 | Package |
| 5 | Landscape Design & Installation | 8 | Plant |
| 6 | Hardscaping | 6 | Bricks |
| 7 | Edging Installation | 5 | Scissors |
| 8 | Mulch & Decorative Rock | 7 | Rock |
| 9 | Grading & Soil Prep | 9 | Construction |
| 10 | Tree & Debris Removal | 8 | Tree |
| 11 | Winter Services | 5 | Snowflake |

A **sticky footer** shows a running cart summary (item count + running total) that persists across all steps.

#### Step 3: Select Specific Services

Within the chosen category, display individual services as selectable list items. Each service shows its name, price range, and pricing unit. Tapping a service selects it and expands an inline form for quantity/measurement input.

```
┌──────────────────────────────────────────────┐
│  ← Categories              Step 3 of 6       │
│                                              │
│  MAINTENANCE & REPAIR                        │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ ☐ Spring Start-Up                   │    │
│  │   $85 - $150  (flat rate)           │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ ☐ Fall Winterization (Blowout)      │    │
│  │   $85 - $150  (flat rate)           │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ ✅ Sprinkler Head Replacement        │    │
│  │   $15 - $50 per head               │    │
│  │   ┌─────────────────────────────┐   │    │
│  │   │ Quantity: [ - ]  8  [ + ]   │   │    │
│  │   │ Price/head: $__35.00___     │   │    │
│  │   │ Subtotal: $280.00           │   │    │
│  │   └─────────────────────────────┘   │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ ✅ Valve Repair/Replacement          │    │
│  │   $125 - $300 per valve             │    │
│  │   ┌─────────────────────────────┐   │    │
│  │   │ Quantity: [ - ]  2  [ + ]   │   │    │
│  │   │ Price/valve: $__200.00__    │   │    │
│  │   │ Subtotal: $400.00           │   │    │
│  │   └─────────────────────────────┘   │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ ☐ Backflow Testing                  │    │
│  │   $75 - $125  (flat rate)           │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ... (remaining services)                    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ 🛒 Cart: 2 items         $680.00    │    │
│  │ [ + Add More Services ] [ Review → ]│    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

**Dynamic input types per pricing unit:**

| Pricing Unit | Input Type | Label | Example |
|-------------|------------|-------|---------|
| `flat` | None (just select) | — | Spring Start-Up: $85–$150 |
| `per_unit` | Quantity stepper (+/−) | "Qty" | Sprinkler heads: 8 × $35 |
| `per_sqft` | Number input | "Square feet" | Sod: 2,000 sq ft × $2.25 |
| `per_linear_ft` | Number input | "Linear feet" | Metal edging: 150 ft × $10 |
| `per_zone` | Quantity stepper (+/−) | "Zones" | Irrigation install: 6 × $800 |
| `per_cubic_yard` | Number input | "Cubic yards" | Mulch: 5 yd³ × $65 |
| `per_ton` | Number input | "Tons" | River rock: 3 tons × $125 |
| `hourly` | Number input | "Hours" | Labor: 4 hrs × $85 |
| `per_mile` | Number input | "Miles (beyond 30)" | Travel: 15 mi × $1.50 |

**Price defaults**: When a service is selected, the price defaults to the **midpoint** of the range. The tech can adjust up or down within (or beyond) the range. The range is shown as a reference but not enforced — sometimes jobs warrant pricing outside the standard range.

For **flat rate** items with a range (e.g., Spring Start-Up $85–$150), the tech gets a simple price input pre-filled with the midpoint, because the final price depends on property size/complexity that only the tech knows on-site.

#### Step 4: Add Another Service or Continue

This isn't a separate screen — it's the **sticky footer** behavior from Step 3:

```
┌──────────────────────────────────────┐
│ 🛒 Cart: 2 items         $680.00    │
│ [ + Add More Services ] [ Review → ]│
└──────────────────────────────────────┘
```

- **"+ Add More Services"** → navigates back to Step 2 (category grid) with the cart preserved
- **"Review →"** → advances to Step 5

The tech can loop through Steps 2–4 as many times as needed, building up their cart across multiple categories. For example: select sprinkler repairs from Maintenance, then add mulch from Mulch & Rock, then add a travel fee from Service Fees.

The cart persists across all navigation and shows a running count + total at all times.

#### Step 5: Review & Adjust

A complete review of all selected line items with the ability to edit prices, quantities, add discounts, and include notes.

```
┌──────────────────────────────────────────────┐
│  ← Back                        Step 5 of 6   │
│                                              │
│  REVIEW YOUR SELECTIONS                      │
│                                              │
│  Customer: John Peterson                     │
│  Property: 1234 Oak St, Minneapolis, MN      │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ 1. Sprinkler Head Replacement       │    │
│  │    8 heads × $35.00       $280.00   │    │
│  │    [Edit] [Remove]                  │    │
│  ├──────────────────────────────────────┤    │
│  │ 2. Valve Repair/Replacement         │    │
│  │    2 valves × $200.00     $400.00   │    │
│  │    [Edit] [Remove]                  │    │
│  ├──────────────────────────────────────┤    │
│  │ 3. Cedar Mulch Installation         │    │
│  │    5 yd³ × $75.00         $375.00   │    │
│  │    [Edit] [Remove]                  │    │
│  ├──────────────────────────────────────┤    │
│  │ 4. Service Call Fee                 │    │
│  │    1 × $75.00              $75.00   │    │
│  │    [Edit] [Remove]                  │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ Subtotal:                 $1,130.00 │    │
│  │ Discount: [ $_____ ] or [ __% ]     │    │
│  │ Discount Amount:             -$0.00 │    │
│  │ ─────────────────────────────────── │    │
│  │ TOTAL:                    $1,130.00 │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  Notes (optional):                           │
│  ┌──────────────────────────────────────┐    │
│  │ Existing backflow preventer in good  │    │
│  │ condition. Recommend full inspection │    │
│  │ in spring.                          │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  [ + Add More Services ]                     │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │        [ Continue to Step 6 → ]     │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

**Editing a line item**: Tapping "Edit" opens an inline editor (same as Step 3 expansion) where the tech can change quantity and unit price. Tapping "Remove" deletes the line item with a confirmation.

**Discount options**:
- Flat dollar amount (e.g., $50 off)
- Percentage (e.g., 10% off)
- Toggle between the two
- Common quick-select buttons: 5%, 10%, 15%, 20% (matching the package discount tiers)

**Notes field**: Free-text area for special conditions, observations, or recommendations. This appears on the generated PDF.

**"+ Add More Services"**: Takes the tech back to Step 2 if they realize they forgot something.

#### Step 6: Generate & Deliver

The final step where the tech chooses the output type and delivery method.

```
┌──────────────────────────────────────────────┐
│  ← Back                        Step 6 of 6   │
│                                              │
│  GENERATE DOCUMENT                           │
│                                              │
│  Total: $1,130.00                            │
│                                              │
│  What would you like to generate?            │
│                                              │
│  ┌───────────────────┐ ┌───────────────────┐ │
│  │                   │ │                   │ │
│  │   📋 ESTIMATE     │ │   💰 INVOICE      │ │
│  │                   │ │                   │ │
│  │ Send a quote for  │ │ Bill for work     │ │
│  │ customer review   │ │ completed today   │ │
│  │                   │ │                   │ │
│  └───────────────────┘ └───────────────────┘ │
│                                              │
└──────────────────────────────────────────────┘
```

**Path A — Generate Estimate:**

```
┌──────────────────────────────────────────────┐
│  ESTIMATE — EST-2026-0043                    │
│                                              │
│  Valid for: [30] days (until 3/9/2026)       │
│                                              │
│  How should we deliver this estimate?        │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │ ☐ Email                             │    │
│  │   [john.peterson@email.com_______]  │    │
│  ├──────────────────────────────────────┤    │
│  │ ☐ Text Message (SMS)               │    │
│  │   [(612) 555-0142________________]  │    │
│  ├──────────────────────────────────────┤    │
│  │ ☐ Both (Email + SMS)               │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  [Preview PDF]                               │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │     [ Send Estimate ]               │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  Estimate saved as draft. You can also       │
│  send it later from the dashboard.           │
└──────────────────────────────────────────────┘
```

- Auto-fills email/phone from customer record (if associated)
- Manual entry for new contacts
- "Preview PDF" opens a modal showing the rendered estimate
- "Send Estimate" dispatches via chosen channel(s) and marks status as `sent`
- SMS sends a short message with a link to view the estimate online (hosted PDF or web view)
- Email sends the PDF as an attachment with a branded email body
- Estimate is saved to the database regardless of delivery (can always send later)

**Path B — Generate Invoice:**

```
┌──────────────────────────────────────────────┐
│  INVOICE — INV-2026-0090                     │
│                                              │
│  Due: [Net 30] (3/9/2026)                    │
│  Due terms: [Net 15 ▼] [Net 30] [Due Now]   │
│                                              │
│  Collect payment now?                        │
│                                              │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │  💵 Cash  │ │  📝 Check │ │  📱 Venmo │  │
│  └───────────┘ └───────────┘ └───────────┘  │
│  ┌───────────┐ ┌───────────┐                 │
│  │  🏦 Zelle │ │  💳 Card  │                 │
│  └───────────┘ └───────────┘                 │
│                                              │
│  — or —                                      │
│                                              │
│  [ Send Invoice for Later Payment ]          │
│  (via Email / SMS, same as estimate flow)    │
│                                              │
│  [Preview PDF]                               │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │     [ Complete & Save ]             │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘
```

**Payment collection on-site:**
- **Cash**: Mark as paid immediately, optional receipt generation
- **Check**: Enter check number as reference, mark as paid
- **Venmo**: Display Grins Venmo handle/QR code, tech confirms payment received
- **Zelle**: Display Grins Zelle phone/email, tech confirms payment received
- **Card**: Future Stripe integration — customer taps/inserts card (requires Stripe Terminal or Stripe payment link)

**Send for later payment:**
- Same email/SMS delivery flow as estimates
- Invoice includes payment instructions (Venmo handle, Zelle info, mailing address for checks)
- Due date based on selected terms (Net 15, Net 30, Due on Receipt)

### Data Model Changes

#### New Table: `estimates`

```sql
CREATE TABLE estimates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    property_id UUID REFERENCES properties(id) ON DELETE SET NULL,
    created_by UUID REFERENCES staff(id) NOT NULL,

    -- Numbering
    estimate_number VARCHAR(20) UNIQUE NOT NULL,  -- "EST-2026-0001"

    -- Line Items
    line_items JSONB NOT NULL DEFAULT '[]',
    -- Each item: {
    --   service_catalog_id: UUID,
    --   description: str,
    --   quantity: Decimal,
    --   unit_label: str (e.g., "heads", "sq ft"),
    --   unit_price: Decimal,
    --   total: Decimal
    -- }

    -- Pricing
    subtotal DECIMAL(10,2) NOT NULL,
    discount_type VARCHAR(10),          -- "flat" or "percent"
    discount_value DECIMAL(10,2),       -- dollar amount or percentage
    discount_amount DECIMAL(10,2) DEFAULT 0,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    total DECIMAL(10,2) NOT NULL,

    -- Validity
    estimate_date DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_until DATE,                   -- expiration date (e.g., 30 days out)

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- Statuses: draft, sent, viewed, accepted, declined, expired, converted

    -- Delivery
    delivery_method VARCHAR(10),        -- "email", "sms", "both"
    delivery_email VARCHAR(255),
    delivery_phone VARCHAR(20),
    sent_at TIMESTAMP WITH TIME ZONE,
    viewed_at TIMESTAMP WITH TIME ZONE,

    -- Conversion
    converted_to_invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    converted_at TIMESTAMP WITH TIME ZONE,

    -- Content
    notes TEXT,
    internal_notes TEXT,                -- tech-only notes, not shown to customer

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_estimates_customer ON estimates(customer_id);
CREATE INDEX idx_estimates_status ON estimates(status);
CREATE INDEX idx_estimates_created_by ON estimates(created_by);
CREATE INDEX idx_estimates_number ON estimates(estimate_number);
```

#### Expand `service_offerings` Table (or New `service_catalog` Table)

The existing `service_offerings` table needs to be populated with the full price list. Additional fields needed:

```sql
ALTER TABLE service_offerings ADD COLUMN price_min DECIMAL(10,2);
ALTER TABLE service_offerings ADD COLUMN price_max DECIMAL(10,2);
ALTER TABLE service_offerings ADD COLUMN default_price DECIMAL(10,2);
ALTER TABLE service_offerings ADD COLUMN pricing_unit VARCHAR(20);
    -- "flat", "per_unit", "per_sqft", "per_linear_ft",
    -- "per_zone", "per_cubic_yard", "per_ton", "hourly", "per_mile"
ALTER TABLE service_offerings ADD COLUMN unit_label VARCHAR(30);
    -- "per head", "per sq ft", "per linear foot", "per zone",
    -- "per cubic yard", "per ton", "per hour", "per mile"
ALTER TABLE service_offerings ADD COLUMN display_category VARCHAR(50);
    -- More granular than existing category enum:
    -- "Irrigation Installation", "Maintenance & Repair",
    -- "Service Fees & Travel", "Annual Packages",
    -- "Landscape Design & Installation", "Hardscaping",
    -- "Edging Installation", "Mulch & Decorative Rock",
    -- "Grading & Soil Prep", "Tree & Debris Removal",
    -- "Winter Services"
ALTER TABLE service_offerings ADD COLUMN sort_order INTEGER DEFAULT 0;
ALTER TABLE service_offerings ADD COLUMN icon VARCHAR(10);  -- emoji for category display
```

#### Service Catalog Seed Data

All 65+ services from the price list need to be seeded into the database. Example entries:

```json
[
  {
    "name": "Irrigation System Installation",
    "display_category": "Irrigation Installation",
    "category": "installation",
    "price_min": 800.00,
    "price_max": 800.00,
    "default_price": 800.00,
    "pricing_unit": "per_zone",
    "unit_label": "per zone",
    "sort_order": 1
  },
  {
    "name": "Sprinkler Head Replacement",
    "display_category": "Maintenance & Repair",
    "category": "repair",
    "price_min": 15.00,
    "price_max": 50.00,
    "default_price": 32.50,
    "pricing_unit": "per_unit",
    "unit_label": "per head",
    "sort_order": 1
  },
  {
    "name": "Sod Installation",
    "display_category": "Landscape Design & Installation",
    "category": "landscaping",
    "price_min": 1.50,
    "price_max": 3.00,
    "default_price": 2.25,
    "pricing_unit": "per_sqft",
    "unit_label": "per sq ft",
    "sort_order": 6
  },
  {
    "name": "Metal/Steel Edging",
    "display_category": "Edging Installation",
    "category": "landscaping",
    "price_min": 8.00,
    "price_max": 12.00,
    "default_price": 10.00,
    "pricing_unit": "per_linear_ft",
    "unit_label": "per linear foot",
    "sort_order": 2
  },
  {
    "name": "Hourly Labor Rate (General Repairs)",
    "display_category": "Maintenance & Repair",
    "category": "repair",
    "price_min": 75.00,
    "price_max": 100.00,
    "default_price": 87.50,
    "pricing_unit": "hourly",
    "unit_label": "per hour",
    "description": "2 hour minimum",
    "sort_order": 12
  }
]
```

The full seed migration will include all 65+ services organized by the 11 display categories.

### Backend Implementation

#### New API Endpoints

**Estimate Endpoints:**
```
POST   /api/v1/estimates                    — Create estimate
GET    /api/v1/estimates                    — List estimates (paginated, filterable)
GET    /api/v1/estimates/{id}               — Get estimate detail
PUT    /api/v1/estimates/{id}               — Update estimate (draft only)
DELETE /api/v1/estimates/{id}               — Cancel/delete estimate
POST   /api/v1/estimates/{id}/send          — Send via email/SMS
POST   /api/v1/estimates/{id}/convert       — Convert estimate → invoice
GET    /api/v1/estimates/public/{token}     — Public view (for customer link via SMS)
```

**Service Catalog Endpoints:**
```
GET    /api/v1/service-catalog              — List all active services
GET    /api/v1/service-catalog/categories   — List categories with service counts
GET    /api/v1/service-catalog/{category}   — List services in a category
```

**PDF Generation Endpoints:**
```
GET    /api/v1/estimates/{id}/pdf           — Generate/download estimate PDF
GET    /api/v1/invoices/{id}/pdf            — Generate/download invoice PDF
```

#### New Services

**`estimate_service.py`**
- Estimate number generation (EST-YEAR-SEQUENCE)
- Create, update, cancel estimates
- Send estimate via email/SMS
- Convert estimate to invoice (copies line items, creates invoice, links records)
- Expiration checking (mark expired estimates)
- Status transitions (draft → sent → viewed → accepted/declined/expired/converted)

**`pdf_service.py`**
- HTML template rendering via Jinja2
- PDF generation via `weasyprint` (or alternative — see Architectural Decisions)
- Estimate PDF template (company branding, line items, terms, validity period)
- Invoice PDF template (company branding, line items, payment instructions, due date)
- Shared template components (header, footer, line item table, totals)

**`email_service.py`**
- Email sending via SendGrid (recommended, since already on Twilio ecosystem) or Resend
- HTML email templates for estimate delivery
- HTML email templates for invoice delivery
- Attachment support (PDF)

#### New Models

**`estimate.py`** (SQLAlchemy model)
- Mirrors the SQL schema above
- Relationships: customer, job, property, created_by (staff), converted_to_invoice
- Status enum: `draft`, `sent`, `viewed`, `accepted`, `declined`, `expired`, `converted`

#### Database Migrations

1. **Migration: Expand service_offerings** — Add `price_min`, `price_max`, `default_price`, `pricing_unit`, `unit_label`, `display_category`, `sort_order`, `icon` columns
2. **Migration: Seed service catalog** — Insert all 65+ services from price list
3. **Migration: Create estimates table** — Full table with indexes
4. **Migration: Add PDF-related fields to invoices** — If needed (e.g., `pdf_generated_at`, `pdf_url`)

### Frontend Implementation

#### New Components

**Wizard Container:**
- `FieldQuoteWizard.tsx` — Main wizard component managing step state, cart state, and navigation
- `WizardStepIndicator.tsx` — Step progress bar (1–6) at top of screen
- `CartFooter.tsx` — Sticky bottom bar showing cart count + total + action buttons

**Step Components:**
- `CustomerSelector.tsx` — Search/select or quick-add customer (pre-step)
- `QuoteStartStep.tsx` — Step 1: "New Quote" button + recent quotes list
- `CategoryGrid.tsx` — Step 2: Grid of service category cards
- `ServiceSelector.tsx` — Step 3: Service list with inline quantity/price inputs
- `QuantityInput.tsx` — Dynamic input component that adapts per pricing unit
- `ReviewStep.tsx` — Step 5: Full line item review with edit/remove/discount
- `GenerateStep.tsx` — Step 6: Choose estimate vs invoice + delivery/payment

**PDF & Delivery:**
- `PDFPreviewModal.tsx` — Modal to preview generated PDF
- `DeliveryForm.tsx` — Email/SMS delivery inputs
- `PaymentCollector.tsx` — On-site payment method selection + confirmation

**Shared/Reusable:**
- `LineItemCard.tsx` — Reusable line item display (used in Steps 3 and 5)
- `PriceRangeInput.tsx` — Number input with min/max range indicator
- `DiscountSelector.tsx` — Flat vs percentage discount toggle with quick-select buttons

#### State Management

The wizard state is complex and spans multiple steps. Use a **React context + reducer** pattern:

```typescript
interface QuoteWizardState {
  // Customer
  customer: Customer | null;

  // Cart (persists across steps 2-4 loop)
  lineItems: QuoteLineItem[];

  // Pricing
  subtotal: number;
  discountType: 'flat' | 'percent' | null;
  discountValue: number;
  discountAmount: number;
  total: number;

  // Output
  outputType: 'estimate' | 'invoice' | null;
  notes: string;
  internalNotes: string;

  // Estimate-specific
  validDays: number;  // default 30

  // Invoice-specific
  paymentTerms: 'due_now' | 'net_15' | 'net_30';
  paymentMethod: PaymentMethod | null;
  paymentReference: string;

  // Delivery
  deliveryMethod: 'email' | 'sms' | 'both' | null;
  deliveryEmail: string;
  deliveryPhone: string;

  // Navigation
  currentStep: number;
  selectedCategory: string | null;
}

interface QuoteLineItem {
  id: string;                    // client-side UUID for key prop
  serviceCatalogId: string;      // FK to service_offerings
  name: string;
  category: string;
  quantity: number;
  unitLabel: string;
  unitPrice: number;
  priceMin: number;
  priceMax: number;
  total: number;
}
```

Use **TanStack Query** (already in the project) for fetching service catalog data, and the reducer for local wizard state. Only persist to the backend when the user finalizes in Step 6.

#### Routing

New route: `/admin/field-quote` — dedicated full-screen wizard, accessible from sidebar nav.

Optional: `/admin/field-quote/:estimateId/edit` — edit an existing draft estimate.

Optional: `/estimates/:token` — public-facing estimate view for customers (accessed via SMS/email link).

### PDF Template Design

Both estimate and invoice PDFs share a common layout:

```
┌──────────────────────────────────────────────┐
│  [GRINS LOGO]     GRINS IRRIGATION &         │
│                   LANDSCAPING                 │
│                   Phone: (XXX) XXX-XXXX       │
│                   Email: info@grins.com       │
│                   License #: XXXXXXX          │
│                                              │
│  ─────────────────────────────────────────── │
│                                              │
│  ESTIMATE #EST-2026-0043                     │
│  Date: February 7, 2026                      │
│  Valid Until: March 9, 2026                  │
│  — or —                                      │
│  INVOICE #INV-2026-0090                      │
│  Date: February 7, 2026                      │
│  Due Date: March 9, 2026                     │
│                                              │
│  ─────────────────────────────────────────── │
│                                              │
│  BILL TO:                                    │
│  John Peterson                               │
│  1234 Oak St                                 │
│  Minneapolis, MN 55401                       │
│  (612) 555-0142                              │
│                                              │
│  ─────────────────────────────────────────── │
│                                              │
│  SERVICE          QTY    RATE      AMOUNT    │
│  ─────────────────────────────────────────── │
│  Sprinkler Head   8 hd   $35.00   $280.00   │
│  Replacement                                 │
│                                              │
│  Valve Repair/    2 vlv  $200.00  $400.00    │
│  Replacement                                 │
│                                              │
│  Cedar Mulch      5 yd³  $75.00   $375.00    │
│  Installation                                │
│                                              │
│  Service Call Fee 1      $75.00    $75.00    │
│                                              │
│  ─────────────────────────────────────────── │
│                                              │
│                    Subtotal:     $1,130.00    │
│                    Discount:         $0.00    │
│                    TOTAL:        $1,130.00    │
│                                              │
│  ─────────────────────────────────────────── │
│                                              │
│  Notes:                                      │
│  Existing backflow preventer in good         │
│  condition. Recommend full inspection        │
│  in spring.                                  │
│                                              │
│  ─────────────────────────────────────────── │
│                                              │
│  (Estimate footer:)                          │
│  This estimate is valid for 30 days.         │
│  To accept, contact us at (XXX) XXX-XXXX.   │
│                                              │
│  (Invoice footer:)                           │
│  Payment Methods:                            │
│  • Venmo: @grins-irrigation                  │
│  • Zelle: (XXX) XXX-XXXX                    │
│  • Check: Mail to [address]                  │
│  • Card: Pay online at [link]                │
│                                              │
│  Thank you for choosing Grins!               │
└──────────────────────────────────────────────┘
```

Templates built with HTML/CSS (Jinja2) and rendered to PDF via `weasyprint`. The same data model feeds both the web preview and the PDF.

### Architectural Decisions

| Decision | Options Considered | Chosen | Rationale |
|----------|-------------------|--------|-----------|
| Estimate vs Invoice selection timing | Upfront (Step 1) / End (Step 6) | **End (Step 6)** | Same selection flow for both; tech may change mind; reduces cognitive load at start |
| Estimate data model | Reuse Invoice table / Separate table | **Separate `estimates` table** | Different lifecycles, statuses, and business rules; avoids polluting invoice logic with estimate conditionals |
| PDF generation | `weasyprint` / `reportlab` / `fpdf2` / `@react-pdf/renderer` | **`weasyprint`** | HTML/CSS templates are easy to design and maintain; Jinja2 already in deps; professional output |
| Email provider | Twilio SendGrid / Resend / AWS SES / SMTP | **Twilio SendGrid** | Already on Twilio ecosystem; simple API; good deliverability; free tier covers volume |
| Price list data storage | New table / Expand `service_offerings` | **Expand `service_offerings`** | Avoid table proliferation; existing model already has pricing fields; just needs more columns and seed data |
| Offline support | Online-only / PWA / localStorage | **Online-only (v1)** | Simplest; cellular coverage adequate for metro MN; can add PWA later if needed |
| Customer association | Required / Optional | **Optional** | Sometimes quick verbal estimates don't need a customer record; can associate later |
| Wizard UI pattern | Full-page stepper / Modal / Drawer | **Full-page stepper** | Tablet needs full screen real estate; modals too cramped; dedicated route allows deep linking |
| Frontend state management | Context + Reducer / Zustand / Redux | **Context + Reducer** | Already using React context patterns in the project; wizard state is localized, doesn't need global store |
| SMS estimate delivery | Send PDF / Send link | **Send link** | MMS is unreliable and expensive; short URL to a public web view is cleaner and trackable (view receipts) |

### Integration Points

**With Existing Invoice System:**
- "Convert to Invoice" creates an invoice from estimate data using existing `invoice_service.py`
- Estimate line items map directly to invoice line items (same JSONB structure)
- Invoice payment recording works as-is for on-site collection

**With Existing SMS System:**
- Estimate/invoice delivery via SMS uses existing `sms_service.py`
- Add new message templates for estimate and invoice delivery
- Leverage existing opt-in tracking and deduplication

**With Existing Job System:**
- Optionally associate estimate/invoice with a job
- `job.quoted_amount` can be auto-populated from accepted estimate total
- `job.payment_collected_on_site` flag works with on-site invoice payment

**With Existing Customer System:**
- Customer search for pre-step uses existing customer API
- Quick-add creates customer via existing customer creation endpoint
- Auto-fill email/phone from customer record for delivery

**With Existing Dashboard:**
- New sidebar nav item: "Field Quote"
- New dashboard widgets: "Recent Estimates", "Pending Estimates", "Estimates Awaiting Response"
- Existing "Overdue Invoices" widget already covers invoices created through this flow

### Dependencies (New Libraries)

**Backend:**
| Library | Purpose | Notes |
|---------|---------|-------|
| `weasyprint` | HTML → PDF generation | Requires system-level dependencies (cairo, pango) — needs Docker/Railway config |
| `sendgrid` (or `python-http-client`) | Email sending | Twilio SendGrid Python SDK |
| `shortuuid` or similar | Public estimate URL tokens | Short, unguessable tokens for public links |

**Frontend:**
| Library | Purpose | Notes |
|---------|---------|-------|
| None required | — | Existing stack (React, TanStack Query, React Hook Form, Radix UI, Tailwind) covers all needs |

**Infrastructure:**
| Service | Purpose | Notes |
|---------|---------|-------|
| Twilio SendGrid | Email delivery | Free tier: 100 emails/day — more than enough |
| Railway env vars | SendGrid API key, company info | Add to existing Railway config |

### Implementation Phases

This feature is large. Break it into sub-phases:

**Sub-Phase 12A: Foundation (Backend)**
1. Database migration: expand `service_offerings` with new columns
2. Seed migration: populate all 65+ services from price list
3. Service catalog API endpoints
4. Estimates model, repository, service, API endpoints
5. Estimate number generation (EST-YEAR-XXXXX)

**Sub-Phase 12B: Wizard UI (Frontend)**
1. Wizard container + step navigation + routing
2. Customer selector (pre-step)
3. Category grid (Step 2)
4. Service selector with dynamic inputs (Step 3)
5. Cart state management (Context + Reducer)
6. Cart footer with running total (Step 4)
7. Review & adjustment screen (Step 5)
8. Output type selection (Step 6)

**Sub-Phase 12C: PDF & Delivery**
1. Install and configure `weasyprint`
2. Jinja2 HTML/CSS templates for estimate and invoice PDFs
3. PDF generation service + API endpoints
4. PDF preview modal in frontend
5. SendGrid integration for email delivery
6. SMS delivery for estimates (link to public view)
7. Public estimate view page (customer-facing)

**Sub-Phase 12D: Payment & Polish**
1. On-site payment collection UI (cash, check, Venmo, Zelle)
2. Payment recording integration with existing invoice system
3. Estimate → Invoice conversion flow
4. Dashboard widgets (recent estimates, pending, awaiting response)
5. Estimate expiration handling (auto-expire after validity period)
6. Mobile/tablet responsive polish and testing

### Effort Estimate

| Sub-Phase | Estimate |
|-----------|----------|
| 12A: Foundation (Backend) | 2–3 days |
| 12B: Wizard UI (Frontend) | 3–4 days |
| 12C: PDF & Delivery | 2–3 days |
| 12D: Payment & Polish | 2–3 days |
| Integration Testing | 1 day |
| **Total** | **~10–14 days** |

### Priority

**High** — This is a revenue-impacting feature. Faster quoting means more closed deals, on-site invoicing means faster payment collection, and professional PDFs build customer trust. This should be the primary Phase 12 deliverable.

### Open Questions

1. **Tax handling** — Does Grins charge sales tax on services in Minnesota? If so, what rate? Does it vary by service type?
2. **Company branding** — Do we have a Grins logo file (PNG/SVG) for PDF headers? Brand colors?
3. **Payment details** — What are the actual Venmo handle, Zelle phone/email, and mailing address for the PDF payment section?
4. **Stripe timeline** — Is actual credit card processing (Stripe) in scope for Phase 12, or just the other payment methods?
5. **Estimate approval** — Should customers be able to "accept" an estimate online (click a button in the web view), or is acceptance tracked manually?
6. **Signature capture** — Is e-signature on estimates needed for Phase 12, or a future enhancement?
7. **Photo attachments** — Should techs be able to attach photos (of the property/issue) to estimates?
8. **Multi-property** — Can a single estimate cover work across multiple properties for the same customer?
