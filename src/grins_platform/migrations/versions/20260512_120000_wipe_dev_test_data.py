"""Dev-only data wipe: clear accumulated E2E test artifacts.

Deletes every row from the domain tables that accumulate state during
testing (customers, leads, jobs, appointments, estimates, invoices,
messages, audit logs, scheduling state, etc.) so the dev environment
can be re-seeded to a clean slate. Seeded reference tables (admin
``staff`` row, ``service_offerings``, templates, ``business_settings``,
``consent_language_versions``, ``scheduling_criteria_config``,
``service_zones``) are left intact.

This is a DATA-only migration. It contains no DDL — no ``CREATE``,
``ALTER``, ``DROP`` of any table/column/index/constraint, and no
``TRUNCATE`` (so identity sequences are preserved). All schema stays
exactly as it was.

Gated by two env vars. Both must hold or the migration is a no-op:

* ``WIPE_DEV_TEST_DATA=1`` — explicit opt-in. Set in Railway's dev env
  vars right before the wipe deploy; unset afterward so later redeploys
  don't carry the flag.
* ``ENVIRONMENT`` not in {"production", "prod", "live"} AND
  ``RAILWAY_ENVIRONMENT`` not a prod-shaped value.

Downgrade is a no-op (deleted rows aren't reconstructable).

Revision ID: 20260512_120000
Revises: 20260510_120000
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "20260512_120000"
down_revision: Union[str, None] = "20260510_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_PROD_ENVIRONMENT_VALUES = {"production", "prod", "live"}
_ALLOWED_RAILWAY_ENVS = {"", "dev", "development", "staging", "test"}


def _is_dev_environment() -> tuple[bool, str]:
    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    railway_env = os.getenv("RAILWAY_ENVIRONMENT", "").strip().lower()

    if environment in _PROD_ENVIRONMENT_VALUES:
        return False, f"ENVIRONMENT='{environment}' looks like prod"
    if railway_env and railway_env not in _ALLOWED_RAILWAY_ENVS:
        return False, f"RAILWAY_ENVIRONMENT='{railway_env}' looks like prod"
    return True, f"ENVIRONMENT='{environment}', RAILWAY_ENVIRONMENT='{railway_env}'"


# Ordered FK-safe deletion plan. Each entry is a single SQL statement
# the migration will execute against op.get_bind(). Order is critical:
# children before parents, and ``invoices`` strictly before ``jobs``
# because of the RESTRICT FK on jobs.id.
_DELETE_STATEMENTS: list[tuple[str, str]] = [
    # Phase A — Communications & audit (leaf-ish, no test-data FKs into them)
    ("sent_messages", "DELETE FROM sent_messages"),
    ("sms_consent_records", "DELETE FROM sms_consent_records"),
    ("communications", "DELETE FROM communications"),
    ("ai_audit_log", "DELETE FROM ai_audit_log"),
    ("ai_usage", "DELETE FROM ai_usage"),
    ("audit_log", "DELETE FROM audit_log"),
    ("stripe_webhook_events", "DELETE FROM stripe_webhook_events"),
    ("webhook_processed_logs", "DELETE FROM webhook_processed_logs"),
    ("email_suppression_list", "DELETE FROM email_suppression_list"),
    ("disclosure_records", "DELETE FROM disclosure_records"),
    ("scheduling_chat_sessions", "DELETE FROM scheduling_chat_sessions"),
    ("scheduling_alerts", "DELETE FROM scheduling_alerts"),
    ("schedule_clear_audit", "DELETE FROM schedule_clear_audit"),
    ("schedule_reassignments", "DELETE FROM schedule_reassignments"),
    ("schedule_waitlist", "DELETE FROM schedule_waitlist"),
    ("change_requests", "DELETE FROM change_requests"),
    ("alerts", "DELETE FROM alerts"),
    ("google_sheet_submissions", "DELETE FROM google_sheet_submissions"),
    # Phase B — Appointment children, then appointments themselves
    ("reschedule_requests", "DELETE FROM reschedule_requests"),
    ("job_confirmation_responses", "DELETE FROM job_confirmation_responses"),
    ("appointment_attachments", "DELETE FROM appointment_attachments"),
    ("appointment_notes", "DELETE FROM appointment_notes"),
    ("appointment_reminder_log", "DELETE FROM appointment_reminder_log"),
    ("appointments", "DELETE FROM appointments"),
    # Phase C — Job / estimate / invoice chain (invoices BEFORE jobs)
    ("job_status_history", "DELETE FROM job_status_history"),
    ("invoices", "DELETE FROM invoices"),
    ("estimate_follow_ups", "DELETE FROM estimate_follow_ups"),
    ("estimates", "DELETE FROM estimates"),
    ("jobs", "DELETE FROM jobs"),
    # Phase D — Sales / campaigns / agreements
    ("campaign_responses", "DELETE FROM campaign_responses"),
    ("campaign_recipients", "DELETE FROM campaign_recipients"),
    ("campaigns", "DELETE FROM campaigns"),
    ("sales_calendar_events", "DELETE FROM sales_calendar_events"),
    ("sales_entries", "DELETE FROM sales_entries"),
    ("agreement_status_logs", "DELETE FROM agreement_status_logs"),
    ("service_agreements", "DELETE FROM service_agreements"),
    ("contract_renewal_proposed_jobs", "DELETE FROM contract_renewal_proposed_jobs"),
    ("contract_renewal_proposals", "DELETE FROM contract_renewal_proposals"),
    # Phase E — Customer / lead and attached child tables
    ("customer_merge_candidates", "DELETE FROM customer_merge_candidates"),
    ("customer_tags", "DELETE FROM customer_tags"),
    ("customer_photos", "DELETE FROM customer_photos"),
    ("customer_documents", "DELETE FROM customer_documents"),
    ("lead_attachments", "DELETE FROM lead_attachments"),
    ("leads", "DELETE FROM leads"),
    ("properties", "DELETE FROM properties"),
    ("customers", "DELETE FROM customers"),
    # Phase F — Misc test artifacts
    ("expenses", "DELETE FROM expenses"),
    ("marketing_budgets", "DELETE FROM marketing_budgets"),
    ("media_library", "DELETE FROM media_library"),
    ("resource_truck_inventory", "DELETE FROM resource_truck_inventory"),
    # Phase G — Non-admin staff (and their owned rows). Admin user
    # (username='admin', seeded by 20250625_100000) is preserved.
    (
        "webauthn_credentials (non-admin)",
        "DELETE FROM webauthn_credentials WHERE user_id IN "
        "(SELECT id FROM staff WHERE username <> 'admin')",
    ),
    (
        "webauthn_user_handles (non-admin)",
        "DELETE FROM webauthn_user_handles WHERE user_id IN "
        "(SELECT id FROM staff WHERE username <> 'admin')",
    ),
    (
        "staff_availability (non-admin)",
        "DELETE FROM staff_availability WHERE staff_id IN "
        "(SELECT id FROM staff WHERE username <> 'admin')",
    ),
    (
        "staff_breaks (non-admin)",
        "DELETE FROM staff_breaks WHERE staff_id IN "
        "(SELECT id FROM staff WHERE username <> 'admin')",
    ),
    ("staff (non-admin)", "DELETE FROM staff WHERE username <> 'admin'"),
]


def upgrade() -> None:
    if os.getenv("WIPE_DEV_TEST_DATA") != "1":
        print(
            "[wipe_dev_test_data] WIPE_DEV_TEST_DATA != '1'; "
            "skipping wipe (no-op). This is the expected behavior in any "
            "environment that has not deliberately opted in."
        )
        return

    is_dev, env_desc = _is_dev_environment()
    if not is_dev:
        print(
            f"[wipe_dev_test_data] Refusing to wipe: {env_desc}. "
            "This migration must never run against production."
        )
        return

    print(f"[wipe_dev_test_data] Proceeding with wipe ({env_desc}).")

    bind = op.get_bind()
    total = 0
    for label, sql in _DELETE_STATEMENTS:
        result = bind.execute(text(sql))
        rowcount = result.rowcount if result.rowcount is not None else 0
        total += rowcount
        print(f"[wipe_dev_test_data]   {label}: {rowcount} row(s)")

    print(f"[wipe_dev_test_data] Done. {total} row(s) deleted across {len(_DELETE_STATEMENTS)} tables.")


def downgrade() -> None:
    # Data-only wipe; deleted rows are not reconstructable. Intentional no-op.
    pass
