"""Create invoices table.

Revision ID: 20250623_100000
Revises: 20250622_100000
Create Date: 2025-01-29

This migration creates the invoices table for invoice management:
- id: UUID primary key
- job_id: Reference to the job
- customer_id: Reference to the customer
- invoice_number: Unique invoice number (INV-YEAR-SEQ)
- amount: Base invoice amount
- late_fee_amount: Late fee amount (default 0)
- total_amount: Total amount (amount + late_fee)
- invoice_date: Date invoice was created
- due_date: Payment due date
- status: Invoice status (draft, sent, viewed, paid, partial, overdue, etc.)
- payment_method: Method of payment
- payment_reference: Payment reference/transaction ID
- paid_at: Timestamp when payment was received
- paid_amount: Amount paid so far
- reminder_count: Number of reminders sent
- last_reminder_sent: Timestamp of last reminder
- lien_eligible: Whether job type is lien-eligible
- lien_warning_sent: Timestamp of 45-day lien warning
- lien_filed_date: Date lien was filed
- line_items: JSONB array of line items
- notes: Optional notes

Also creates invoice_number_seq sequence for thread-safe numbering.

Requirements: 7.1-7.10
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = "20250623_100000"
down_revision = "20250622_100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create invoices table and invoice_number_seq sequence."""
    # Create sequence for invoice numbers
    op.execute("CREATE SEQUENCE IF NOT EXISTS invoice_number_seq START 1")

    # Create invoices table
    op.create_table(
        "invoices",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "invoice_number",
            sa.String(50),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "amount",
            sa.Numeric(10, 2),
            nullable=False,
        ),
        sa.Column(
            "late_fee_amount",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "total_amount",
            sa.Numeric(10, 2),
            nullable=False,
        ),
        sa.Column(
            "invoice_date",
            sa.Date(),
            nullable=False,
            server_default=sa.text("CURRENT_DATE"),
        ),
        sa.Column(
            "due_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "payment_method",
            sa.String(50),
            nullable=True,
        ),
        sa.Column(
            "payment_reference",
            sa.String(255),
            nullable=True,
        ),
        sa.Column(
            "paid_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "paid_amount",
            sa.Numeric(10, 2),
            nullable=True,
        ),
        sa.Column(
            "reminder_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "last_reminder_sent",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "lien_eligible",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "lien_warning_sent",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "lien_filed_date",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "line_items",
            JSONB(),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
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
        # Check constraint for status enum
        sa.CheckConstraint(
            "status IN ('draft', 'sent', 'viewed', 'paid', 'partial', "
            "'overdue', 'lien_warning', 'lien_filed', 'cancelled')",
            name="ck_invoices_status",
        ),
        # Check constraint for payment_method enum
        sa.CheckConstraint(
            "payment_method IS NULL OR payment_method IN "
            "('cash', 'check', 'venmo', 'zelle', 'stripe')",
            name="ck_invoices_payment_method",
        ),
        # Check constraint for positive amounts
        sa.CheckConstraint(
            "amount >= 0",
            name="ck_invoices_positive_amount",
        ),
        sa.CheckConstraint(
            "late_fee_amount >= 0",
            name="ck_invoices_positive_late_fee",
        ),
        sa.CheckConstraint(
            "total_amount >= 0",
            name="ck_invoices_positive_total",
        ),
        sa.CheckConstraint(
            "paid_amount IS NULL OR paid_amount >= 0",
            name="ck_invoices_positive_paid",
        ),
        sa.CheckConstraint(
            "reminder_count >= 0",
            name="ck_invoices_positive_reminder_count",
        ),
    )

    # Create indexes for performance
    op.create_index(
        "ix_invoices_job_id",
        "invoices",
        ["job_id"],
    )
    op.create_index(
        "ix_invoices_customer_id",
        "invoices",
        ["customer_id"],
    )
    op.create_index(
        "ix_invoices_status",
        "invoices",
        ["status"],
    )
    op.create_index(
        "ix_invoices_invoice_date",
        "invoices",
        ["invoice_date"],
    )
    op.create_index(
        "ix_invoices_due_date",
        "invoices",
        ["due_date"],
    )
    op.create_index(
        "ix_invoices_lien_eligible",
        "invoices",
        ["lien_eligible"],
    )
    # Composite index for overdue invoices query
    op.create_index(
        "ix_invoices_overdue",
        "invoices",
        ["status", "due_date"],
        postgresql_where=sa.text("status NOT IN ('paid', 'cancelled')"),
    )
    # Composite index for lien deadline queries
    op.create_index(
        "ix_invoices_lien_deadlines",
        "invoices",
        ["lien_eligible", "invoice_date", "status"],
        postgresql_where=sa.text(
            "lien_eligible = true "
            "AND status NOT IN ('paid', 'cancelled', 'lien_filed')",
        ),
    )


def downgrade() -> None:
    """Drop invoices table and invoice_number_seq sequence."""
    # Drop indexes
    op.drop_index("ix_invoices_lien_deadlines", table_name="invoices")
    op.drop_index("ix_invoices_overdue", table_name="invoices")
    op.drop_index("ix_invoices_lien_eligible", table_name="invoices")
    op.drop_index("ix_invoices_due_date", table_name="invoices")
    op.drop_index("ix_invoices_invoice_date", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_invoices_customer_id", table_name="invoices")
    op.drop_index("ix_invoices_job_id", table_name="invoices")

    # Drop table
    op.drop_table("invoices")

    # Drop sequence
    op.execute("DROP SEQUENCE IF EXISTS invoice_number_seq")
