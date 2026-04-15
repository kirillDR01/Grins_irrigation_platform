#!/usr/bin/env python3
"""One-time migration: Work Requests (GoogleSheetSubmissions) → Sales Entries.

Converts existing google_sheet_submissions records into sales_entries,
mapping work request processing status to the closest SalesEntryStatus.
Preserves customer_id, property_id (via lead linkage), and notes.

Requirements: 13.3
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def get_database_url() -> str:
    """Load DATABASE_URL from environment or .env file."""
    load_dotenv()
    url = os.getenv("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(1)
    return url.replace("postgresql+asyncpg://", "postgresql://")


def map_status(processing_status: str, has_lead: bool) -> str:
    """Map work request processing_status to SalesEntryStatus value.

    Args:
        processing_status: The google_sheet_submission processing_status.
        has_lead: Whether the submission was promoted to a lead.

    Returns:
        SalesEntryStatus string value.
    """
    # Submissions that were promoted to leads and moved further along
    # are likely further in the pipeline
    if processing_status == "migrated" and has_lead:
        return "schedule_estimate"
    # Default: all work requests start at the beginning of the sales pipeline
    return "schedule_estimate"


def build_notes(row: dict[str, object]) -> str | None:
    """Build notes from work request service columns."""
    parts: list[str] = []
    if row.get("spring_startup"):
        parts.append(f"Spring Startup: {row['spring_startup']}")
    if row.get("fall_blowout"):
        parts.append(f"Fall Blowout: {row['fall_blowout']}")
    if row.get("summer_tuneup"):
        parts.append(f"Summer Tuneup: {row['summer_tuneup']}")
    if row.get("repair_existing"):
        parts.append(f"Repair: {row['repair_existing']}")
    if row.get("new_system_install"):
        parts.append(f"New Install: {row['new_system_install']}")
    if row.get("addition_to_system"):
        parts.append(f"Addition: {row['addition_to_system']}")
    if row.get("additional_services_info"):
        parts.append(f"Additional: {row['additional_services_info']}")
    if row.get("additional_info"):
        parts.append(f"Info: {row['additional_info']}")
    if row.get("work_requested"):
        parts.append(f"Work Requested: {row['work_requested']}")
    return "; ".join(parts) if parts else None


def determine_job_type(row: dict[str, object]) -> str | None:
    """Determine job type from work request service columns."""
    if row.get("new_system_install"):
        return "installation"
    if row.get("addition_to_system"):
        return "installation"
    if row.get("repair_existing"):
        return "repair"
    if row.get("spring_startup"):
        return "seasonal"
    if row.get("fall_blowout"):
        return "seasonal"
    if row.get("summer_tuneup"):
        return "seasonal"
    return None


def main() -> None:
    """Run the work requests → sales entries migration."""
    db_url = get_database_url()
    engine = create_engine(db_url)
    now = datetime.now(tz=timezone.utc).isoformat()

    migrated = 0
    skipped_no_customer = 0
    skipped_already_migrated = 0
    errors: list[str] = []

    with engine.begin() as conn:
        # Check if sales_entries table exists
        check = conn.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT 1 FROM information_schema.tables "
                "  WHERE table_name = 'sales_entries'"
                ")",
            ),
        )
        if not check.scalar():
            print("ERROR: sales_entries table does not exist. Run migrations first.")
            sys.exit(1)

        # Fetch all google_sheet_submissions with their linked lead data
        rows = (
            conn.execute(
                text(
                    """
                SELECT
                    gs.id AS submission_id,
                    gs.processing_status,
                    gs.name,
                    gs.phone,
                    gs.email,
                    gs.spring_startup,
                    gs.fall_blowout,
                    gs.summer_tuneup,
                    gs.repair_existing,
                    gs.new_system_install,
                    gs.addition_to_system,
                    gs.additional_services_info,
                    gs.additional_info,
                    gs.work_requested,
                    gs.promoted_to_lead_id,
                    gs.created_at AS submission_created_at,
                    l.customer_id AS lead_customer_id,
                    l.id AS lead_id,
                    l.moved_to AS lead_moved_to
                FROM google_sheet_submissions gs
                LEFT JOIN leads l ON l.id = gs.promoted_to_lead_id
                ORDER BY gs.created_at ASC
                """,
                ),
            )
            .mappings()
            .all()
        )

        print(f"Found {len(rows)} google_sheet_submissions to process.")

        # Check which submissions already have a sales_entry (via lead_id)
        existing_lead_ids = set()
        if rows:
            existing = conn.execute(
                text("SELECT lead_id FROM sales_entries WHERE lead_id IS NOT NULL"),
            ).all()
            existing_lead_ids = {r[0] for r in existing}

        for row in rows:
            submission_id = row["submission_id"]
            lead_id = row["lead_id"]
            lead_customer_id = row["lead_customer_id"]

            try:
                # Skip if already migrated to sales via lead
                if lead_id and lead_id in existing_lead_ids:
                    skipped_already_migrated += 1
                    continue

                # Resolve customer_id: prefer lead linkage, fall back to phone match
                customer_id = lead_customer_id
                if not customer_id and row.get("phone"):
                    phone = row["phone"].strip()
                    if phone:
                        match = conn.execute(
                            text(
                                "SELECT id FROM customers WHERE phone = :phone LIMIT 1",
                            ),
                            {"phone": phone},
                        ).first()
                        if match:
                            customer_id = match[0]

                if not customer_id and row.get("email"):
                    email = row["email"].strip().lower()
                    if email:
                        match = conn.execute(
                            text(
                                "SELECT id FROM customers "
                                "WHERE LOWER(email) = :email LIMIT 1",
                            ),
                            {"email": email},
                        ).first()
                        if match:
                            customer_id = match[0]

                if not customer_id:
                    skipped_no_customer += 1
                    continue

                # Resolve property_id from customer's primary property
                prop = conn.execute(
                    text(
                        "SELECT id FROM properties "
                        "WHERE customer_id = :cid AND is_primary = true LIMIT 1",
                    ),
                    {"cid": customer_id},
                ).first()
                property_id = prop[0] if prop else None

                notes = build_notes(dict(row))
                job_type = determine_job_type(dict(row))
                status = map_status(
                    row["processing_status"] or "imported",
                    has_lead=lead_id is not None,
                )

                conn.execute(
                    text(
                        """
                        INSERT INTO sales_entries
                            (customer_id, property_id, lead_id, job_type,
                             status, notes, created_at, updated_at)
                        VALUES
                            (:customer_id, :property_id, :lead_id, :job_type,
                             :status, :notes, :created_at, :updated_at)
                        """,
                    ),
                    {
                        "customer_id": customer_id,
                        "property_id": property_id,
                        "lead_id": lead_id,
                        "job_type": job_type,
                        "status": status,
                        "notes": notes,
                        "created_at": row.get("submission_created_at") or now,
                        "updated_at": now,
                    },
                )
                migrated += 1

            except Exception as e:
                errors.append(f"Submission {submission_id}: {e}")

    print("\n=== Migration Summary ===")
    print(f"Total submissions:      {len(rows)}")
    print(f"Migrated to sales:      {migrated}")
    print(f"Skipped (no customer):  {skipped_no_customer}")
    print(f"Skipped (already done): {skipped_already_migrated}")
    print(f"Errors:                 {len(errors)}")
    if errors:
        print("\nErrors:")
        for err in errors:
            print(f"  - {err}")

    engine.dispose()


if __name__ == "__main__":
    main()
