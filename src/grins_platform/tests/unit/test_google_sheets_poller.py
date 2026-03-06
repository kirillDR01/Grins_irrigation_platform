"""Unit tests for GoogleSheetsPoller.

Tests lifecycle, JWT auth, token refresh, poll loop with mocked HTTP,
header row detection/skipping, and graceful config error handling.

Validates: Requirements 1.1-1.8, 5.8, 8.1-8.7, 12.1, 12.4
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from grins_platform.services.google_sheets_poller import (
    _TOKEN_EXPIRY_BUFFER,
    _TOKEN_URL,
    GoogleSheetsPoller,
)

_HTTPX_CLIENT = "grins_platform.services.google_sheets_poller.httpx.AsyncClient"
_JOSE_ENCODE = "grins_platform.services.google_sheets_poller.jose_jwt.encode"
_SUB_REPO = (
    "grins_platform.services.google_sheets_poller.GoogleSheetSubmissionRepository"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_poller(
    *,
    spreadsheet_id: str = "sheet-123",
    sheet_name: str = "Form Responses 1",
    poll_interval: int = 1,
    key_path: str = "sa.json",
) -> GoogleSheetsPoller:
    """Create a poller with mocked dependencies."""
    service = AsyncMock()
    db_manager = AsyncMock()
    return GoogleSheetsPoller(
        service=service,
        db_manager=db_manager,
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        poll_interval=poll_interval,
        key_path=key_path,
    )


_SA_KEY = {
    "client_email": "test@proj.iam.gserviceaccount.com",
    "private_key": (
        "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----\n"
    ),
}


def _mock_httpx_client(response: MagicMock) -> AsyncMock:
    """Build an async-context-manager mock for httpx.AsyncClient."""
    client = AsyncMock()
    client.get.return_value = response
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPollerLifecycle:
    """Start/stop lifecycle tests."""

    @pytest.mark.asyncio
    async def test_start_sets_running_and_creates_task(self) -> None:
        poller = _make_poller()
        with patch.object(poller, "_load_service_account_key"):
            poller._poll_loop = AsyncMock()  # type: ignore[assignment]
            await poller.start()

        assert poller._running is True
        assert poller._task is not None
        await poller.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self) -> None:
        poller = _make_poller()
        poller._running = True
        poller._task = asyncio.create_task(asyncio.sleep(999))

        await poller.stop()

        assert poller._running is False
        assert poller._task is None

    @pytest.mark.asyncio
    async def test_stop_when_not_started_is_safe(self) -> None:
        poller = _make_poller()
        await poller.stop()
        assert poller._running is False


# ---------------------------------------------------------------------------
# Service account key loading
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestServiceAccountKeyLoading:
    """Test _load_service_account_key."""

    def test_loads_email_and_key(self, tmp_path: Path) -> None:
        key_file = tmp_path / "sa.json"
        key_file.write_text(json.dumps(_SA_KEY))

        poller = _make_poller(key_path=str(key_file))
        poller._load_service_account_key()

        assert poller._sa_email == _SA_KEY["client_email"]
        assert poller._sa_private_key == _SA_KEY["private_key"]

    def test_missing_file_raises(self) -> None:
        poller = _make_poller(key_path="/nonexistent/sa.json")
        with pytest.raises(FileNotFoundError):
            poller._load_service_account_key()


# ---------------------------------------------------------------------------
# JWT assertion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJWTAssertion:
    """Test _build_jwt_assertion."""

    def test_builds_signed_jwt(self) -> None:
        poller = _make_poller()
        poller._sa_email = "svc@proj.iam.gserviceaccount.com"

        with patch(_JOSE_ENCODE) as mock_enc:
            mock_enc.return_value = "signed.jwt.token"
            result = poller._build_jwt_assertion()

        assert result == "signed.jwt.token"
        claims = mock_enc.call_args[0][0]
        assert claims["iss"] == poller._sa_email
        assert claims["aud"] == _TOKEN_URL
        assert "exp" in claims
        assert "iat" in claims
        assert mock_enc.call_args[1]["algorithm"] == "RS256"


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTokenRefresh:
    """Test _ensure_token and _request_token."""

    @pytest.mark.asyncio
    async def test_reuses_valid_token(self) -> None:
        poller = _make_poller()
        poller._access_token = "valid-tok"
        poller._token_expiry = time.time() + 3600

        assert await poller._ensure_token() == "valid-tok"

    @pytest.mark.asyncio
    async def test_refreshes_when_within_buffer(self) -> None:
        poller = _make_poller()
        poller._access_token = "old-tok"
        poller._token_expiry = time.time() + _TOKEN_EXPIRY_BUFFER - 1

        poller._build_jwt_assertion = MagicMock(return_value="jwt")  # type: ignore[assignment]
        poller._request_token = AsyncMock(return_value="new-tok")  # type: ignore[assignment]

        assert await poller._ensure_token() == "new-tok"

    @pytest.mark.asyncio
    async def test_refreshes_when_no_token(self) -> None:
        poller = _make_poller()
        poller._access_token = None

        poller._build_jwt_assertion = MagicMock(return_value="jwt")  # type: ignore[assignment]
        poller._request_token = AsyncMock(return_value="fresh")  # type: ignore[assignment]

        assert await poller._ensure_token() == "fresh"

    @pytest.mark.asyncio
    async def test_request_token_stores_token(self) -> None:
        poller = _make_poller()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "tok-abc",
            "expires_in": 3600,
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(_HTTPX_CLIENT, return_value=mock_client):
            result = await poller._request_token("jwt-assertion")

        assert result == "tok-abc"
        assert poller._access_token == "tok-abc"
        assert poller._token_expiry > time.time()


# ---------------------------------------------------------------------------
# Fetch sheet data — HTTP error handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFetchSheetData:
    """Test _fetch_sheet_data with various HTTP responses."""

    @pytest.mark.asyncio
    async def test_success_returns_rows(self) -> None:
        poller = _make_poller()
        poller._sa_email = "svc@test.iam.gserviceaccount.com"
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"values": [["a"], ["b"]]}
        resp.raise_for_status = MagicMock()

        with patch(
            _HTTPX_CLIENT,
            return_value=_mock_httpx_client(resp),
        ):
            result = await poller._fetch_sheet_data("token")

        assert result == [["a"], ["b"]]

    @pytest.mark.asyncio
    async def test_403_returns_empty(self) -> None:
        poller = _make_poller()
        poller._sa_email = "svc@test.iam.gserviceaccount.com"
        resp = MagicMock()
        resp.status_code = 403
        resp.raise_for_status = MagicMock()

        with patch(
            _HTTPX_CLIENT,
            return_value=_mock_httpx_client(resp),
        ):
            result = await poller._fetch_sheet_data("token")

        assert result == []
        assert poller._last_error is not None

    @pytest.mark.asyncio
    async def test_429_returns_empty(self) -> None:
        poller = _make_poller()
        resp = MagicMock()
        resp.status_code = 429
        resp.raise_for_status = MagicMock()

        with patch(
            _HTTPX_CLIENT,
            return_value=_mock_httpx_client(resp),
        ):
            result = await poller._fetch_sheet_data("token")

        assert result == []
        assert "rate" in (poller._last_error or "").lower()

    @pytest.mark.asyncio
    async def test_5xx_returns_empty(self) -> None:
        poller = _make_poller()
        resp = MagicMock()
        resp.status_code = 503
        resp.raise_for_status = MagicMock()

        with patch(
            _HTTPX_CLIENT,
            return_value=_mock_httpx_client(resp),
        ):
            result = await poller._fetch_sheet_data("token")

        assert result == []
        assert "503" in (poller._last_error or "")

    @pytest.mark.asyncio
    async def test_timeout_returns_empty(self) -> None:
        poller = _make_poller()
        client = AsyncMock()
        client.get.side_effect = httpx.TimeoutException("timed out")
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch(_HTTPX_CLIENT, return_value=client):
            result = await poller._fetch_sheet_data("token")

        assert result == []
        assert "timed out" in (poller._last_error or "").lower()

    @pytest.mark.asyncio
    async def test_empty_values_returns_empty_list(self) -> None:
        poller = _make_poller()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {}
        resp.raise_for_status = MagicMock()

        with patch(
            _HTTPX_CLIENT,
            return_value=_mock_httpx_client(resp),
        ):
            result = await poller._fetch_sheet_data("token")

        assert result == []


# ---------------------------------------------------------------------------
# Execute poll cycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExecutePollCycle:
    """Test _execute_poll_cycle with mocked fetch and service."""

    def _setup_db(
        self,
        poller: GoogleSheetsPoller,
        max_row: int,
    ) -> AsyncMock:
        mock_session = AsyncMock()
        mock_sub_repo = AsyncMock()
        mock_sub_repo.get_max_row_number.return_value = max_row

        async def fake_get_session():
            yield mock_session

        poller._db_manager.get_session = fake_get_session
        return mock_sub_repo

    @pytest.mark.asyncio
    async def test_no_rows_returns_zero(self) -> None:
        poller = _make_poller()
        poller._ensure_token = AsyncMock(return_value="tok")  # type: ignore[assignment]
        poller._fetch_sheet_data = AsyncMock(return_value=[])  # type: ignore[assignment]

        count = await poller._execute_poll_cycle()

        assert count == 0
        assert poller._last_sync is not None
        assert poller._last_error is None

    @pytest.mark.asyncio
    async def test_processes_new_rows(self) -> None:
        poller = _make_poller()
        poller._ensure_token = AsyncMock(return_value="tok")  # type: ignore[assignment]
        poller._fetch_sheet_data = AsyncMock(  # type: ignore[assignment]
            return_value=[["Timestamp", "c2"], ["data1", "d2"]],
        )
        mock_sub_repo = self._setup_db(poller, max_row=0)
        poller._service.process_row.return_value = MagicMock()  # type: ignore[attr-defined]

        with patch(_SUB_REPO, return_value=mock_sub_repo):
            count = await poller._execute_poll_cycle()

        assert count == 1
        poller._service.process_row.assert_called_once()  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_skips_already_processed_rows(self) -> None:
        poller = _make_poller()
        poller._ensure_token = AsyncMock(return_value="tok")  # type: ignore[assignment]
        poller._fetch_sheet_data = AsyncMock(  # type: ignore[assignment]
            return_value=[
                ["Timestamp"],
                ["old1"],
                ["old2"],
                ["new"],
            ],
        )
        mock_sub_repo = self._setup_db(poller, max_row=4)
        poller._service.process_row.return_value = MagicMock()  # type: ignore[attr-defined]

        with patch(_SUB_REPO, return_value=mock_sub_repo):
            count = await poller._execute_poll_cycle()

        # row_numbers: 3, 4, 5. max_row=4 → only row 5 processed
        assert count == 1

    @pytest.mark.asyncio
    async def test_row_error_does_not_block_others(self) -> None:
        poller = _make_poller()
        poller._ensure_token = AsyncMock(return_value="tok")  # type: ignore[assignment]
        poller._fetch_sheet_data = AsyncMock(  # type: ignore[assignment]
            return_value=[["Timestamp"], ["bad"], ["good"]],
        )
        mock_sub_repo = self._setup_db(poller, max_row=0)
        poller._service.process_row.side_effect = [  # type: ignore[attr-defined]
            RuntimeError("bad"),
            MagicMock(),
        ]

        with patch(_SUB_REPO, return_value=mock_sub_repo):
            count = await poller._execute_poll_cycle()

        assert count == 1


# ---------------------------------------------------------------------------
# Sync status & trigger
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyncStatus:
    """Test sync_status property."""

    def test_initial_status(self) -> None:
        poller = _make_poller()
        status = poller.sync_status
        assert status.is_running is False
        assert status.last_sync is None
        assert status.last_error is None

    def test_running_status(self) -> None:
        poller = _make_poller()
        poller._running = True
        assert poller.sync_status.is_running is True


@pytest.mark.unit
class TestTriggerSync:
    """Test manual trigger_sync."""

    @pytest.mark.asyncio
    async def test_trigger_calls_execute(self) -> None:
        poller = _make_poller()
        poller._execute_poll_cycle = AsyncMock(return_value=5)  # type: ignore[assignment]

        assert await poller.trigger_sync() == 5
        poller._execute_poll_cycle.assert_called_once()
