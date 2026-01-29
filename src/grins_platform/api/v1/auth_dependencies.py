"""
Authentication dependencies for FastAPI endpoints.

This module provides FastAPI dependencies for authentication and
role-based access control (RBAC).

Validates: Requirements 17.1-17.12, 20.1-20.6
"""

from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.exceptions.auth import (
    InvalidTokenError,
    TokenExpiredError,
    UserNotFoundError,
)
from grins_platform.models.enums import UserRole
from grins_platform.models.staff import Staff
from grins_platform.repositories.staff_repository import StaffRepository
from grins_platform.services.auth_service import AuthService

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    """Get AuthService dependency.

    Args:
        session: Database session from dependency injection

    Returns:
        AuthService instance
    """
    repository = StaffRepository(session=session)
    return AuthService(repository=repository)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> Staff:
    """Get the current authenticated user.

    This dependency extracts the JWT token from the Authorization header,
    validates it, and returns the associated user.

    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials
        auth_service: AuthService instance

    Returns:
        Authenticated Staff member

    Raises:
        HTTPException: 401 if not authenticated or token invalid

    Validates: Requirements 17.1-17.12, 20.1-20.6
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await auth_service.get_current_user(credentials.credentials)
    except TokenExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except (InvalidTokenError, UserNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    else:
        # Store user in request state for access in route handlers
        request.state.current_user = user
        return user


async def get_current_active_user(
    current_user: Annotated[Staff, Depends(get_current_user)],
) -> Staff:
    """Get the current active user.

    This dependency ensures the user is both authenticated and active.

    Args:
        current_user: Current authenticated user

    Returns:
        Active Staff member

    Raises:
        HTTPException: 403 if user is not active

    Validates: Requirements 17.1-17.12, 20.1-20.6
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return current_user


def _get_user_role(staff: Staff) -> UserRole:
    """Map staff role to user role.

    Args:
        staff: Staff member

    Returns:
        Corresponding UserRole
    """
    role_mapping = {
        "admin": UserRole.ADMIN,
        "sales": UserRole.MANAGER,
        "tech": UserRole.TECH,
    }
    return role_mapping.get(staff.role, UserRole.TECH)


async def require_admin(
    current_user: Annotated[Staff, Depends(get_current_active_user)],
) -> Staff:
    """Require admin role for access.

    Args:
        current_user: Current active user

    Returns:
        Staff member with admin role

    Raises:
        HTTPException: 403 if user is not admin

    Validates: Requirements 17.1-17.12
    """
    user_role = _get_user_role(current_user)
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_manager_or_admin(
    current_user: Annotated[Staff, Depends(get_current_active_user)],
) -> Staff:
    """Require manager or admin role for access.

    Args:
        current_user: Current active user

    Returns:
        Staff member with manager or admin role

    Raises:
        HTTPException: 403 if user is not manager or admin

    Validates: Requirements 17.5-17.6
    """
    user_role = _get_user_role(current_user)
    if user_role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or admin access required",
        )
    return current_user


def require_roles(*allowed_roles: UserRole) -> Callable[..., Any]:
    """Create a decorator that requires specific roles.

    This decorator can be used to protect route handlers by requiring
    the authenticated user to have one of the specified roles.

    Args:
        *allowed_roles: Roles that are allowed to access the endpoint

    Returns:
        Decorator function

    Validates: Requirements 17.1-17.12

    Example:
        @router.get("/admin-only")
        @require_roles(UserRole.ADMIN)
        async def admin_endpoint(
            current_user: Staff = Depends(get_current_active_user)
        ):
            return {"message": "Admin access granted"}
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> object:
            # Get current_user from kwargs (injected by FastAPI)
            current_user: Staff | None = kwargs.get("current_user")
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                )

            user_role = _get_user_role(current_user)
            if user_role not in allowed_roles:
                roles_str = [r.value for r in allowed_roles]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {roles_str}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[Staff, Depends(get_current_user)]
CurrentActiveUser = Annotated[Staff, Depends(get_current_active_user)]
AdminUser = Annotated[Staff, Depends(require_admin)]
ManagerOrAdminUser = Annotated[Staff, Depends(require_manager_or_admin)]


__all__ = [
    "AdminUser",
    "CurrentActiveUser",
    "CurrentUser",
    "ManagerOrAdminUser",
    "get_auth_service",
    "get_current_active_user",
    "get_current_user",
    "require_admin",
    "require_manager_or_admin",
    "require_roles",
]
