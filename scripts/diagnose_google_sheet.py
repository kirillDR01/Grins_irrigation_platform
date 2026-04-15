"""Diagnostic script to verify Google Sheets connection and column mapping.

Usage:
    python scripts/diagnose_google_sheet.py

Reads credentials from .env and prints:
  1. Connection status
  2. Sheet header row
  3. Column mapping (header → internal field)
  4. First data row (redacted PII)
  5. Any unmapped or missing fields
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import httpx
from dotenv import load_dotenv
from jose import jwt as jose_jwt

from grins_platform.services.google_sheets_service import (
    INTERNAL_FIELDS,
    build_column_map,
    extract_row_by_headers,
)

load_dotenv()

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


def load_service_account() -> tuple[str, str]:
    """Load service account email and private key from env."""
    key_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_JSON", "")
    key_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_PATH", "")

    if key_json:
        data = json.loads(key_json)
    elif key_path:
        with Path(key_path).open() as f:
            data = json.load(f)
    else:
        print("ERROR: No service account key configured.")
        print("  Set GOOGLE_SERVICE_ACCOUNT_KEY_PATH or GOOGLE_SERVICE_ACCOUNT_KEY_JSON in .env")
        sys.exit(1)

    return data["client_email"], data["private_key"]


async def get_token(email: str, private_key: str) -> str:
    """Get OAuth2 access token via JWT assertion."""
    now = int(time.time())
    claims = {
        "iss": email,
        "scope": _SHEETS_SCOPE,
        "aud": _TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    assertion = jose_jwt.encode(claims, private_key, algorithm="RS256")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def fetch_sheet(token: str, spreadsheet_id: str, sheet_name: str) -> list[list[str]]:
    """Fetch all data from the sheet."""
    quoted_name = f"'{sheet_name}'"
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/"
        f"{spreadsheet_id}/values/{quoted_name}"
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 403:
            print(f"ERROR: 403 Forbidden. Share the sheet with the service account.")
            sys.exit(1)
        resp.raise_for_status()
        return resp.json().get("values", [])


def redact(value: str, field: str) -> str:
    """Redact PII fields for display."""
    if field in ("phone", "email", "name", "address") and value:
        if len(value) <= 3:
            return "***"
        return value[:2] + "***" + value[-1:]
    return value


async def main() -> None:
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    sheet_name = os.getenv("GOOGLE_SHEETS_SHEET_NAME", "Form Responses 1")

    if not spreadsheet_id:
        print("ERROR: GOOGLE_SHEETS_SPREADSHEET_ID not set in .env")
        sys.exit(1)

    print("=" * 60)
    print("Google Sheets Connection Diagnostic")
    print("=" * 60)
    print(f"Spreadsheet ID: {spreadsheet_id[:8]}...{spreadsheet_id[-4:]}")
    print(f"Sheet name:     {sheet_name}")
    print()

    # 1. Auth
    print("[1] Loading service account...")
    email, private_key = load_service_account()
    print(f"    Service account: {email}")

    print("[2] Getting OAuth token...")
    token = await get_token(email, private_key)
    print("    Token obtained successfully.")

    # 2. Fetch
    print(f"[3] Fetching sheet '{sheet_name}'...")
    rows = await fetch_sheet(token, spreadsheet_id, sheet_name)
    print(f"    Fetched {len(rows)} rows.")

    if not rows:
        print("    WARNING: No data in sheet!")
        return

    # 3. Detect header
    header_idx = None
    for i in range(min(5, len(rows))):
        if rows[i] and rows[i][0].strip().lower() == "timestamp":
            header_idx = i
            break

    if header_idx is None:
        print("    WARNING: Could not find header row (no 'Timestamp' column).")
        print("    First 3 rows:")
        for i, r in enumerate(rows[:3]):
            print(f"      Row {i}: {r[:5]}...")
        return

    header_row = rows[header_idx]
    print(f"    Header row at index {header_idx} ({len(header_row)} columns)")
    print()

    # 4. Print headers
    print("[4] Sheet headers:")
    for i, h in enumerate(header_row):
        col_letter = chr(65 + i) if i < 26 else f"A{chr(65 + i - 26)}"
        print(f"    {col_letter} (idx {i:2d}): {h}")
    print()

    # 5. Build column map
    print("[5] Column mapping (header → internal field):")
    col_map = build_column_map(header_row)
    for field in INTERNAL_FIELDS:
        idx = col_map.get(field)
        if idx is not None:
            col_letter = chr(65 + idx) if idx < 26 else f"A{chr(65 + idx - 26)}"
            print(f"    {field:30s} → column {col_letter} (idx {idx}): '{header_row[idx]}'")
        else:
            print(f"    {field:30s} → NOT FOUND")
    print()

    # 6. Unmapped headers
    mapped_indices = set(col_map.values())
    unmapped = [(i, h) for i, h in enumerate(header_row) if i not in mapped_indices]
    if unmapped:
        print("[6] Unmapped headers (not used by the system):")
        for i, h in unmapped:
            col_letter = chr(65 + i) if i < 26 else f"A{chr(65 + i - 26)}"
            print(f"    {col_letter} (idx {i:2d}): {h}")
        print()

    # 7. Missing critical fields
    critical = {"name", "phone", "email", "city", "address", "client_type"}
    missing = critical - set(col_map.keys())
    if missing:
        print(f"[!] CRITICAL FIELDS MISSING: {sorted(missing)}")
        print("    These fields will get empty/default values (Unknown, 0000000000).")
        print()

    # 8. Sample data row
    if len(rows) > header_idx + 1:
        data_row = rows[header_idx + 1]
        print("[7] First data row (PII redacted):")
        extracted = extract_row_by_headers(data_row, col_map)
        for field, value in zip(INTERNAL_FIELDS, extracted):
            display = redact(value, field)
            print(f"    {field:30s}: '{display}'")
    else:
        print("[7] No data rows found after header.")

    print()
    print("=" * 60)
    print("Diagnostic complete.")


if __name__ == "__main__":
    asyncio.run(main())
