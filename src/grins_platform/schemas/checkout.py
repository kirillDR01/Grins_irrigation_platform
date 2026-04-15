"""Checkout schemas for subscription management.

Validates: Requirements 2.1, 2.2
"""

from pydantic import BaseModel, EmailStr


class SubscriptionManageRequest(BaseModel):
    """Request body for managing a subscription via email."""

    email: EmailStr
