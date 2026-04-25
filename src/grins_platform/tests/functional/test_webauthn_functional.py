"""Functional tests for the WebAuthn repositories against a real Postgres.

These tests run only when ``WEBAUTHN_TEST_DATABASE_URL`` is set to a
reachable async-Postgres URL — they exercise the *real* schema (not
mocks), so they need the migration to have run first.

To run locally against the Railway dev DB:

    WEBAUTHN_TEST_DATABASE_URL='postgresql+asyncpg://...' \
        uv run pytest -m functional \
        src/grins_platform/tests/functional/test_webauthn_functional.py -v

The tests are isolated by staff_id (each test creates its own ephemeral
staff row inside a savepoint that is rolled back at teardown), so they
are safe against shared dev data.
"""

from __future__ import annotations

import os
import secrets
import uuid
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from grins_platform.repositories.webauthn_credential_repository import (
    WebAuthnCredentialRepository,
    WebAuthnUserHandleRepository,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


pytestmark = pytest.mark.functional

_DB_URL = os.environ.get("WEBAUTHN_TEST_DATABASE_URL")
_SKIP_REASON = (
    "Set WEBAUTHN_TEST_DATABASE_URL to a reachable async-postgres URL "
    "(e.g. the Railway dev shortline proxy URL) to run these tests."
)


def _require_url() -> None:
    if not _DB_URL:
        pytest.skip(_SKIP_REASON)


@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    _require_url()
    e = create_async_engine(_DB_URL or "")  # _require_url skips if None
    try:
        yield e
    finally:
        await e.dispose()


@pytest_asyncio.fixture
async def db_session(
    engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """An autocommit-style session per test.

    We don't wrap in a transaction because the dev Postgres is shared and
    the FK-cascade test needs commits to be visible. Each test creates a
    unique staff row and cleans up after itself.
    """
    SM = async_sessionmaker(engine, expire_on_commit=False)
    async with SM() as session:
        yield session


async def _create_temp_staff(session: AsyncSession) -> uuid.UUID:
    """Insert a throwaway staff row and return its id.

    Returned id is unique to the test; FK cascade tests delete it directly.
    """
    staff_id = uuid.uuid4()
    suffix = staff_id.hex[:8]
    await session.execute(
        text(
            """
            INSERT INTO staff (id, name, phone, role, is_login_enabled,
                               is_active, is_available, failed_login_attempts)
            VALUES (:id, :name, :phone, 'admin', false, true, true, 0)
            """,
        ),
        {
            "id": staff_id,
            "name": f"webauthn-test-{suffix}",
            "phone": f"5550000{suffix[:4]}",
        },
    )
    await session.commit()
    return staff_id


async def _delete_staff(session: AsyncSession, staff_id: uuid.UUID) -> None:
    await session.execute(
        text("DELETE FROM staff WHERE id = :id"),
        {"id": staff_id},
    )
    await session.commit()


@pytest.mark.asyncio
class TestUserHandleRepository:
    async def test_get_or_create_is_idempotent(
        self,
        db_session: AsyncSession,
    ) -> None:
        staff_id = await _create_temp_staff(db_session)
        try:
            repo = WebAuthnUserHandleRepository(db_session)
            handle1 = await repo.get_or_create_for_staff(staff_id)
            await db_session.commit()
            handle2 = await repo.get_or_create_for_staff(staff_id)
            assert handle1 == handle2
            assert len(handle1) == 64
        finally:
            await _delete_staff(db_session, staff_id)


@pytest.mark.asyncio
class TestCredentialRepositoryCRUD:
    async def test_full_lifecycle(self, db_session: AsyncSession) -> None:
        staff_id = await _create_temp_staff(db_session)
        try:
            repo = WebAuthnCredentialRepository(db_session)
            cred_id = secrets.token_bytes(32)

            cred = await repo.create(
                staff_id=staff_id,
                credential_id=cred_id,
                public_key=secrets.token_bytes(64),
                sign_count=0,
                transports=["internal"],
                aaguid=None,
                credential_device_type="single_device",
                backup_eligible=False,
                backup_state=False,
                device_name="Functional Test Device",
            )
            await db_session.commit()
            assert cred.id is not None

            found = await repo.find_by_credential_id(cred_id)
            assert found is not None and found.id == cred.id

            await repo.update_sign_count(cred_id, 7)
            await db_session.commit()
            refreshed = await repo.find_by_credential_id(cred_id)
            assert refreshed is not None
            assert refreshed.sign_count == 7
            assert refreshed.last_used_at is not None

            rows = await repo.list_for_staff(staff_id)
            assert any(r.id == cred.id for r in rows)

            revoked = await repo.revoke(cred.id, staff_id)
            assert revoked is True
            await db_session.commit()
            assert await repo.find_by_credential_id(cred_id) is None
        finally:
            await _delete_staff(db_session, staff_id)

    async def test_revoke_idor_safe(self, db_session: AsyncSession) -> None:
        owner = await _create_temp_staff(db_session)
        attacker = await _create_temp_staff(db_session)
        try:
            repo = WebAuthnCredentialRepository(db_session)
            cred_id = secrets.token_bytes(32)
            cred = await repo.create(
                staff_id=owner,
                credential_id=cred_id,
                public_key=secrets.token_bytes(64),
                sign_count=0,
                transports=None,
                aaguid=None,
                credential_device_type="single_device",
                backup_eligible=False,
                backup_state=False,
                device_name="IDOR Test",
            )
            await db_session.commit()

            wrongly_revoked = await repo.revoke(cred.id, attacker)
            assert wrongly_revoked is False

            still_findable = await repo.find_by_credential_id(cred_id)
            assert still_findable is not None
        finally:
            await _delete_staff(db_session, owner)
            await _delete_staff(db_session, attacker)

    async def test_duplicate_credential_id_raises_integrity_error(
        self,
        db_session: AsyncSession,
    ) -> None:
        staff_id = await _create_temp_staff(db_session)
        try:
            repo = WebAuthnCredentialRepository(db_session)
            cred_id = secrets.token_bytes(32)
            await repo.create(
                staff_id=staff_id,
                credential_id=cred_id,
                public_key=secrets.token_bytes(64),
                sign_count=0,
                transports=None,
                aaguid=None,
                credential_device_type="single_device",
                backup_eligible=False,
                backup_state=False,
                device_name="First",
            )
            await db_session.commit()

            with pytest.raises(IntegrityError):
                await repo.create(
                    staff_id=staff_id,
                    credential_id=cred_id,  # same bytes
                    public_key=secrets.token_bytes(64),
                    sign_count=0,
                    transports=None,
                    aaguid=None,
                    credential_device_type="single_device",
                    backup_eligible=False,
                    backup_state=False,
                    device_name="Duplicate",
                )
            await db_session.rollback()
        finally:
            await _delete_staff(db_session, staff_id)

    async def test_fk_cascade_deletes_credentials_with_staff(
        self,
        db_session: AsyncSession,
    ) -> None:
        staff_id = await _create_temp_staff(db_session)
        repo = WebAuthnCredentialRepository(db_session)
        cred_id = secrets.token_bytes(32)
        await repo.create(
            staff_id=staff_id,
            credential_id=cred_id,
            public_key=secrets.token_bytes(64),
            sign_count=0,
            transports=None,
            aaguid=None,
            credential_device_type="single_device",
            backup_eligible=False,
            backup_state=False,
            device_name="Cascade Test",
        )
        await db_session.commit()
        # Drop the staff — credential should cascade.
        await _delete_staff(db_session, staff_id)
        gone = await repo.find_by_credential_id(cred_id)
        assert gone is None

    async def test_check_constraint_blocks_invalid_device_type(
        self,
        db_session: AsyncSession,
    ) -> None:
        staff_id = await _create_temp_staff(db_session)
        try:
            repo = WebAuthnCredentialRepository(db_session)
            with pytest.raises(IntegrityError):
                await repo.create(
                    staff_id=staff_id,
                    credential_id=secrets.token_bytes(32),
                    public_key=secrets.token_bytes(64),
                    sign_count=0,
                    transports=None,
                    aaguid=None,
                    credential_device_type="totally-bogus",
                    backup_eligible=False,
                    backup_state=False,
                    device_name="Bad Type",
                )
            await db_session.rollback()
        finally:
            await _delete_staff(db_session, staff_id)
