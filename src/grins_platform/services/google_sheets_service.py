"""Google Sheets service for business logic operations.

Processes Google Sheet submission rows, creates leads for new clients,
and provides listing/detail access to submissions.

Validates: Requirements 3.1-3.11, 11.1, 17.2-17.4
"""

from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING
from uuid import UUID

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import LeadSituation
from grins_platform.repositories.google_sheet_submission_repository import (
    GoogleSheetSubmissionRepository,
)
from grins_platform.repositories.lead_repository import LeadRepository
from grins_platform.schemas.customer import normalize_phone
from grins_platform.schemas.google_sheet_submission import (
    GoogleSheetSubmissionResponse,
    PaginatedSubmissionResponse,
    SubmissionListParams,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.google_sheet_submission import GoogleSheetSubmission

EXPECTED_COLUMNS = 18

# The Google Sheet has 20 columns (A-T), but the internal data model uses 18.
# Column R ("Score") and S ("Email Address" duplicate) are not needed.
# Column T ("Landscape/Hardscape") maps to internal index 17.
_SHEET_COLUMNS = 20


class GoogleSheetsService(LoggerMixin):
    """Business logic for Google Sheet submission processing."""

    DOMAIN = "sheets"

    def __init__(
        self,
        submission_repo: GoogleSheetSubmissionRepository | None,
        lead_repo: LeadRepository | None,
    ) -> None:
        super().__init__()
        self.submission_repo = submission_repo
        self.lead_repo = lead_repo

    async def process_row(
        self,
        row: list[str],
        row_number: int,
        session: AsyncSession,
    ) -> GoogleSheetSubmission:
        """Process a single sheet row: store submission and optionally create lead."""
        self.log_started("process_row", row_number=row_number)

        sub_repo = GoogleSheetSubmissionRepository(session)
        lead_repo = LeadRepository(session)

        padded = pad_row(remap_sheet_row(row))

        submission = await sub_repo.create(
            sheet_row_number=row_number,
            timestamp=padded[0] or None,
            spring_startup=padded[1] or None,
            fall_blowout=padded[2] or None,
            summer_tuneup=padded[3] or None,
            repair_existing=padded[4] or None,
            new_system_install=padded[5] or None,
            addition_to_system=padded[6] or None,
            additional_services_info=padded[7] or None,
            date_work_needed_by=padded[8] or None,
            name=padded[9] or None,
            phone=padded[10] or None,
            email=padded[11] or None,
            city=padded[12] or None,
            address=padded[13] or None,
            client_type=padded[14] or None,
            property_type=padded[15] or None,
            referral_source=padded[16] or None,
            landscape_hardscape=padded[17] or None,
        )

        client_type = (padded[14].strip().lower()) if padded[14] else ""

        if client_type == "new":
            phone = self.safe_normalize_phone(padded[10])
            existing_lead = await lead_repo.get_by_phone_and_active_status(phone)

            if existing_lead:
                self.logger.info(
                    "sheets.googlesheetservice.lead_linked_existing",
                    submission_id=str(submission.id),
                    existing_lead_id=str(existing_lead.id),
                    phone=phone,
                )
                await sub_repo.update(
                    submission.id,
                    {
                        "processing_status": "lead_created",
                        "lead_id": existing_lead.id,
                    },
                )
            else:
                lead = await lead_repo.create(
                    name=self.normalize_name(padded[9]),
                    phone=phone,
                    email=padded[11].strip() or None,
                    zip_code=None,
                    situation=self.map_situation(padded).value,
                    notes=self.aggregate_notes(padded) or None,
                    source_site="google_sheets",
                )
                self.logger.info(
                    "sheets.googlesheetservice.lead_created",
                    submission_id=str(submission.id),
                    lead_id=str(lead.id),
                    phone=phone,
                )
                await sub_repo.update(
                    submission.id,
                    {"processing_status": "lead_created", "lead_id": lead.id},
                )
        else:
            self.logger.info(
                "sheets.googlesheetservice.lead_skipped",
                submission_id=str(submission.id),
                client_type=client_type or "empty",
            )
            await sub_repo.update(
                submission.id,
                {"processing_status": "skipped"},
            )

        updated = await sub_repo.get_by_id(submission.id)
        self.log_completed(
            "process_row",
            row_number=row_number,
            processing_status=updated.processing_status if updated else "unknown",
            lead_id=str(updated.lead_id) if updated and updated.lead_id else None,
        )
        return updated or submission

    async def create_lead_from_submission(
        self,
        submission_id: UUID,
        session: AsyncSession,
    ) -> GoogleSheetSubmission:
        """Manually create a lead from an existing submission."""
        self.log_started(
            "create_lead_from_submission",
            submission_id=str(submission_id),
        )

        sub_repo = GoogleSheetSubmissionRepository(session)
        lead_repo = LeadRepository(session)

        submission = await sub_repo.get_by_id(submission_id)
        if not submission:
            msg = f"Submission {submission_id} not found"
            raise ValueError(msg)

        if submission.lead_id is not None:
            msg = "Submission already has a linked lead"
            raise ValueError(msg)

        phone = self.safe_normalize_phone(submission.phone or "")
        existing_lead = await lead_repo.get_by_phone_and_active_status(phone)

        if existing_lead:
            await sub_repo.update(
                submission_id,
                {"processing_status": "lead_created", "lead_id": existing_lead.id},
            )
        else:
            row = _submission_to_row(submission)
            lead = await lead_repo.create(
                name=self.normalize_name(submission.name or ""),
                phone=phone,
                email=(submission.email or "").strip() or None,
                zip_code=None,
                situation=self.map_situation(row).value,
                notes=self.aggregate_notes(row) or None,
                source_site="google_sheets",
            )
            await sub_repo.update(
                submission_id,
                {"processing_status": "lead_created", "lead_id": lead.id},
            )

        updated = await sub_repo.get_by_id(submission_id)
        self.log_completed(
            "create_lead_from_submission",
            submission_id=str(submission_id),
            lead_id=str(updated.lead_id) if updated and updated.lead_id else None,
        )
        return updated or submission

    async def list_submissions(
        self,
        params: SubmissionListParams,
        session: AsyncSession,
    ) -> PaginatedSubmissionResponse:
        """List submissions with filtering and pagination."""
        self.log_started("list_submissions")

        sub_repo = GoogleSheetSubmissionRepository(session)
        submissions, total = await sub_repo.list_with_filters(params)
        total_pages = ceil(total / params.page_size) if total > 0 else 0

        self.log_completed("list_submissions", count=len(submissions), total=total)
        return PaginatedSubmissionResponse(
            items=[
                GoogleSheetSubmissionResponse.model_validate(s) for s in submissions
            ],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    async def get_submission(
        self,
        submission_id: UUID,
        session: AsyncSession,
    ) -> GoogleSheetSubmission | None:
        """Get a single submission by ID."""
        self.log_started("get_submission", submission_id=str(submission_id))

        sub_repo = GoogleSheetSubmissionRepository(session)
        submission = await sub_repo.get_by_id(submission_id)

        self.log_completed(
            "get_submission",
            submission_id=str(submission_id),
            found=submission is not None,
        )
        return submission

    @staticmethod
    def map_situation(row: list[str]) -> LeadSituation:
        """Map sheet service columns to LeadSituation enum."""
        if row[5].strip():  # new_system_install
            return LeadSituation.NEW_SYSTEM
        if row[6].strip():  # addition_to_system
            return LeadSituation.UPGRADE
        if row[4].strip():  # repair_existing
            return LeadSituation.REPAIR
        if any(row[i].strip() for i in (1, 2, 3)):  # seasonal
            return LeadSituation.EXPLORING
        return LeadSituation.EXPLORING

    @staticmethod
    def aggregate_notes(row: list[str]) -> str:
        """Combine sheet columns into structured notes string."""
        parts: list[str] = []
        services: list[str] = []
        for idx, label in [
            (1, "Spring Startup"),
            (2, "Fall Blowout"),
            (3, "Summer Tuneup"),
            (4, "Repair"),
            (5, "New System Install"),
            (6, "Addition to System"),
        ]:
            if row[idx].strip():
                services.append(f"{label}: {row[idx].strip()}")
        if services:
            parts.append("Services: " + "; ".join(services))

        field_map = [
            (8, "Date needed by"),
            (7, "Additional services"),
            (12, "City"),
            (13, "Address"),
            (17, "Landscape/Hardscape"),
            (16, "Referral source"),
        ]
        for idx, label in field_map:
            if row[idx].strip():
                parts.append(f"{label}: {row[idx].strip()}")

        return "\n".join(parts) if parts else ""

    @staticmethod
    def normalize_name(raw_name: str) -> str:
        """Normalize name with fallback for empty input."""
        stripped = raw_name.strip() if raw_name else ""
        return stripped if stripped else "Unknown"

    @staticmethod
    def safe_normalize_phone(raw_phone: str) -> str:
        """Normalize phone with fallback for invalid input.

        Wraps the existing normalize_phone() which raises ValueError
        on non-10-digit input. Returns "0000000000" on any failure.
        """
        if not raw_phone or not raw_phone.strip():
            return "0000000000"
        try:
            return normalize_phone(raw_phone)
        except ValueError:
            return "0000000000"


def remap_sheet_row(raw_row: list[str]) -> list[str]:
    """Remap a raw Google Sheet row (up to 20 columns A-T) to 18-column internal format.

    The sheet layout diverges from the internal model at column R:
      A-Q (indices 0-16)  → map directly to internal indices 0-16
      R   (index 17)      → "Score" — skipped
      S   (index 18)      → duplicate email — skipped
      T   (index 19)      → "Landscape/Hardscape" → internal index 17
    """
    # Pad to 20 so we can safely index
    padded = raw_row + [""] * max(0, _SHEET_COLUMNS - len(raw_row))
    result = padded[:17]  # A-Q unchanged (indices 0-16)
    result.append(padded[19] if len(padded) > 19 else "")  # T → internal 17
    return result


def pad_row(row: list[str]) -> list[str]:
    """Pad a row to exactly 18 columns, truncating extras."""
    if len(row) >= EXPECTED_COLUMNS:
        return row[:EXPECTED_COLUMNS]
    return row + [""] * (EXPECTED_COLUMNS - len(row))


def _submission_to_row(submission: GoogleSheetSubmission) -> list[str]:
    """Convert a submission model back to an 18-element row list for helpers."""
    return [
        submission.timestamp or "",
        submission.spring_startup or "",
        submission.fall_blowout or "",
        submission.summer_tuneup or "",
        submission.repair_existing or "",
        submission.new_system_install or "",
        submission.addition_to_system or "",
        submission.additional_services_info or "",
        submission.date_work_needed_by or "",
        submission.name or "",
        submission.phone or "",
        submission.email or "",
        submission.city or "",
        submission.address or "",
        submission.client_type or "",
        submission.property_type or "",
        submission.referral_source or "",
        submission.landscape_hardscape or "",
    ]
