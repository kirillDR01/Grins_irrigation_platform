#!/usr/bin/env python3
"""Seed dev DB with fixtures for the payment-links E2E flow.

Creates:
  - one customer with the SMS-allowlist phone + email-allowlist email
  - one job with quoted_amount $50
  - one appointment scheduled for today (08:00–10:00, admin staff)
  - one invoice for $50 (triggers Stripe Payment Link auto-create hook)
  - one separate job + $0 invoice for the F11 hide test

Outputs IDs as shell exports the e2e script can `source`.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

API = os.environ.get("API_BASE", "https://grins-dev-dev.up.railway.app/api/v1")
USERNAME = os.environ.get("E2E_ADMIN_USER", "admin")
PASSWORD = os.environ.get("E2E_ADMIN_PASS", "admin123")
PHONE = "9527373312"
EMAIL = "kirillrakitinsecond@gmail.com"


def call(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode() or "{}"
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body_str = e.read().decode()
        print(f"HTTP {e.code} on {method} {path}: {body_str}", file=sys.stderr)
        raise


def main() -> int:
    auth = call("POST", "/auth/login", {"username": USERNAME, "password": PASSWORD})
    token = auth["access_token"]
    admin_id = auth["user"]["id"]
    print(f"# logged in as {auth['user']['username']} ({admin_id})", file=sys.stderr)

    today = dt.date.today().isoformat()

    # 1. Customer — reuse the existing one matching the SMS-allowlist phone if any.
    existing = call("GET", f"/customers/lookup/phone/{PHONE}", None, token)
    if isinstance(existing, list) and existing:
        customer_id = existing[0]["id"]
        # Refresh email + opt-ins on reuse so the test invariants hold across
        # consecutive runs (bughunt 2026-04-28 §Bug 5).
        call(
            "PUT",
            f"/customers/{customer_id}",
            {
                "email": EMAIL,
                "email_opt_in": True,
                "sms_opt_in": True,
            },
            token,
        )
        print(f"# customer {customer_id} (reused, refreshed)", file=sys.stderr)
    else:
        suffix = dt.datetime.now(dt.UTC).strftime("%H%M%S")
        customer_payload = {
            "first_name": "PaymentLink",
            "last_name": f"E2E{suffix}",
            "phone": PHONE,
            "email": EMAIL,
            "sms_opt_in": True,
            "email_opt_in": True,
            "internal_notes": "Created by scripts/seed_e2e_payment_links.py",
        }
        customer = call("POST", "/customers", customer_payload, token)
        customer_id = customer["id"]
        print(f"# customer {customer_id} (created)", file=sys.stderr)

    # 2a. Job for the paid invoice
    job_payload = {
        "customer_id": customer_id,
        "job_type": "small_repair",
        "description": "E2E payment-link test job",
        "estimated_duration_minutes": 60,
        "quoted_amount": "50.00",
        "priority_level": 1,
    }
    job = call("POST", "/jobs", job_payload, token)
    job_id = job["id"]
    print(f"# job {job_id}", file=sys.stderr)

    # 3. Appointment for today
    appt_payload = {
        "job_id": job_id,
        "staff_id": admin_id,
        "scheduled_date": today,
        "time_window_start": "08:00:00",
        "time_window_end": "10:00:00",
        "notes": "E2E payment-link test appointment",
    }
    appt = call("POST", "/appointments", appt_payload, token)
    appt_id = appt["id"]
    # Walk draft → scheduled → in_progress so the Collect Payment CTA renders.
    final_status = "draft"
    for next_status in ("scheduled", "in_progress"):
        try:
            call("PUT", f"/appointments/{appt_id}", {"status": next_status}, token)
            final_status = next_status
        except urllib.error.HTTPError as e:
            print(
                f"# appointment {appt_id} status→{next_status} failed: {e.code}",
                file=sys.stderr,
            )
            break
    print(f"# appointment {appt_id} ({final_status})", file=sys.stderr)

    # 4. Invoice — triggers auto-create payment link hook
    inv_payload = {
        "job_id": job_id,
        "amount": "50.00",
        "due_date": today,
        "line_items": [
            {
                "description": "E2E test service",
                "quantity": "1",
                "unit_price": "50.00",
                "total": "50.00",
            }
        ],
        "notes": "E2E payment-link invoice",
    }
    inv = call("POST", "/invoices", inv_payload, token)
    inv_id = inv["id"]
    link_url = inv.get("stripe_payment_link_url")
    link_id = inv.get("stripe_payment_link_id")
    print(f"# invoice {inv_id} link={link_url}", file=sys.stderr)

    # 5. $0 invoice — needs a separate job
    zero_job = call("POST", "/jobs", {**job_payload, "description": "E2E $0 job", "quoted_amount": "0"}, token)
    zero_job_id = zero_job["id"]
    zero_inv = call("POST", "/invoices", {
        "job_id": zero_job_id,
        "amount": "0",
        "due_date": today,
        "line_items": [],
        "notes": "E2E $0 invoice",
    }, token)
    zero_inv_id = zero_inv["id"]
    print(f"# zero-invoice {zero_inv_id}", file=sys.stderr)

    # Output as shell exports.
    print(f"export INVOICE_ID={inv_id}")
    print(f"export ZERO_INVOICE_ID={zero_inv_id}")
    print(f"export APPOINTMENT_ID={appt_id}")
    print(f"export CUSTOMER_ID={customer_id}")
    print(f"export STRIPE_PAYMENT_LINK_ID={link_id or ''}")
    print(f"export STRIPE_PAYMENT_LINK_URL={link_url or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
