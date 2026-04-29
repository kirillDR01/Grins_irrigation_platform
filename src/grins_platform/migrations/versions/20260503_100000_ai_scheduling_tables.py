"""AI Scheduling System: Create new tables and extend existing models.

Revision ID: 20260503_100000
Revises: 20260502_120000
Create Date: 2026-05-03

Creates 6 new tables for the AI scheduling system:
- scheduling_criteria_config (30 criteria weights, hard/soft, enabled, config_json)
- scheduling_alerts (AI-generated alerts and suggestions)
- change_requests (Resource-initiated change requests)
- scheduling_chat_sessions (AI chat session context)
- resource_truck_inventory (parts inventory per resource truck)
- service_zones (configurable geographic service zones)

Extends 4 existing tables:
- jobs: sla_deadline, compliance_deadline, job_phase, depends_on_job_id,
  is_outdoor, predicted_complexity, revenue_per_hour
- staff: performance_score, callback_rate, avg_satisfaction,
  service_zone_id, overtime_threshold_minutes
- customers: clv_score, preferred_resource_id, time_window_preference,
  time_window_is_hard
- appointments: ai_explanation, criteria_scores

Seeds scheduling_criteria_config with all 30 criteria (numbers 1-30).

Requirements: 3.1-3.5, 4.1-4.5, 5.1-5.5, 6.1-6.5, 7.1-7.5, 8.1-8.5,
              19.1-19.2, 20.1-20.2, 21.1-21.4, 35.1
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "20260503_100000"
down_revision: Union[str, None] = "20260502_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create AI scheduling tables, extend existing models, seed criteria."""

    # ── service_zones (must be created BEFORE staff FK) ─────────────
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
        sa.Column("boundary_data", JSONB(), nullable=True),
        sa.Column("assigned_staff_ids", JSONB(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
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
    op.create_index("ix_service_zones_is_active", "service_zones", ["is_active"])

    # ── scheduling_criteria_config ──────────────────────────────────
    op.create_table(
        "scheduling_criteria_config",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("criterion_number", sa.Integer(), nullable=False),
        sa.Column("criterion_name", sa.String(100), nullable=False),
        sa.Column("criterion_group", sa.String(50), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column(
            "is_hard_constraint",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("config_json", JSONB(), nullable=True),
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
    op.create_index(
        "ix_scheduling_criteria_config_criterion_number",
        "scheduling_criteria_config",
        ["criterion_number"],
        unique=True,
    )
    op.create_index(
        "ix_scheduling_criteria_config_criterion_group",
        "scheduling_criteria_config",
        ["criterion_group"],
    )

    # ── scheduling_alerts ───────────────────────────────────────────
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
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("affected_job_ids", JSONB(), nullable=True),
        sa.Column("affected_staff_ids", JSONB(), nullable=True),
        sa.Column("criteria_triggered", JSONB(), nullable=True),
        sa.Column("resolution_options", JSONB(), nullable=True),
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
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("schedule_date", sa.Date(), nullable=True),
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
            "status IN ('active','resolved','dismissed','expired')",
            name="ck_scheduling_alerts_status",
        ),
    )
    op.create_index(
        "ix_scheduling_alerts_alert_type",
        "scheduling_alerts",
        ["alert_type"],
    )
    op.create_index(
        "ix_scheduling_alerts_severity",
        "scheduling_alerts",
        ["severity"],
    )
    op.create_index(
        "ix_scheduling_alerts_status",
        "scheduling_alerts",
        ["status"],
    )
    op.create_index(
        "ix_scheduling_alerts_schedule_date",
        "scheduling_alerts",
        ["schedule_date"],
    )
    op.create_index(
        "ix_scheduling_alerts_created_at",
        "scheduling_alerts",
        ["created_at"],
    )

    # ── change_requests ─────────────────────────────────────────────
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
        sa.Column("details", JSONB(), nullable=True),
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
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
            "status IN ('pending','approved','denied','expired')",
            name="ck_change_requests_status",
        ),
        sa.CheckConstraint(
            "request_type IN ('delay_report','followup_job','access_issue',"
            "'nearby_pickup','resequence','crew_assist','parts_log','upgrade_quote')",
            name="ck_change_requests_request_type",
        ),
    )
    op.create_index(
        "ix_change_requests_resource_id",
        "change_requests",
        ["resource_id"],
    )
    op.create_index(
        "ix_change_requests_status",
        "change_requests",
        ["status"],
    )
    op.create_index(
        "ix_change_requests_affected_job_id",
        "change_requests",
        ["affected_job_id"],
    )

    # ── scheduling_chat_sessions ────────────────────────────────────
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
        sa.Column("messages", JSONB(), nullable=True, server_default="[]"),
        sa.Column("context", JSONB(), nullable=True, server_default="{}"),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
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
            "user_role IN ('admin','resource')",
            name="ck_scheduling_chat_sessions_user_role",
        ),
    )
    op.create_index(
        "ix_scheduling_chat_sessions_user_id",
        "scheduling_chat_sessions",
        ["user_id"],
    )
    op.create_index(
        "ix_scheduling_chat_sessions_is_active",
        "scheduling_chat_sessions",
        ["is_active"],
    )

    # ── resource_truck_inventory ────────────────────────────────────
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
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "reorder_threshold",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "last_restocked",
            sa.TIMESTAMP(timezone=True),
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
    )
    op.create_index(
        "ix_resource_truck_inventory_staff_id",
        "resource_truck_inventory",
        ["staff_id"],
    )

    # ── Extend jobs table ───────────────────────────────────────────
    op.add_column(
        "jobs",
        sa.Column("sla_deadline", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("compliance_deadline", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("job_phase", sa.Integer(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column("depends_on_job_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_jobs_depends_on_job_id",
        "jobs",
        "jobs",
        ["depends_on_job_id"],
        ["id"],
        ondelete="SET NULL",
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

    # ── Extend staff table ──────────────────────────────────────────
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
        sa.Column("service_zone_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_staff_service_zone_id",
        "staff",
        "service_zones",
        ["service_zone_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "staff",
        sa.Column("overtime_threshold_minutes", sa.Integer(), nullable=True),
    )

    # ── Extend customers table ──────────────────────────────────────
    op.add_column(
        "customers",
        sa.Column("clv_score", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("preferred_resource_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_customers_preferred_resource_id",
        "customers",
        "staff",
        ["preferred_resource_id"],
        ["id"],
        ondelete="SET NULL",
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

    # ── Extend appointments table ───────────────────────────────────
    op.add_column(
        "appointments",
        sa.Column("ai_explanation", sa.Text(), nullable=True),
    )
    op.add_column(
        "appointments",
        sa.Column("criteria_scores", JSONB(), nullable=True),
    )

    # ── Seed scheduling_criteria_config with all 30 criteria ────────
    # Hard constraints (criteria 5, 6, 7, 8, 21, 23, 30): weight=80
    # Soft constraints (all others): weight=60
    op.execute(
        sa.text(
            """
            INSERT INTO scheduling_criteria_config
                (criterion_number, criterion_name, criterion_group,
                 weight, is_hard_constraint, is_enabled, config_json)
            VALUES
                -- Geographic group (1-5)
                (1, 'Resource-to-job proximity', 'geographic',
                 60, false, true, '{}'),
                (2, 'Intra-route drive time', 'geographic',
                 60, false, true, '{}'),
                (3, 'Service zone boundaries', 'geographic',
                 60, false, true, '{}'),
                (4, 'Real-time traffic', 'geographic',
                 60, false, true, '{}'),
                (5, 'Job site access constraints', 'geographic',
                 80, true, true, '{}'),

                -- Resource group (6-10)
                (6, 'Skill/certification match', 'resource',
                 80, true, true, '{}'),
                (7, 'Equipment on truck', 'resource',
                 80, true, true, '{}'),
                (8, 'Resource availability windows', 'resource',
                 80, true, true, '{}'),
                (9, 'Workload balance', 'resource',
                 60, false, true, '{}'),
                (10, 'Performance history', 'resource',
                 60, false, true, '{}'),

                -- Customer/Job group (11-15)
                (11, 'Customer time-window preferences', 'customer_job',
                 60, false, true, '{}'),
                (12, 'Job type duration estimates', 'customer_job',
                 60, false, true, '{}'),
                (13, 'Job priority level', 'customer_job',
                 60, false, true, '{}'),
                (14, 'Customer lifetime value', 'customer_job',
                 60, false, true, '{}'),
                (15, 'Customer-resource relationship', 'customer_job',
                 60, false, true, '{}'),

                -- Capacity/Demand group (16-20)
                (16, 'Daily capacity utilization', 'capacity_demand',
                 60, false, true, '{}'),
                (17, 'Weekly demand forecast', 'capacity_demand',
                 60, false, true, '{}'),
                (18, 'Seasonal peak windows', 'capacity_demand',
                 60, false, true, '{}'),
                (19, 'Cancellation/no-show probability', 'capacity_demand',
                 60, false, true, '{}'),
                (20, 'Pipeline/backlog pressure', 'capacity_demand',
                 60, false, true, '{}'),

                -- Business Rules group (21-25)
                (21, 'Compliance deadlines', 'business_rules',
                 80, true, true, '{}'),
                (22, 'Revenue per resource-hour', 'business_rules',
                 60, false, true, '{}'),
                (23, 'Contract/SLA commitments', 'business_rules',
                 80, true, true, '{}'),
                (24, 'Overtime cost threshold', 'business_rules',
                 60, false, true, '{}'),
                (25, 'Seasonal pricing signals', 'business_rules',
                 60, false, true, '{}'),

                -- Predictive group (26-30)
                (26, 'Weather forecast impact', 'predictive',
                 60, false, true, '{}'),
                (27, 'Predicted job complexity', 'predictive',
                 60, false, true, '{}'),
                (28, 'Lead-to-job conversion timing', 'predictive',
                 60, false, true, '{}'),
                (29, 'Resource location at shift start', 'predictive',
                 60, false, true, '{}'),
                (30, 'Cross-job dependency chains', 'predictive',
                 80, true, true, '{}')
            ON CONFLICT DO NOTHING;
            """
        )
    )


def downgrade() -> None:
    """Reverse all AI scheduling changes."""

    # ── Revert appointments extensions ──────────────────────────────
    op.drop_column("appointments", "criteria_scores")
    op.drop_column("appointments", "ai_explanation")

    # ── Revert customers extensions ─────────────────────────────────
    op.drop_column("customers", "time_window_is_hard")
    op.drop_column("customers", "time_window_preference")
    op.drop_constraint(
        "fk_customers_preferred_resource_id",
        "customers",
        type_="foreignkey",
    )
    op.drop_column("customers", "preferred_resource_id")
    op.drop_column("customers", "clv_score")

    # ── Revert staff extensions ─────────────────────────────────────
    op.drop_column("staff", "overtime_threshold_minutes")
    op.drop_constraint(
        "fk_staff_service_zone_id",
        "staff",
        type_="foreignkey",
    )
    op.drop_column("staff", "service_zone_id")
    op.drop_column("staff", "avg_satisfaction")
    op.drop_column("staff", "callback_rate")
    op.drop_column("staff", "performance_score")

    # ── Revert jobs extensions ──────────────────────────────────────
    op.drop_column("jobs", "revenue_per_hour")
    op.drop_column("jobs", "predicted_complexity")
    op.drop_column("jobs", "is_outdoor")
    op.drop_constraint(
        "fk_jobs_depends_on_job_id",
        "jobs",
        type_="foreignkey",
    )
    op.drop_column("jobs", "depends_on_job_id")
    op.drop_column("jobs", "job_phase")
    op.drop_column("jobs", "compliance_deadline")
    op.drop_column("jobs", "sla_deadline")

    # ── Drop new tables (reverse order of creation) ─────────────────
    op.drop_index(
        "ix_resource_truck_inventory_staff_id",
        table_name="resource_truck_inventory",
    )
    op.drop_table("resource_truck_inventory")

    op.drop_index(
        "ix_scheduling_chat_sessions_is_active",
        table_name="scheduling_chat_sessions",
    )
    op.drop_index(
        "ix_scheduling_chat_sessions_user_id",
        table_name="scheduling_chat_sessions",
    )
    op.drop_table("scheduling_chat_sessions")

    op.drop_index(
        "ix_change_requests_affected_job_id",
        table_name="change_requests",
    )
    op.drop_index("ix_change_requests_status", table_name="change_requests")
    op.drop_index(
        "ix_change_requests_resource_id",
        table_name="change_requests",
    )
    op.drop_table("change_requests")

    op.drop_index(
        "ix_scheduling_alerts_created_at",
        table_name="scheduling_alerts",
    )
    op.drop_index(
        "ix_scheduling_alerts_schedule_date",
        table_name="scheduling_alerts",
    )
    op.drop_index(
        "ix_scheduling_alerts_status",
        table_name="scheduling_alerts",
    )
    op.drop_index(
        "ix_scheduling_alerts_severity",
        table_name="scheduling_alerts",
    )
    op.drop_index(
        "ix_scheduling_alerts_alert_type",
        table_name="scheduling_alerts",
    )
    op.drop_table("scheduling_alerts")

    op.drop_index(
        "ix_scheduling_criteria_config_criterion_group",
        table_name="scheduling_criteria_config",
    )
    op.drop_index(
        "ix_scheduling_criteria_config_criterion_number",
        table_name="scheduling_criteria_config",
    )
    op.drop_table("scheduling_criteria_config")

    op.drop_index("ix_service_zones_is_active", table_name="service_zones")
    op.drop_table("service_zones")
