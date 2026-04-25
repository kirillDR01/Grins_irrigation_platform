"""
Authentication exceptions for the Grin's Irrigation Platform.

This module defines custom exception classes for authentication-related
errors including invalid credentials, account lockout, and token issues.

Validates: Requirements 14.2, 16.5-16.7
"""

from __future__ import annotations


class AuthenticationError(Exception):
    """Base exception for authentication operations.

    All authentication-related exceptions inherit from this class.
    """


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid.

    Validates: Requirement 14.2
    """

    def __init__(self, message: str = "Invalid username or password") -> None:
        """Initialize with error message.

        Args:
            message: Error message
        """
        super().__init__(message)


class AccountLockedError(AuthenticationError):
    """Raised when account is locked due to failed login attempts.

    Validates: Requirements 16.5-16.7
    """

    def __init__(self, message: str = "Account is locked") -> None:
        """Initialize with error message.

        Args:
            message: Error message with lockout details
        """
        super().__init__(message)


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired.

    Validates: Requirement 14.5
    """

    def __init__(self, message: str = "Token has expired") -> None:
        """Initialize with error message.

        Args:
            message: Error message
        """
        super().__init__(message)


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT token is invalid.

    Validates: Requirement 14.5
    """

    def __init__(self, message: str = "Invalid token") -> None:
        """Initialize with error message.

        Args:
            message: Error message
        """
        super().__init__(message)


class UserNotFoundError(AuthenticationError):
    """Raised when a user is not found during authentication.

    Validates: Requirement 18.4
    """

    def __init__(self, message: str = "User not found") -> None:
        """Initialize with error message.

        Args:
            message: Error message
        """
        super().__init__(message)


class WebAuthnVerificationError(AuthenticationError):
    """Raised when a WebAuthn ceremony's cryptographic verification fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class WebAuthnChallengeNotFoundError(AuthenticationError):
    """Raised when the Redis challenge entry for a ceremony is missing or expired."""

    def __init__(self, message: str = "Challenge expired or invalid") -> None:
        super().__init__(message)


class WebAuthnCredentialNotFoundError(AuthenticationError):
    """Raised when a passkey credential cannot be located by id."""

    def __init__(self, message: str = "Passkey not found") -> None:
        super().__init__(message)


class WebAuthnDuplicateCredentialError(AuthenticationError):
    """Raised when a registration would create a duplicate credential."""

    def __init__(self, message: str = "Passkey already registered") -> None:
        super().__init__(message)


__all__ = [
    "AccountLockedError",
    "AuthenticationError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "TokenExpiredError",
    "UserNotFoundError",
    "WebAuthnChallengeNotFoundError",
    "WebAuthnCredentialNotFoundError",
    "WebAuthnDuplicateCredentialError",
    "WebAuthnVerificationError",
]
