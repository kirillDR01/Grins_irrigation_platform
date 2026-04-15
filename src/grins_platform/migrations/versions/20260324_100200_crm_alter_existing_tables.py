"""CRM Gap Closure: Alter existing tables.

Revision ID: 20260324_100200
Revises: 20260324_100100
Create Date: 2026-03-24

Alters existing tables for CRM Gap Closure:
- leads: add city, state, address, action_tags (Req 12, 13)
- jobs: add notes, summary (Req 20)
- appointments: add en_route_at, materials_needed, estimated_duration_minutes;
  update status CHECK (Req 35, 40, 79)
- invoices: add pre_due_reminder_sent_at, last_past_due_reminder_at,
  document_url, invoice_token, invoice_token_expires_at (Req 54, 80, 84)
- sent_messages: make customer_id nullable, add lead_id FK,
  add CHECK, update message_type CHECK (Req 81)
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260324_100200"
down_revision: Union[str, None] = "20260324_100100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Alter existing tables for CRM Gap Closure."""

    # ── leads: add address fields and action_tags ───────────────────
    op.add_column("leads", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("leads", sa.Column("state", sa.String(2), nullable=True))
    op.add_column("leads", sa.Column("address", sa.Text(), nullable=True))
    op.add_column(
        "leads",
        sa.Column(
            "action_tags",
            JSONB(),
            nullable=True,
            server_default="[]",
        ),
    )

    # ── jobs: add notes and summary ─────────────────────────────────
    op.add_column("jobs", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("summary", sa.String(255), nullable=True))

    # ── appointments: add new columns and update status CHECK ───────
    op.add_column(
        "appointments",
        sa.Column("en_route_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column("materials_needed", sa.Text(), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=True),
    )

    # Drop old status CHECK and create new one with all 8 values
    op.drop_constraint("ck_appointments_status", "appointments", type_="check")
    op.create_check_constraint(
        "ck_appointments_status",
        "appointments",
        "status IN ('pending','scheduled','confirmed','en_route',"
        "'in_progress','completed','cancelled','no_show')",
    )

    # ── invoices: add reminder tracking, PDF, and portal fields ─────
    op.add_column(
        "invoices",
        sa.Column(
            "pre_due_reminder_sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "last_past_due_reminder_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column("invoices", sa.Column("document_url", sa.String(500), nullable=True))
    op.add_column(
        "invoices",
        sa.Column("invoice_token", sa.UUID(), nullable=True, unique=True),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "invoice_token_expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    # ── sent_messages: make customer_id nullable, add lead_id ───────
    # 1. Drop the existing FK constraint on customer_id
    op.drop_constraint(
        "fk_sent_messages_customer_id",
        "sent_messages",
        type_="foreignkey",
    )
    # 2. Alter customer_id to nullable
    op.alter_column(
        "sent_messages",
        "customer_id",
        existing_type=sa.UUID(),
        nullable=True,
    )
    # 3. Re-add FK constraint
    op.create_foreign_key(
        "fk_sent_messages_customer_id",
        "sent_messages",
        "customers",
        ["customer_id"],
        ["id"],
    )
    # 4. Add lead_id column with FK
    op.add_column(
        "sent_messages",
        sa.Column("lead_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_sent_messages_lead_id",
        "sent_messages",
        "leads",
        ["lead_id"],
        ["id"],
    )
    op.create_index("idx_sent_messages_lead_id", "sent_messages", ["lead_id"])
    # 5. Add CHECK: at least one of customer_id or lead_id must be set
    op.create_check_constraint(
        "ck_sent_messages_recipient",
        "sent_messages",
        "customer_id IS NOT NULL OR lead_id IS NOT NULL",
    )
    # 6. Drop old message_type CHECK and create expanded one
    op.drop_constraint("ck_sent_messages_message_type", "sent_messages", type_="check")
    op.create_check_constraint(
        "ck_sent_messages_message_type",
        "sent_messages",
        "message_type IN ("
        "'appointment_confirmation','appointment_reminder',"
        "'on_the_way','arrival','completion','invoice','payment_reminder',"
        "'custom','lead_confirmation','estimate_sent','contract_sent',"
        "'review_request','campaign')",
    )

    # ── GoogleSheetSubmission → Lead data migration ─────────────────
    op.execute(
        sa.text(
            """
            INSERT INTO leads (name, phone, email, zip_code, situation, notes,
                               source_site, lead_source, city, address, status,
                               created_at, updated_at)
            SELECT
                COALESCE(g.name, 'Unknown'),
                COALESCE(g.phone, '0000000000'),
                g.email,
                NULL,
                CASE
                    WHEN g.new_system_install IS NOT NULL THEN 'new_system'
                    WHEN g.repair_existing IS NOT NULL THEN 'repair'
                    WHEN g.addition_to_system IS NOT NULL THEN 'upgrade'
                    ELSE 'exploring'
                END,
                COALESCE(g.additional_services_info, ''),
                COALESCE(g.referral_source, 'google_form'),
                'google_form',
                g.city,
                g.address,
                'new',
                g.created_at,
                g.created_at
            FROM google_sheet_submissions g
            WHERE g.processing_status = 'imported'
              AND g.promoted_to_lead_id IS NULL
              AND g.lead_id IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM leads l
                  WHERE l.phone = COALESCE(g.phone, '0000000000')
                    AND l.name = COALESCE(g.name, 'Unknown')
              )
            ON CONFLICT DO NOTHING;
            """,
        ),
    )


def downgrade() -> None:
    """Reverse all alterations to existing tables."""

    # ── sent_messages: revert ───────────────────────────────────────
    op.drop_constraint("ck_sent_messages_message_type", "sent_messages", type_="check")
    op.create_check_constraint(
        "ck_sent_messages_message_type",
        "sent_messages",
        "message_type IN ('appointment_confirmation','appointment_reminder',"
        "'on_the_way','arrival','completion','invoice','payment_reminder','custom')",
    )
    op.drop_constraint("ck_sent_messages_recipient", "sent_messages", type_="check")
    op.drop_index("idx_sent_messages_lead_id", table_name="sent_messages")
    op.drop_constraint("fk_sent_messages_lead_id", "sent_messages", type_="foreignkey")
    op.drop_column("sent_messages", "lead_id")
    op.drop_constraint(
        "fk_sent_messages_customer_id",
        "sent_messages",
        type_="foreignkey",
    )
    op.alter_column(
        "sent_messages",
        "customer_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_sent_messages_customer_id",
        "sent_messages",
        "customers",
        ["customer_id"],
        ["id"],
    )

    # ── invoices: revert ────────────────────────────────────────────
    op.drop_column("invoices", "invoice_token_expires_at")
    op.drop_column("invoices", "invoice_token")
    op.drop_column("invoices", "document_url")
    op.drop_column("invoices", "last_past_due_reminder_at")
    op.drop_column("invoices", "pre_due_reminder_sent_at")

    # ── appointments: revert ────────────────────────────────────────
    op.drop_constraint("ck_appointments_status", "appointments", type_="check")
    op.create_check_constraint(
        "ck_appointments_status",
        "appointments",
        "status IN ('scheduled','confirmed','in_progress','completed','cancelled')",
    )
    op.drop_column("appointments", "estimated_duration_minutes")
    op.drop_column("appointments", "materials_needed")
    op.drop_column("appointments", "en_route_at")

    # ── jobs: revert ────────────────────────────────────────────────
    op.drop_column("jobs", "summary")
    op.drop_column("jobs", "notes")

    # ── leads: revert ───────────────────────────────────────────────
    op.drop_column("leads", "action_tags")
    op.drop_column("leads", "address")
    op.drop_column("leads", "state")
    op.drop_column("leads", "city")
