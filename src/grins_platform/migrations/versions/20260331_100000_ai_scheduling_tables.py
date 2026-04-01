"""AI Scheduling System: Create 6 new tables, extend 4 models, seed.

Revision ID: 20260331_100000
Revises: 20260328_110000
Create Date: 2026-03-31

New tables: service_zones, scheduling_criteria_config,
scheduling_alerts, change_requests, scheduling_chat_sessions,
resource_truck_inventory.

Extended: jobs, staff, customers, appointments.

Seed data: 30 scheduling criteria (6 groups x 5 criteria each).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260331_100000"
down_revision: Union[str, None] = "20260328_110000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create AI scheduling tables, extend existing models, seed criteria."""

    # ── service_zones (MUST be created BEFORE staff extensions) ──────
    op.create_table(
        "service_zones",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("boundary_type", sa.String(20), nullable=False),
        sa.Column("boundary_data", JSONB, nullable=True),
        sa.Column("assigned_staff_ids", JSONB, nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default="true",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── scheduling_criteria_config ───────────────────────────────────
    op.create_table(
        "scheduling_criteria_config",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("criterion_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("criterion_name", sa.String(100), nullable=False),
        sa.Column("criterion_group", sa.String(50), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="50"),
        sa.Column(
            "is_hard_constraint",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "is_enabled", sa.Boolean(), nullable=False, server_default="true",
        ),
        sa.Column("config_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── scheduling_alerts ────────────────────────────────────────────
    op.create_table(
        "scheduling_alerts",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("affected_job_ids", JSONB, nullable=True),
        sa.Column("affected_staff_ids", JSONB, nullable=True),
        sa.Column("criteria_triggered", JSONB, nullable=True),
        sa.Column("resolution_options", JSONB, nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "resolved_by",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved_action", sa.String(50), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schedule_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── change_requests ──────────────────────────────────────────────
    op.create_table(
        "change_requests",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "resource_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("details", JSONB, nullable=True),
        sa.Column(
            "affected_job_id",
            sa.UUID(),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "admin_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── scheduling_chat_sessions ─────────────────────────────────────
    op.create_table(
        "scheduling_chat_sessions",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_role", sa.String(20), nullable=False),
        sa.Column("messages", JSONB, nullable=True),
        sa.Column("context", JSONB, nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default="true",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── resource_truck_inventory ─────────────────────────────────────
    op.create_table(
        "resource_truck_inventory",
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
        sa.Column("part_name", sa.String(100), nullable=False),
        sa.Column(
            "quantity", sa.Integer(), nullable=False, server_default="0",
        ),
        sa.Column(
            "reorder_threshold",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
        sa.Column("last_restocked", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # ── Extend jobs table ────────────────────────────────────────────
    op.add_column(
        "jobs",
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("compliance_deadline", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("job_phase", sa.Integer(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "depends_on_job_id",
            sa.UUID(),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "is_outdoor",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("predicted_complexity", sa.Float(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("revenue_per_hour", sa.Numeric(10, 2), nullable=True),
    )

    # ── Extend staff table ───────────────────────────────────────────
    op.add_column(
        "staff",
        sa.Column("performance_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "staff",
        sa.Column("callback_rate", sa.Float(), nullable=True),
    )
    op.add_column(
        "staff",
        sa.Column("avg_satisfaction", sa.Float(), nullable=True),
    )
    op.add_column(
        "staff",
        sa.Column(
            "service_zone_id",
            sa.UUID(),
            sa.ForeignKey("service_zones.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "staff",
        sa.Column("overtime_threshold_minutes", sa.Integer(), nullable=True),
    )

    # ── Extend customers table ───────────────────────────────────────
    op.add_column(
        "customers",
        sa.Column("clv_score", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column(
            "preferred_resource_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "customers",
        sa.Column("time_window_preference", sa.String(50), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column(
            "time_window_is_hard",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # ── Extend appointments table ────────────────────────────────────
    op.add_column(
        "appointments",
        sa.Column("ai_explanation", sa.Text(), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column("criteria_scores", JSONB, nullable=True),
    )

    # ── Seed scheduling_criteria_config with 30 criteria ─────────────
    criteria_table = sa.table(
        "scheduling_criteria_config",
        sa.column("criterion_number", sa.Integer),
        sa.column("criterion_name", sa.String),
        sa.column("criterion_group", sa.String),
        sa.column("weight", sa.Integer),
        sa.column("is_hard_constraint", sa.Boolean),
        sa.column("is_enabled", sa.Boolean),
    )

    # Hard constraints: criteria 6, 7, 8, 21, 23, 30 → weight 100
    # Soft constraints: all others → weight 50
    op.bulk_insert(
        criteria_table,
        [
            # Geographic (1-5)
            {
                "criterion_number": 1,
                "criterion_name": "Resource-to-Job Proximity",
                "criterion_group": "geographic",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 2,
                "criterion_name": "Intra-Route Drive Time",
                "criterion_group": "geographic",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 3,
                "criterion_name": "Service Zone Boundaries",
                "criterion_group": "geographic",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 4,
                "criterion_name": "Real-Time Traffic",
                "criterion_group": "geographic",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 5,
                "criterion_name": "Job Site Access Constraints",
                "criterion_group": "geographic",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            # Resource (6-10)
            {
                "criterion_number": 6,
                "criterion_name": "Skill/Certification Match",
                "criterion_group": "resource",
                "weight": 100,
                "is_hard_constraint": True,
                "is_enabled": True,
            },
            {
                "criterion_number": 7,
                "criterion_name": "Equipment on Truck",
                "criterion_group": "resource",
                "weight": 100,
                "is_hard_constraint": True,
                "is_enabled": True,
            },
            {
                "criterion_number": 8,
                "criterion_name": "Resource Availability Windows",
                "criterion_group": "resource",
                "weight": 100,
                "is_hard_constraint": True,
                "is_enabled": True,
            },
            {
                "criterion_number": 9,
                "criterion_name": "Workload Balance",
                "criterion_group": "resource",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 10,
                "criterion_name": "Performance History",
                "criterion_group": "resource",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            # Customer/Job (11-15)
            {
                "criterion_number": 11,
                "criterion_name": "Customer Time-Window Preferences",
                "criterion_group": "customer_job",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 12,
                "criterion_name": "Job Type Duration Estimates",
                "criterion_group": "customer_job",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 13,
                "criterion_name": "Job Priority Level",
                "criterion_group": "customer_job",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 14,
                "criterion_name": "Customer Lifetime Value",
                "criterion_group": "customer_job",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 15,
                "criterion_name": "Customer-Resource Relationship",
                "criterion_group": "customer_job",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            # Capacity/Demand (16-20)
            {
                "criterion_number": 16,
                "criterion_name": "Daily Capacity Utilization",
                "criterion_group": "capacity_demand",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 17,
                "criterion_name": "Weekly Demand Forecast",
                "criterion_group": "capacity_demand",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 18,
                "criterion_name": "Seasonal Peak Windows",
                "criterion_group": "capacity_demand",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 19,
                "criterion_name": "Cancellation/No-Show Probability",
                "criterion_group": "capacity_demand",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 20,
                "criterion_name": "Pipeline/Backlog Pressure",
                "criterion_group": "capacity_demand",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            # Business Rules (21-25)
            {
                "criterion_number": 21,
                "criterion_name": "Compliance Deadlines",
                "criterion_group": "business_rules",
                "weight": 100,
                "is_hard_constraint": True,
                "is_enabled": True,
            },
            {
                "criterion_number": 22,
                "criterion_name": "Revenue Per Resource-Hour",
                "criterion_group": "business_rules",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 23,
                "criterion_name": "Contract/SLA Commitments",
                "criterion_group": "business_rules",
                "weight": 100,
                "is_hard_constraint": True,
                "is_enabled": True,
            },
            {
                "criterion_number": 24,
                "criterion_name": "Overtime Cost Threshold",
                "criterion_group": "business_rules",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 25,
                "criterion_name": "Seasonal Pricing Signals",
                "criterion_group": "business_rules",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            # Predictive (26-30)
            {
                "criterion_number": 26,
                "criterion_name": "Weather Forecast Impact",
                "criterion_group": "predictive",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 27,
                "criterion_name": "Predicted Job Complexity",
                "criterion_group": "predictive",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 28,
                "criterion_name": "Lead-to-Job Conversion Timing",
                "criterion_group": "predictive",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 29,
                "criterion_name": "Resource Location at Shift Start",
                "criterion_group": "predictive",
                "weight": 50,
                "is_hard_constraint": False,
                "is_enabled": True,
            },
            {
                "criterion_number": 30,
                "criterion_name": "Cross-Job Dependency Chains",
                "criterion_group": "predictive",
                "weight": 100,
                "is_hard_constraint": True,
                "is_enabled": True,
            },
        ],
    )


def downgrade() -> None:
    """Drop all AI scheduling additions in reverse order."""

    # ── Remove appointments extensions ───────────────────────────────
    op.drop_column("appointments", "criteria_scores")
    op.drop_column("appointments", "ai_explanation")

    # ── Remove customers extensions ──────────────────────────────────
    op.drop_column("customers", "time_window_is_hard")
    op.drop_column("customers", "time_window_preference")
    op.drop_column("customers", "preferred_resource_id")
    op.drop_column("customers", "clv_score")

    # ── Remove staff extensions (drop FK column before service_zones) ─
    op.drop_column("staff", "overtime_threshold_minutes")
    op.drop_column("staff", "service_zone_id")
    op.drop_column("staff", "avg_satisfaction")
    op.drop_column("staff", "callback_rate")
    op.drop_column("staff", "performance_score")

    # ── Remove jobs extensions ───────────────────────────────────────
    op.drop_column("jobs", "revenue_per_hour")
    op.drop_column("jobs", "predicted_complexity")
    op.drop_column("jobs", "is_outdoor")
    op.drop_column("jobs", "depends_on_job_id")
    op.drop_column("jobs", "job_phase")
    op.drop_column("jobs", "compliance_deadline")
    op.drop_column("jobs", "sla_deadline")

    # ── Drop new tables in reverse creation order ────────────────────
    op.drop_table("resource_truck_inventory")
    op.drop_table("scheduling_chat_sessions")
    op.drop_table("change_requests")
    op.drop_table("scheduling_alerts")
    op.drop_table("scheduling_criteria_config")
    op.drop_table("service_zones")
