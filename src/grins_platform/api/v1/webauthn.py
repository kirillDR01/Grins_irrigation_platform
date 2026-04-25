"""FastAPI endpoints for WebAuthn / Passkey authentication.

Six endpoints under ``/auth/webauthn``:

* ``POST /register/begin``      — protected; returns options + ceremony handle.
* ``POST /register/finish``     — protected; persists the new credential.
* ``POST /authenticate/begin``  — public; returns options for the browser.
* ``POST /authenticate/finish`` — public; mints the JWT cookie set on success.
* ``GET  /credentials``         — protected; lists the user's passkeys.
* ``DELETE /credentials/{id}``  — protected; revokes a passkey (IDOR-safe).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

# AsyncSession and AuthService must be importable at runtime (not under
# TYPE_CHECKING) so FastAPI can resolve `Annotated[...]` Depends parameters
# even with `from __future__ import annotations` in scope.
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth import (
    ACCESS_COOKIE_MAX_AGE,
    ACCESS_TOKEN_COOKIE,
    COOKIE_MAX_AGE,
    COOKIE_SAMESITE,
    COOKIE_SECURE,
    CSRF_TOKEN_COOKIE,
    REFRESH_TOKEN_COOKIE,
    _create_user_response,
)
from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,
    get_auth_service,
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.exceptions.auth import (
    AccountLockedError,
    InvalidCredentialsError,
    WebAuthnChallengeNotFoundError,
    WebAuthnCredentialNotFoundError,
    WebAuthnDuplicateCredentialError,
    WebAuthnVerificationError,
)
from grins_platform.repositories.staff_repository import StaffRepository
from grins_platform.repositories.webauthn_credential_repository import (
    WebAuthnCredentialRepository,
    WebAuthnUserHandleRepository,
)
from grins_platform.schemas.auth import LoginResponse
from grins_platform.schemas.webauthn import (
    AuthenticationBeginRequest,
    AuthenticationBeginResponse,
    AuthenticationFinishRequest,
    PasskeyListResponse,
    PasskeyResponse,
    RegistrationBeginResponse,
    RegistrationFinishRequest,
)
from grins_platform.services.auth_service import AuthService  # noqa: TC001
from grins_platform.services.webauthn_config import WebAuthnSettings
from grins_platform.services.webauthn_service import WebAuthnService

router = APIRouter(prefix="/webauthn", tags=["auth-webauthn"])


@lru_cache(maxsize=1)
def _get_webauthn_settings() -> WebAuthnSettings:
    return WebAuthnSettings()


async def _get_redis_client():  # type: ignore[no-untyped-def]
    """Return an async Redis client for ceremony challenge storage."""
    from redis.asyncio import Redis  # noqa: PLC0415

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(redis_url, decode_responses=False)


async def get_webauthn_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> WebAuthnService:
    """Construct a :class:`WebAuthnService` for one request."""
    redis_client = await _get_redis_client()
    return WebAuthnService(
        staff_repository=StaffRepository(session=session),
        credential_repository=WebAuthnCredentialRepository(session=session),
        user_handle_repository=WebAuthnUserHandleRepository(session=session),
        auth_service=auth_service,
        redis_client=redis_client,
        settings=_get_webauthn_settings(),
    )


def _set_login_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
) -> None:
    """Set the same three cookies as the password ``/auth/login`` endpoint."""
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=COOKIE_MAX_AGE,
        path="/",
    )
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=ACCESS_COOKIE_MAX_AGE,
        path="/",
    )
    response.set_cookie(
        key=CSRF_TOKEN_COOKIE,
        value=csrf_token,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


@router.post(
    "/register/begin",
    response_model=RegistrationBeginResponse,
    summary="Begin a passkey registration ceremony",
)
async def register_begin(
    current_user: CurrentActiveUser,
    service: Annotated[WebAuthnService, Depends(get_webauthn_service)],
) -> RegistrationBeginResponse:
    handle, options = await service.start_registration(current_user)
    return RegistrationBeginResponse(handle=handle, options=options)


@router.post(
    "/register/finish",
    response_model=PasskeyResponse,
    summary="Finish a passkey registration ceremony",
)
async def register_finish(
    request: RegistrationFinishRequest,
    current_user: CurrentActiveUser,
    service: Annotated[WebAuthnService, Depends(get_webauthn_service)],
) -> PasskeyResponse:
    try:
        cred = await service.finish_registration(
            staff=current_user,
            handle=request.handle,
            credential=request.credential,
            device_name=request.device_name,
        )
    except WebAuthnChallengeNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge expired or invalid",
        ) from e
    except WebAuthnDuplicateCredentialError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Passkey already registered",
        ) from e
    except WebAuthnVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passkey verification failed",
        ) from e
    return PasskeyResponse.model_validate(cred)


@router.post(
    "/authenticate/begin",
    response_model=AuthenticationBeginResponse,
    summary="Begin a passkey sign-in ceremony",
)
async def authenticate_begin(
    request: AuthenticationBeginRequest,
    service: Annotated[WebAuthnService, Depends(get_webauthn_service)],
) -> AuthenticationBeginResponse:
    handle, options = await service.start_authentication(username=request.username)
    return AuthenticationBeginResponse(handle=handle, options=options)


@router.post(
    "/authenticate/finish",
    response_model=LoginResponse,
    summary="Finish a passkey sign-in ceremony",
)
async def authenticate_finish(
    request: AuthenticationFinishRequest,
    response: Response,
    service: Annotated[WebAuthnService, Depends(get_webauthn_service)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    try:
        result = await service.finish_authentication(
            handle=request.handle,
            credential=request.credential,
        )
    except WebAuthnChallengeNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge expired or invalid",
        ) from e
    except WebAuthnVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        ) from e
    except AccountLockedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is locked. Please try again later.",
        ) from e
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        ) from e

    staff, access_token, refresh_token, csrf_token = result
    _set_login_cookies(
        response,
        access_token=access_token,
        refresh_token=refresh_token,
        csrf_token=csrf_token,
    )
    user_response = _create_user_response(staff, auth_service)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_COOKIE_MAX_AGE,
        user=user_response,
        csrf_token=csrf_token,
    )


@router.get(
    "/credentials",
    response_model=PasskeyListResponse,
    summary="List the current user's passkeys",
)
async def list_credentials(
    current_user: CurrentActiveUser,
    service: Annotated[WebAuthnService, Depends(get_webauthn_service)],
) -> PasskeyListResponse:
    rows = await service.list_credentials(current_user)
    return PasskeyListResponse(
        passkeys=[PasskeyResponse.model_validate(row) for row in rows],
    )


@router.delete(
    "/credentials/{credential_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a passkey owned by the current user",
)
async def revoke_credential(
    credential_uuid: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[WebAuthnService, Depends(get_webauthn_service)],
) -> Response:
    try:
        await service.revoke_credential(
            credential_row_id=credential_uuid,
            staff=current_user,
        )
    except WebAuthnCredentialNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passkey not found",
        ) from e
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["get_webauthn_service", "router"]
