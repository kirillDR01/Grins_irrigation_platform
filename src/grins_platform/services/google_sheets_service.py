"""Google Sheets service for business logic operations.

Processes Google Sheet submission rows, creates leads for all submissions
(auto-promotion), and provides listing/detail access to submissions.

Uses header-based dynamic column mapping so the integration adapts
automatically when the Google Form questions are reordered or modified.

Validates: Requirements 3.1-3.11, 11.1, 17.2-17.4, 52.1, 52.2, 52.5
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from math import ceil
from typing import TYPE_CHECKING
from uuid import UUID

from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.enums import IntakeTag, LeadSituation, LeadSourceExtended
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

logger = get_logger(__name__)

EXPECTED_COLUMNS = 18

# The Google Sheet has 20 columns (A-T), but the internal data model uses 18.
# Column R ("Score") and S ("Email Address" duplicate) are not needed.
# Column T ("Landscape/Hardscape") maps to internal index 17.
_SHEET_COLUMNS = 20

# --- Header-based dynamic column mapping ---
#
# The 18 internal fields in the order expected by process_row and the DB model.
INTERNAL_FIELDS = [
    "timestamp",
    "spring_startup",
    "fall_blowout",
    "summer_tuneup",
    "repair_existing",
    "new_system_install",
    "addition_to_system",
    "additional_services_info",
    "date_work_needed_by",
    "name",
    "phone",
    "email",
    "city",
    "address",
    "client_type",
    "property_type",
    "referral_source",
    "landscape_hardscape",
]

# Keyword patterns for matching header strings to internal field names.
# Each entry: (field_name, required_keywords, exclude_keywords).
# All required keywords must appear in the lowercased header; if any
# exclude keyword appears the pattern is skipped.
#
# IMPORTANT: build_column_map uses LAST-match-wins so that when the sheet
# has both old columns (B-Q) and new columns (T-AC) with duplicate field
# names, the newer columns (later in the header) take priority. This
# handles the transition from the old multi-checkbox form to the new
# simplified form.
_HEADER_PATTERNS: list[tuple[str, list[str], list[str]]] = [
    ("timestamp", ["timestamp"], []),
    ("spring_startup", ["spring"], []),
    ("fall_blowout", ["fall", "blow"], []),
    ("summer_tuneup", ["summer", "tune"], []),
    ("repair_existing", ["repair"], []),
    ("new_system_install", ["new", "install"], ["existing"]),
    ("new_system_install", ["new", "system"], ["existing"]),
    # "additional services" must come BEFORE "addition" — "addition" is a
    # substring of "additional" and would match first otherwise.
    ("additional_services_info", ["additional", "service"], []),
    ("additional_services_info", ["additional", "info"], ["addition to"]),
    ("addition_to_system", ["addition"], ["service", "additional service"]),
    ("date_work_needed_by", ["date", "need"], []),
    ("date_work_needed_by", ["when", "need"], []),
    ("date_work_needed_by", ["date", "completion"], []),
    ("date_work_needed_by", ["requested date"], []),
    ("landscape_hardscape", ["landscape"], []),
    ("landscape_hardscape", ["hardscape"], []),
    ("client_type", ["client", "type"], []),
    ("client_type", ["new", "existing"], ["install", "system"]),
    ("property_type", ["property", "type"], []),
    ("referral_source", ["referral"], []),
    ("referral_source", ["hear about"], []),
    ("referral_source", ["how did you"], []),
    # New-form fields (columns W, Z, AC)
    ("zip_code", ["zip"], []),
    ("work_requested", ["select", "work", "requested"], []),
    ("work_requested", ["work requested"], []),
    ("agreed_to_terms", ["agree", "terms"], []),
    ("agreed_to_terms", ["terms of service"], []),
    # Generic single-keyword patterns last
    ("name", ["name"], ["additional", "service", "sheet"]),
    ("phone", ["phone"], []),
    ("phone", ["number"], ["row", "sheet", "zone", "invoice"]),
    ("email", ["email"], []),
    ("city", ["city"], []),
    ("address", ["address"], ["email"]),
]

# Extra fields extracted from the raw row via col_map but not stored in
# the 18-column submission model. Used for lead creation and notes.
EXTRA_FIELDS = ["zip_code", "work_requested", "agreed_to_terms"]


def compute_row_hash(raw_row: list[str]) -> str:
    """Compute a deterministic SHA-256 hash of a raw sheet row.

    Takes the raw sheet row (before any mapping), joins all cell values
    with a pipe delimiter, and returns the hex digest. Same row content
    produces the same hash regardless of sheet position.
    """
    joined = "|".join(raw_row)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _match_header(header: str) -> str | None:
    """Match a single header string to an internal field name.

    Returns the field name or None if no pattern matches.
    """
    h = header.strip().lower()
    if not h:
        return None

    for field, required, exclude in _HEADER_PATTERNS:
        if any(kw in h for kw in exclude):
            continue
        if all(kw in h for kw in required):
            return field

    return None


def build_column_map(headers: list[str]) -> dict[str, int]:
    """Build a mapping from internal field names to sheet column indices.

    Uses LAST-match-wins so that when the sheet has both old (B-Q) and
    new (T-AC) columns with the same field names, the newer columns
    (which appear later) take priority. This handles the form transition.
    """
    col_map: dict[str, int] = {}
    for idx, header in enumerate(headers):
        field = _match_header(header)
        if field:
            col_map[field] = idx  # last occurrence wins
    return col_map


def extract_row_by_headers(
    raw_row: list[str],
    col_map: dict[str, int],
) -> list[str]:
    """Extract an 18-element internal row from a raw sheet row using a column map.

    Fields not found in col_map get empty strings.
    """
    result: list[str] = []
    for field in INTERNAL_FIELDS:
        idx = col_map.get(field)
        if idx is not None and idx < len(raw_row):
            result.append(raw_row[idx])
        else:
            result.append("")
    return result


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
        col_map: dict[str, int] | None = None,
        content_hash: str | None = None,
    ) -> GoogleSheetSubmission:
        """Process a sheet row: store submission and create lead.

        All work request submissions are auto-promoted to Leads regardless of
        client type. The submission is updated with promoted_to_lead_id and
        promoted_at for tracking.

        Args:
            col_map: Optional header-based column mapping. When provided, fields
                are extracted by column name rather than hardcoded position. This
                makes the integration resilient to Google Form column changes.

        Validates: Requirements 52.1, 52.2, 52.5
        """
        self.log_started("process_row", row_number=row_number)

        sub_repo = GoogleSheetSubmissionRepository(session)
        lead_repo = LeadRepository(session)

        if col_map:
            padded = pad_row(extract_row_by_headers(row, col_map))
        else:
            padded = pad_row(remap_sheet_row(row))

        # Extract extra fields from the raw row that aren't in the 18-column
        # submission model (zip_code, work_requested, agreed_to_terms).
        extras = _extract_extras(row, col_map)

        submission = await sub_repo.create(
            sheet_row_number=row_number,
            content_hash=content_hash,
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
            # New form fields (stored in DB for visibility in admin)
            zip_code=extras.get("zip_code") or None,
            work_requested=extras.get("work_requested") or None,
            agreed_to_terms=extras.get("agreed_to_terms") or None,
        )

        client_type = (padded[14].strip().lower()) if padded[14] else ""
        is_new = client_type == "new"
        source_detail = (
            "New client work request" if is_new else "Existing client work request"
        )

        phone = self.safe_normalize_phone(padded[10])
        existing_lead = await lead_repo.get_by_phone_and_active_status(phone)

        # Determine situation from old checkbox columns OR new single-select
        work_requested = extras.get("work_requested", "")
        situation = self.map_situation(padded, work_requested=work_requested)

        # Build notes including extra fields
        notes = self.aggregate_notes(padded, extras=extras) or None

        # Use zip_code from form if available
        zip_code = extras.get("zip_code") or None

        # Determine if they agreed to terms of service
        agreed = extras.get("agreed_to_terms", "").strip().lower() in (
            "yes",
            "true",
            "1",
        )

        if existing_lead:
            lead_id = existing_lead.id
            self.logger.info(
                "sheets.googlesheetservice.lead_linked_existing",
                submission_id=str(submission.id),
                existing_lead_id=str(existing_lead.id),
                phone=phone,
            )
        else:
            lead = await lead_repo.create(
                name=self.normalize_name(padded[9]),
                phone=phone,
                email=padded[11].strip() or None,
                zip_code=zip_code,
                address=padded[13].strip() or None,
                city=padded[12].strip() or None,
                situation=situation.value,
                notes=notes,
                source_site="google_sheets",
                lead_source=LeadSourceExtended.GOOGLE_FORM.value,
                source_detail=source_detail,
                intake_tag=IntakeTag.SCHEDULE.value,
                terms_accepted=agreed,
                property_type=padded[15].strip() or None,
                customer_type=padded[14].strip() or None,
            )
            lead_id = lead.id
            self.logger.info(
                "sheets.googlesheetservice.lead_created",
                submission_id=str(submission.id),
                lead_id=str(lead.id),
                phone=phone,
            )

        await sub_repo.update(
            submission.id,
            {
                "processing_status": "lead_created",
                "lead_id": lead_id,
                "promoted_to_lead_id": lead_id,
                "promoted_at": datetime.now(tz=timezone.utc),
            },
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
        """Manually create a lead from an existing submission.

        Also sets promoted_to_lead_id and promoted_at for tracking.

        Validates: Requirements 52.1, 52.2, 52.5
        """
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

        client_type = (
            (submission.client_type.strip().lower()) if submission.client_type else ""
        )
        is_new = client_type == "new"
        source_detail = (
            "New client work request" if is_new else "Existing client work request"
        )

        phone = self.safe_normalize_phone(submission.phone or "")
        existing_lead = await lead_repo.get_by_phone_and_active_status(phone)

        if existing_lead:
            lead_id = existing_lead.id
        else:
            row = _submission_to_row(submission)
            # Build extras from stored submission fields
            sub_extras: dict[str, str] = {}
            if submission.work_requested:
                sub_extras["work_requested"] = submission.work_requested
            if submission.zip_code:
                sub_extras["zip_code"] = submission.zip_code
            if submission.agreed_to_terms:
                sub_extras["agreed_to_terms"] = submission.agreed_to_terms

            work_req = sub_extras.get("work_requested", "")
            agreed = sub_extras.get("agreed_to_terms", "").strip().lower() in (
                "yes",
                "true",
                "1",
            )

            lead = await lead_repo.create(
                name=self.normalize_name(submission.name or ""),
                phone=phone,
                email=(submission.email or "").strip() or None,
                zip_code=sub_extras.get("zip_code") or None,
                address=(submission.address or "").strip() or None,
                city=(submission.city or "").strip() or None,
                situation=self.map_situation(row, work_requested=work_req).value,
                notes=self.aggregate_notes(row, extras=sub_extras) or None,
                source_site="google_sheets",
                lead_source=LeadSourceExtended.GOOGLE_FORM.value,
                source_detail=source_detail,
                intake_tag=IntakeTag.SCHEDULE.value,
                terms_accepted=agreed,
                property_type=(submission.property_type or "").strip() or None,
                customer_type=(submission.client_type or "").strip() or None,
            )
            lead_id = lead.id

        await sub_repo.update(
            submission_id,
            {
                "processing_status": "lead_created",
                "lead_id": lead_id,
                "promoted_to_lead_id": lead_id,
                "promoted_at": datetime.now(tz=timezone.utc),
            },
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
    def map_situation(  # noqa: PLR0911
        row: list[str],
        work_requested: str = "",
    ) -> LeadSituation:
        """Map service columns to LeadSituation enum.

        Checks both the old checkbox columns (B-G, indices 1-6) and the new
        single-select ``work_requested`` text. Old checkboxes take priority
        when present; otherwise the work_requested text is checked for keywords.
        """
        # Old form: individual checkbox columns
        if row[5].strip():  # new_system_install
            return LeadSituation.NEW_SYSTEM
        if row[6].strip():  # addition_to_system
            return LeadSituation.UPGRADE
        if row[4].strip():  # repair_existing
            return LeadSituation.REPAIR
        if any(row[i].strip() for i in (1, 2, 3)):  # seasonal
            return LeadSituation.EXPLORING

        # New form: single "Please Select Work Requested" text
        if work_requested:
            wr = work_requested.lower()
            if "new" in wr and ("install" in wr or "system" in wr):
                return LeadSituation.NEW_SYSTEM
            if "addition" in wr:
                return LeadSituation.UPGRADE
            if "repair" in wr:
                return LeadSituation.REPAIR
            if any(kw in wr for kw in ("spring", "blow", "winteriz", "tune")):
                return LeadSituation.EXPLORING
            # Any work_requested value implies at least exploring
            return LeadSituation.EXPLORING

        return LeadSituation.EXPLORING

    @staticmethod
    def aggregate_notes(
        row: list[str],
        extras: dict[str, str] | None = None,
    ) -> str:
        """Combine sheet columns into structured notes string.

        Includes both old-form service checkboxes and new-form extra fields
        (work_requested, zip_code, agreed_to_terms).
        """
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

        # Extra fields from new form columns (not in 18-column model)
        if extras:
            extra_map = [
                ("work_requested", "Work requested"),
                ("zip_code", "Zip code"),
                ("agreed_to_terms", "Agreed to terms"),
            ]
            for key, label in extra_map:
                val = extras.get(key, "")
                if val:
                    parts.append(f"{label}: {val}")

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


def _extract_extras(
    raw_row: list[str],
    col_map: dict[str, int] | None,
) -> dict[str, str]:
    """Extract extra fields (not in 18-column model) from the raw row.

    These fields exist in the new form columns but don't have dedicated
    columns in the google_sheet_submissions DB table. They're used for
    lead creation and notes aggregation.
    """
    extras: dict[str, str] = {}
    if not col_map:
        return extras
    for field in EXTRA_FIELDS:
        idx = col_map.get(field)
        if idx is not None and idx < len(raw_row):
            val = raw_row[idx].strip()
            if val:
                extras[field] = val
    return extras


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
