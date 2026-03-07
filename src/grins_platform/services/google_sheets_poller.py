"""Google Sheets background poller.

Authenticates via service account JWT (RS256), fetches new rows
on a configurable interval, and delegates processing to GoogleSheetsService.

Validates: Requirements 1.1-1.8, 5.8, 8.1-8.7, 11.3, 11.6, 16.1, 16.2, 16.4
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from jose import jwt as jose_jwt
from sqlalchemy.exc import IntegrityError

from grins_platform.log_config import get_logger
from grins_platform.repositories.google_sheet_submission_repository import (
    GoogleSheetSubmissionRepository,
)
from grins_platform.schemas.google_sheet_submission import SyncStatusResponse

if TYPE_CHECKING:
    from grins_platform.database import DatabaseManager
    from grins_platform.services.google_sheets_service import GoogleSheetsService

logger = get_logger(__name__)

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
_TOKEN_EXPIRY_BUFFER = 100  # seconds before expiry to trigger refresh


def detect_header_row(rows: list[list[str]]) -> int:
    """Return the start index for data rows, skipping header if detected.

    Checks if the first row's first cell contains "Timestamp"
    (case-insensitive, stripped). Returns 1 to skip header, 0 otherwise.
    """
    if rows and rows[0] and rows[0][0].strip().lower() == "timestamp":
        return 1
    return 0


class GoogleSheetsPoller:
    """Background poller for Google Sheets data.

    Runs as an asyncio task within the FastAPI lifespan.
    Handles JWT auth, token refresh, and periodic polling.
    """

    def __init__(
        self,
        service: GoogleSheetsService,
        db_manager: DatabaseManager,
        spreadsheet_id: str,
        sheet_name: str = "Form Responses 1",
        poll_interval: int = 60,
        key_path: str = "",
    ) -> None:
        super().__init__()
        self._service = service
        self._db_manager = db_manager
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        self._poll_interval = poll_interval
        self._key_path = key_path

        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._poll_lock = asyncio.Lock()

        # Token state
        self._access_token: str | None = None
        self._token_expiry: float = 0.0

        # Status
        self._last_sync: datetime | None = None
        self._last_error: str | None = None

        # Service account data (loaded on start)
        self._sa_email: str = ""
        self._sa_private_key: str = ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background polling task."""
        logger.info(
            "poller.start_started",
            spreadsheet_id=self._spreadsheet_id,
        )
        self._load_service_account_key()
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("poller.start_completed")

    async def stop(self) -> None:
        """Stop the background polling task gracefully."""
        logger.info("poller.stop_started")
        self._running = False
        if self._task is not None:
            _ = self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("poller.stop_completed")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @property
    def sync_status(self) -> SyncStatusResponse:
        """Return current poller status."""
        return SyncStatusResponse(
            last_sync=self._last_sync,
            is_running=self._running,
            last_error=self._last_error,
        )

    # ------------------------------------------------------------------
    # Manual trigger
    # ------------------------------------------------------------------

    async def trigger_sync(self) -> int:
        """Manual sync — acquires lock, waits if running."""
        logger.info("poller.trigger_sync_started")
        async with self._poll_lock:
            return await self._execute_poll_cycle()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _load_service_account_key(self) -> None:
        """Load service account credentials from key file."""
        with Path(self._key_path).open() as f:
            data: dict[str, Any] = json.load(f)
        self._sa_email = data["client_email"]
        self._sa_private_key = data["private_key"]
        # Never log key contents
        logger.info(
            "poller.service_account_loaded",
            email=self._sa_email,
        )

    def _build_jwt_assertion(self) -> str:
        """Build a signed JWT assertion for Google OAuth2."""
        now = int(time.time())
        claims = {
            "iss": self._sa_email,
            "scope": _SHEETS_SCOPE,
            "aud": _TOKEN_URL,
            "iat": now,
            "exp": now + 3600,
        }
        return jose_jwt.encode(
            claims,
            self._sa_private_key,
            algorithm="RS256",
        )

    async def _request_token(self, assertion: str) -> str:
        """Exchange JWT assertion for an access token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "grant_type": ("urn:ietf:params:oauth:grant-type:jwt-bearer"),
                    "assertion": assertion,
                },
            )
            _ = resp.raise_for_status()
            token_data = resp.json()
        self._access_token = token_data["access_token"]
        self._token_expiry = time.time() + token_data.get(
            "expires_in",
            3600,
        )
        # Never log token values
        logger.info("poller.token_refreshed")
        result: str = token_data["access_token"]
        return result

    async def _ensure_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        if (
            self._access_token is not None
            and time.time() < self._token_expiry - _TOKEN_EXPIRY_BUFFER
        ):
            return self._access_token
        assertion = self._build_jwt_assertion()
        return await self._request_token(assertion)

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Main polling loop — runs until stopped."""
        while self._running:
            try:
                async with self._poll_lock:
                    _ = await self._execute_poll_cycle()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._last_error = str(e)
                logger.exception(
                    "poller.poll_cycle_failed",
                    error=str(e),
                )
            try:
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break

    async def _execute_poll_cycle(self) -> int:
        """Execute one poll cycle: fetch and process new rows."""
        logger.info("poller.poll_cycle_started")
        token = await self._ensure_token()
        rows = await self._fetch_sheet_data(token)

        if not rows:
            self._last_sync = datetime.now(timezone.utc)
            self._last_error = None
            logger.info(
                "poller.poll_cycle_completed",
                new_rows=0,
            )
            return 0

        # Detect header row dynamically
        start_idx = detect_header_row(rows)

        # Get max stored row to find new rows
        max_row = 0
        async for session in self._db_manager.get_session():
            sub_repo = GoogleSheetSubmissionRepository(session)
            max_row = await sub_repo.get_max_row_number()
            break

        new_count = 0
        for i, row_data in enumerate(
            rows[start_idx:],
            start=start_idx + 1,
        ):
            # 1-based row number matching sheet position
            row_number = i + 1
            if row_number <= max_row:
                continue

            try:
                async for session in self._db_manager.get_session():
                    _ = await self._service.process_row(
                        row_data,
                        row_number,
                        session,
                    )
                    await session.commit()
                    new_count += 1
                    break
            except IntegrityError:
                logger.debug(
                    "poller.row_duplicate_skipped",
                    row_number=row_number,
                )
            except Exception as e:
                logger.exception(
                    "poller.row_processing_failed",
                    row_number=row_number,
                    error=str(e),
                )

        self._last_sync = datetime.now(timezone.utc)
        self._last_error = None
        logger.info(
            "poller.poll_cycle_completed",
            new_rows=new_count,
        )
        return new_count

    async def _fetch_sheet_data(
        self,
        token: str,
    ) -> list[list[str]]:
        """Fetch all rows from the configured sheet range."""
        url = (
            f"https://sheets.googleapis.com/v4/spreadsheets/"
            f"{self._spreadsheet_id}/values/"
            f"{self._sheet_name}!A:R"
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as c:
                resp = await c.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                    },
                )
        except httpx.TimeoutException:
            logger.exception("poller.fetch_timeout")
            self._last_error = "Google Sheets API request timed out"
            return []

        if resp.status_code == 403:
            msg = (
                "Sheet not shared with service account."
                f" Share with {self._sa_email} as Viewer."
            )
            logger.error(
                "poller.fetch_forbidden",
                message=msg,
            )
            self._last_error = msg
            return []
        if resp.status_code == 429:
            logger.warning("poller.fetch_rate_limited")
            self._last_error = "Rate limited by Google Sheets API"
            return []
        if resp.status_code >= 500:
            logger.error(
                "poller.fetch_server_error",
                status=resp.status_code,
            )
            self._last_error = f"Google API server error: {resp.status_code}"
            return []

        try:
            _ = resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.exception(
                "poller.fetch_http_error",
                status=e.response.status_code,
            )
            self._last_error = f"HTTP error: {e.response.status_code}"
            return []

        data: dict[str, Any] = resp.json()
        result: list[list[str]] = data.get("values", [])
        return result
