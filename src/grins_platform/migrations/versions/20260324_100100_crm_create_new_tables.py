"""CRM Gap Closure: Create new tables.

Revision ID: 20260324_100100
Revises: 20260324_100000
Create Date: 2026-03-24

Creates all new tables required by the CRM Gap Closure spec:
- communications (Req 4)
- customer_photos (Req 9)
- lead_attachments (Req 15)
- estimate_templates (Req 17)
- contract_templates (Req 17)
- estimates (Req 48, 78)
- estimate_follow_ups (Req 51)
- expenses (Req 53)
- campaigns + campaign_recipients (Req 45)
- marketing_budgets (Req 64)
- media_library (Req 49)
- staff_breaks (Req 42)
- audit_log (Req 74)
- business_settings (Req 87)
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260324_100100"
down_revision: Union[str, None] = "20260324_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all new CRM Gap Closure tables."""

    # ── communications ──────────────────────────────────────────────
    op.create_table(
        "communications",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "lead_id",
            sa.UUID(),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("addressed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("addressed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "addressed_by",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "channel IN ('sms','email','phone','voicemail','chat')",
            name="ck_communications_channel",
        ),
        sa.CheckConstraint(
            "direction IN ('inbound','outbound')",
            name="ck_communications_direction",
        ),
    )
    op.create_index("idx_communications_customer_id", "communications", ["customer_id"])
    op.create_index("idx_communications_lead_id", "communications", ["lead_id"])
    op.create_index("idx_communications_addressed", "communications", ["addressed"])

    # ── customer_photos ─────────────────────────────────────────────
    op.create_table(
        "customer_photos",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_key", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("caption", sa.String(500), nullable=True),
        sa.Column(
            "uploaded_by",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "appointment_id",
            sa.UUID(),
            sa.ForeignKey("appointments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_customer_photos_customer_id",
        "customer_photos",
        ["customer_id"],
    )

    # ── lead_attachments ────────────────────────────────────────────
    op.create_table(
        "lead_attachments",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "lead_id",
            sa.UUID(),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_key", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column(
            "attachment_type",
            sa.String(20),
            nullable=False,
            server_default="other",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "attachment_type IN ('estimate','contract','photo','document','other')",
            name="ck_lead_attachments_type",
        ),
    )
    op.create_index("idx_lead_attachments_lead_id", "lead_attachments", ["lead_id"])

    # ── estimate_templates ──────────────────────────────────────────
    op.create_table(
        "estimate_templates",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("line_items", JSONB(), nullable=True),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── contract_templates ──────────────────────────────────────────
    op.create_table(
        "contract_templates",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("terms_and_conditions", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── estimates ───────────────────────────────────────────────────
    op.create_table(
        "estimates",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "lead_id",
            sa.UUID(),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "job_id",
            sa.UUID(),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "template_id",
            sa.UUID(),
            sa.ForeignKey("estimate_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("line_items", JSONB(), nullable=True),
        sa.Column("options", JSONB(), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column(
            "discount_amount",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("promotion_code", sa.String(50), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        # Portal token fields (Req 78)
        sa.Column("customer_token", sa.UUID(), nullable=True, unique=True),
        sa.Column("token_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "token_readonly",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        # Approval tracking
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("approved_ip", sa.String(45), nullable=True),
        sa.Column("approved_user_agent", sa.String(500), nullable=True),
        sa.Column("rejected_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("rejected_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "status IN ('draft','sent','viewed','approved',"
            "'rejected','expired','cancelled')",
            name="ck_estimates_status",
        ),
    )
    op.create_index("idx_estimates_lead_id", "estimates", ["lead_id"])
    op.create_index("idx_estimates_customer_id", "estimates", ["customer_id"])
    op.create_index("idx_estimates_status", "estimates", ["status"])
    op.create_index("idx_estimates_customer_token", "estimates", ["customer_token"])

    # ── estimate_follow_ups ─────────────────────────────────────────
    op.create_table(
        "estimate_follow_ups",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "estimate_id",
            sa.UUID(),
            sa.ForeignKey("estimates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("follow_up_number", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False, server_default="sms"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("promotion_code", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "status IN ('scheduled','sent','cancelled','skipped')",
            name="ck_estimate_follow_ups_status",
        ),
    )
    op.create_index(
        "idx_estimate_follow_ups_estimate_id",
        "estimate_follow_ups",
        ["estimate_id"],
    )
    op.create_index("idx_estimate_follow_ups_status", "estimate_follow_ups", ["status"])

    # ── expenses ────────────────────────────────────────────────────
    op.create_table(
        "expenses",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "job_id",
            sa.UUID(),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "staff_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("vendor", sa.String(200), nullable=True),
        sa.Column("receipt_file_key", sa.String(500), nullable=True),
        sa.Column("receipt_amount_extracted", sa.Numeric(10, 2), nullable=True),
        sa.Column("lead_source", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "category IN ('materials','labor','fuel','equipment','vehicle',"
            "'insurance','marketing','office','subcontractor','other')",
            name="ck_expenses_category",
        ),
    )
    op.create_index("idx_expenses_category", "expenses", ["category"])
    op.create_index("idx_expenses_date", "expenses", ["date"])
    op.create_index("idx_expenses_job_id", "expenses", ["job_id"])

    # ── campaigns ───────────────────────────────────────────────────
    op.create_table(
        "campaigns",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("campaign_type", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("target_audience", JSONB(), nullable=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "campaign_type IN ('email','sms','both')",
            name="ck_campaigns_type",
        ),
        sa.CheckConstraint(
            "status IN ('draft','scheduled','sending','sent','cancelled')",
            name="ck_campaigns_status",
        ),
    )
    op.create_index("idx_campaigns_status", "campaigns", ["status"])

    # ── campaign_recipients ─────────────────────────────────────────
    op.create_table(
        "campaign_recipients",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "campaign_id",
            sa.UUID(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "lead_id",
            sa.UUID(),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "delivery_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("delivered_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_campaign_recipients_campaign_id",
        "campaign_recipients",
        ["campaign_id"],
    )

    # ── marketing_budgets ───────────────────────────────────────────
    op.create_table(
        "marketing_budgets",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("budget_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "actual_spend",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── media_library ───────────────────────────────────────────────
    op.create_table(
        "media_library",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("file_key", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("media_type", sa.String(20), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("caption", sa.String(500), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "media_type IN ('image','video','document')",
            name="ck_media_library_type",
        ),
    )
    op.create_index("idx_media_library_media_type", "media_library", ["media_type"])
    op.create_index("idx_media_library_category", "media_library", ["category"])

    # ── staff_breaks ────────────────────────────────────────────────
    op.create_table(
        "staff_breaks",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "staff_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "appointment_id",
            sa.UUID(),
            sa.ForeignKey("appointments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("start_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("end_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("break_type", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "break_type IN ('lunch','gas','personal','other')",
            name="ck_staff_breaks_type",
        ),
    )
    op.create_index("idx_staff_breaks_staff_id", "staff_breaks", ["staff_id"])

    # ── audit_log ───────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "actor_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_role", sa.String(20), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=True),
        sa.Column("details", JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_audit_log_actor_id", "audit_log", ["actor_id"])
    op.create_index("idx_audit_log_resource_type", "audit_log", ["resource_type"])
    op.create_index("idx_audit_log_created_at", "audit_log", ["created_at"])

    # ── business_settings ───────────────────────────────────────────
    op.create_table(
        "business_settings",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("setting_key", sa.String(100), nullable=False, unique=True),
        sa.Column("setting_value", JSONB(), nullable=True),
        sa.Column(
            "updated_by",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    # Seed default business settings
    op.execute(
        sa.text(
            """
            INSERT INTO business_settings (setting_key, setting_value) VALUES
            ('company_name', '"Grin''s Irrigations"'),
            ('company_address', '""'),
            ('company_phone', '""'),
            ('company_email', '""'),
            ('company_logo_url', '""'),
            ('company_website', '""'),
            ('default_payment_terms_days', '30'),
            ('late_fee_percentage', '0'),
            ('lien_warning_days', '45'),
            ('lien_filing_days', '120'),
            ('day_of_reminder_time', '"07:00"'),
            ('sms_time_window_start', '"08:00"'),
            ('sms_time_window_end', '"21:00"'),
            ('enable_delay_notifications', 'true'),
            ('default_valid_days', '30'),
            ('follow_up_intervals_days', '[3,7,14,21]'),
            ('enable_auto_follow_ups', 'true')
            ON CONFLICT DO NOTHING;
            """,
        ),
    )


def downgrade() -> None:
    """Drop all new CRM Gap Closure tables."""
    op.drop_table("business_settings")
    op.drop_table("audit_log")
    op.drop_table("staff_breaks")
    op.drop_table("media_library")
    op.drop_table("marketing_budgets")
    op.drop_table("campaign_recipients")
    op.drop_table("campaigns")
    op.drop_table("expenses")
    op.drop_table("estimate_follow_ups")
    op.drop_table("estimates")
    op.drop_table("contract_templates")
    op.drop_table("estimate_templates")
    op.drop_table("lead_attachments")
    op.drop_table("customer_photos")
    op.drop_table("communications")
