"""CSV audience upload processing.

Parses uploaded CSV files, normalizes phones, matches against existing
customers/leads, and stages the result for campaign creation.

Validates: Requirement 35
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.services.sms.phone_normalizer import (
    PhoneNormalizationError,
    normalize_to_e164,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_ROWS = 5000

# Encodings to try in order
_ENCODINGS = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]

# Accepted column names (case-insensitive) for phone
_PHONE_ALIASES = {"phone", "phone_number", "phonenumber", "mobile", "cell", "telephone"}
_FIRST_NAME_ALIASES = {"first_name", "firstname", "first", "fname"}
_LAST_NAME_ALIASES = {"last_name", "lastname", "last", "lname"}


@dataclass(frozen=True)
class RejectedRow:
    """A row that could not be processed."""

    row_number: int
    phone_raw: str
    reason: str


@dataclass(frozen=True)
class StagedRecipient:
    """A successfully parsed and normalized recipient."""

    phone_e164: str
    first_name: str | None
    last_name: str | None
    row_number: int


@dataclass
class CsvParseResult:
    """Result of parsing a CSV file."""

    upload_id: str = field(default_factory=lambda: str(uuid4()))
    recipients: list[StagedRecipient] = field(default_factory=list)
    rejected: list[RejectedRow] = field(default_factory=list)
    duplicates_collapsed: int = 0
    total_rows: int = 0


class _CsvUploadLog(LoggerMixin):
    DOMAIN = "sms"


_log = _CsvUploadLog()


def _detect_and_decode(raw: bytes) -> str:
    """Try encodings in order, return decoded text."""
    # Try each encoding; latin-1 always succeeds so this won't exhaust
    for enc in _ENCODINGS:
        result = _try_decode(raw, enc)
        if result is not None:
            return result
    msg = "Could not decode CSV with any supported encoding"
    raise ValueError(msg)


def _try_decode(raw: bytes, encoding: str) -> str | None:
    """Attempt to decode bytes with a single encoding."""
    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, ValueError):
        return None


def _find_column(headers: list[str], aliases: set[str]) -> int | None:
    """Find column index matching any alias (case-insensitive)."""
    for i, h in enumerate(headers):
        if h.strip().lower() in aliases:
            return i
    return None


def parse_csv(raw_bytes: bytes) -> CsvParseResult:
    """Parse CSV bytes into staged recipients.

    Args:
        raw_bytes: Raw file content.

    Returns:
        CsvParseResult with recipients, rejected rows, and stats.

    Raises:
        ValueError: If file exceeds size/row limits or has no phone column.
    """
    if len(raw_bytes) > MAX_FILE_SIZE:
        msg = f"File exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit"
        raise ValueError(msg)

    text = _detect_and_decode(raw_bytes)
    reader = csv.reader(io.StringIO(text))

    # Read header
    try:
        headers = next(reader)
    except StopIteration:
        msg = "CSV file is empty"
        raise ValueError(msg)  # noqa: B904

    phone_idx = _find_column(headers, _PHONE_ALIASES)
    if phone_idx is None:
        msg = "CSV must contain a 'phone' column"
        raise ValueError(msg)

    first_name_idx = _find_column(headers, _FIRST_NAME_ALIASES)
    last_name_idx = _find_column(headers, _LAST_NAME_ALIASES)

    result = CsvParseResult()
    seen_phones: dict[str, int] = {}  # e164 -> first row number

    for row_num, row in enumerate(reader, start=2):  # 1-based, header is row 1
        result.total_rows += 1

        if result.total_rows > MAX_ROWS:
            msg = f"CSV exceeds {MAX_ROWS} row limit"
            raise ValueError(msg)

        if phone_idx >= len(row):
            result.rejected.append(
                RejectedRow(row_num, "", "Row too short — missing phone column"),
            )
            continue

        phone_raw = row[phone_idx].strip()
        if not phone_raw:
            result.rejected.append(RejectedRow(row_num, phone_raw, "Empty phone"))
            continue

        try:
            e164 = normalize_to_e164(phone_raw)
        except PhoneNormalizationError as e:
            result.rejected.append(RejectedRow(row_num, phone_raw, str(e)))
            continue

        # Dedupe within file — first occurrence wins
        if e164 in seen_phones:
            result.duplicates_collapsed += 1
            continue

        seen_phones[e164] = row_num

        first_name = (
            row[first_name_idx].strip()
            if first_name_idx is not None and first_name_idx < len(row)
            else None
        )
        last_name = (
            row[last_name_idx].strip()
            if last_name_idx is not None and last_name_idx < len(row)
            else None
        )

        result.recipients.append(
            StagedRecipient(
                phone_e164=e164,
                first_name=first_name or None,
                last_name=last_name or None,
                row_number=row_num,
            ),
        )

    return result


async def match_recipients(
    session: AsyncSession,
    recipients: list[StagedRecipient],
) -> tuple[int, int, int]:
    """Match staged recipients against existing customers and leads.

    Returns:
        (matched_customers, matched_leads, will_become_ghost_leads)
    """
    from grins_platform.models.customer import Customer  # noqa: PLC0415
    from grins_platform.models.lead import Lead  # noqa: PLC0415

    phones = [r.phone_e164 for r in recipients]
    if not phones:
        return 0, 0, 0

    # Batch query customers by phone
    cust_result = await session.execute(
        select(Customer.phone).where(Customer.phone.in_(phones)),
    )
    customer_phones: set[str] = {row[0] for row in cust_result.all()}

    # Batch query leads by phone
    lead_result = await session.execute(
        select(Lead.phone).where(Lead.phone.in_(phones)),
    )
    lead_phones: set[str] = {row[0] for row in lead_result.all()}

    matched_customers = 0
    matched_leads = 0
    will_become_ghost = 0

    for r in recipients:
        if r.phone_e164 in customer_phones:
            matched_customers += 1
        elif r.phone_e164 in lead_phones:
            matched_leads += 1
        else:
            will_become_ghost += 1

    return matched_customers, matched_leads, will_become_ghost
