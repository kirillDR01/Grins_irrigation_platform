"""SMS provider factory — resolves provider from SMS_PROVIDER env var.

Validates: Requirements 1.3, 1.4, 41
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from grins_platform.log_config import get_logger
from grins_platform.services.sms.callrail_provider import CallRailProvider
from grins_platform.services.sms.null_provider import NullProvider
from grins_platform.services.sms.twilio_provider import TwilioProvider

if TYPE_CHECKING:
    from grins_platform.services.sms.base import BaseSMSProvider

logger = get_logger(__name__)

# Track the last resolved provider name for switch detection
_last_provider_name: str | None = None


def get_sms_provider() -> BaseSMSProvider:
    """Return the SMS provider indicated by ``SMS_PROVIDER`` env var.

    Defaults to ``callrail`` when the variable is unset or empty.

    Raises:
        ValueError: If the provider name is not recognised.
    """
    global _last_provider_name  # noqa: PLW0603

    name = (os.environ.get("SMS_PROVIDER") or "callrail").lower().strip()

    if _last_provider_name is not None and _last_provider_name != name:
        logger.info(
            "sms.provider.switched",
            previous=_last_provider_name,
            current=name,
        )
    _last_provider_name = name

    if name == "callrail":
        return CallRailProvider(
            api_key=os.environ.get("CALLRAIL_API_KEY", ""),
            account_id=os.environ.get("CALLRAIL_ACCOUNT_ID", ""),
            company_id=os.environ.get("CALLRAIL_COMPANY_ID", ""),
            tracking_number=os.environ.get("CALLRAIL_TRACKING_NUMBER", ""),
            webhook_secret=os.environ.get("CALLRAIL_WEBHOOK_SECRET", ""),
        )

    if name == "twilio":
        return TwilioProvider()

    if name == "null":
        return NullProvider()

    msg = f"Unknown SMS provider: {name!r}. Choose from: callrail, twilio, null"
    raise ValueError(msg)


def get_resolved_provider_name() -> str | None:
    """Return the last resolved provider name, or None if never called."""
    return _last_provider_name
