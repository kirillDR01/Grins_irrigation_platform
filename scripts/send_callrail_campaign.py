#!/usr/bin/env python3
"""Interim CSV blast script for sending SMS campaigns via CallRail.

Usage::

    # Dry-run (default):
    uv run python scripts/send_callrail_campaign.py \\
        recipients.csv --message "Hi {first_name}!"

    # Read template from file:
    uv run python scripts/send_callrail_campaign.py \\
        recipients.csv --template-file message.txt

    # Live mode (actually sends, throttled at ~140/hr):
    uv run python scripts/send_callrail_campaign.py \\
        recipients.csv --message "Hi {first_name}!" --confirm

CSV format: phone,first_name,last_name
(header required, first_name/last_name optional)

Requirements: 12.1-12.10
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Ensure project root is on sys.path for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from grins_platform.database import DatabaseManager  # noqa: E402
from grins_platform.schemas.ai import MessageType  # noqa: E402
from grins_platform.services.sms.consent import (  # noqa: E402
    check_sms_consent,
)
from grins_platform.services.sms.factory import (  # noqa: E402
    get_sms_provider,
)
from grins_platform.services.sms.ghost_lead import (  # noqa: E402
    create_or_get,
)
from grins_platform.services.sms.phone_normalizer import (  # noqa: E402
    PhoneNormalizationError,
    normalize_to_e164,
)
from grins_platform.services.sms.recipient import Recipient  # noqa: E402
from grins_platform.services.sms.templating import (  # noqa: E402
    render_template,
)
from grins_platform.services.sms_service import SMSService  # noqa: E402


@dataclass
class CsvRow:
    """Parsed CSV row."""

    line: int
    phone: str
    first_name: str
    last_name: str


def parse_csv(path: Path) -> tuple[list[CsvRow], list[str]]:
    """Parse CSV file returning valid rows and errors."""
    rows: list[CsvRow] = []
    errors: list[str] = []

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "phone" not in [
            h.strip().lower() for h in reader.fieldnames
        ]:
            errors.append("CSV must have a 'phone' column header")
            return rows, errors

        for i, raw in enumerate(reader, start=2):
            mapped = {k.strip().lower(): (v or "").strip() for k, v in raw.items()}
            phone = mapped.get("phone", "")
            if not phone:
                errors.append(f"Row {i}: empty phone")
                continue
            rows.append(
                CsvRow(
                    line=i,
                    phone=phone,
                    first_name=mapped.get("first_name", ""),
                    last_name=mapped.get("last_name", ""),
                ),
            )
    return rows, errors


# Throttle: ~140/hr = 1 send every ~25.7 seconds
_SEND_INTERVAL_SECS = 26.0


async def run(
    csv_path: Path,
    template: str,
    *,
    confirm: bool,
) -> None:
    """Execute the CSV blast."""
    rows, parse_errors = parse_csv(csv_path)
    if parse_errors:
        for e in parse_errors:
            print(f"[PARSE ERROR] {e}")
    if not rows:
        print("No valid rows to process.")
        return

    # Normalize phones and dedupe
    normalized: list[tuple[CsvRow, str]] = []
    seen_phones: set[str] = set()
    bad_phones: list[str] = []

    for row in rows:
        try:
            e164 = normalize_to_e164(row.phone)
        except PhoneNormalizationError:
            bad_phones.append(f"Row {row.line}: {row.phone!r}")
            continue
        if e164 in seen_phones:
            continue
        seen_phones.add(e164)
        normalized.append((row, e164))

    if bad_phones:
        print(f"\n[BAD PHONES] {len(bad_phones)} un-normalizable:")
        for bp in bad_phones:
            print(f"  {bp}")

    total = len(normalized)
    print(f"\n[SUMMARY] {total} unique recipients")

    if not confirm:
        # Dry-run: render and print each message
        print("\n--- DRY RUN (no messages sent) ---\n")
        for row, e164 in normalized:
            ctx = {
                "first_name": row.first_name,
                "last_name": row.last_name,
            }
            rendered = render_template(template, ctx)
            print(f"  TO: {e164}  MSG: {rendered}")
        print(f"\n[DRY RUN COMPLETE] {total} messages would be sent.")
        return

    # Live mode
    print("\n--- LIVE MODE ---\n")
    db = DatabaseManager()
    provider = get_sms_provider()

    sent_count = 0
    failed_count = 0
    skipped_consent = 0

    async for session in db.get_session():
        sms_svc = SMSService(session=session, provider=provider)

        for idx, (row, e164) in enumerate(normalized):
            tag = f"[{idx + 1}/{total}]"

            # Consent check
            ok = await check_sms_consent(session, e164, "marketing")
            if not ok:
                print(f"  {tag} SKIP (no consent): {e164}")
                skipped_consent += 1
                continue

            # Ghost lead for unmatched phones
            lead = await create_or_get(
                session,
                e164,
                row.first_name or None,
                row.last_name or None,
            )
            recipient = Recipient.from_adhoc(
                phone=e164,
                lead_id=lead.id,
                first_name=row.first_name or None,
                last_name=row.last_name or None,
            )

            ctx = {
                "first_name": row.first_name,
                "last_name": row.last_name,
            }
            rendered = render_template(template, ctx)

            try:
                await sms_svc.send_message(
                    recipient=recipient,
                    message=rendered,
                    message_type=MessageType.CAMPAIGN,
                    consent_type="marketing",
                    skip_formatting=True,
                )
                sent_count += 1
                print(f"  {tag} SENT: {e164}")
            except Exception as exc:
                failed_count += 1
                print(f"  {tag} FAIL: {e164} - {exc}")

            # Throttle between sends
            if idx < total - 1:
                time.sleep(_SEND_INTERVAL_SECS)

    print(
        f"\n[COMPLETE] sent={sent_count} "
        f"failed={failed_count} "
        f"skipped_consent={skipped_consent}",
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Send SMS campaign from CSV via CallRail",
    )
    parser.add_argument(
        "csv",
        type=Path,
        help="Path to CSV file",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--message",
        "-m",
        help="Message template string",
    )
    group.add_argument(
        "--template-file",
        "-f",
        type=Path,
        help="File containing message template",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually send (default is dry-run)",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"CSV file not found: {args.csv}")
        sys.exit(1)

    if args.template_file:
        if not args.template_file.exists():
            print(f"Template file not found: {args.template_file}")
            sys.exit(1)
        template = args.template_file.read_text(encoding="utf-8").strip()
    else:
        template = args.message

    if not template:
        print("Empty message template")
        sys.exit(1)

    asyncio.run(run(args.csv, template, confirm=args.confirm))


if __name__ == "__main__":
    main()
