"""SMS provider package — pluggable provider abstraction.

Public API:
    BaseSMSProvider  — Protocol for all SMS providers
    ProviderSendResult — Frozen dataclass returned by send_text()
    InboundSMS — Frozen dataclass for parsed inbound webhooks
    Recipient — Unified SMS target (customer, lead, or ad-hoc)
    SourceType — Literal type for recipient source
    NullProvider — Test provider that records sends in memory
    CallRailProvider — CallRail v3 text-messages provider
    TwilioProvider — Twilio stub provider (placeholder)
    get_sms_provider — Factory that resolves provider from SMS_PROVIDER env var
    create_or_get_ghost_lead — Find or create ghost Lead for ad-hoc phones
    normalize_to_e164 — Phone normalization to E.164
    PhoneNormalizationError — Raised on invalid phone input
    SMSRateLimitTracker — Header-based rate limit tracker for CallRail
    RateLimitState — Snapshot of rate-limit counters
    CheckResult — Result of a rate-limit check
    render_template — Safe merge-field substitution (missing keys → "")
    SafeDict — Dict that returns "" for missing keys
    check_sms_consent — Type-scoped consent check with hard-STOP precedence
    bulk_insert_attestation_consent — Bulk-insert consent records for CSV attestation
    ConsentType — Literal type for consent categories
    RecipientState — Enum of campaign recipient delivery states
    InvalidStateTransitionError — Raised on forbidden state transitions
    transition — Validate and execute a state transition
    orphan_recovery_query — Mark stuck 'sending' recipients as 'failed'
    count_segments — SMS segment counter (GSM-7 vs UCS-2)
    Encoding — Literal type for SMS encoding
    parse_csv — Parse CSV bytes into staged recipients
    match_recipients — Match staged recipients against DB customers/leads
    CsvParseResult — Result of CSV parsing
    StagedRecipient — A successfully parsed recipient
    RejectedRow — A row that could not be processed
"""

from grins_platform.services.sms.base import (
    BaseSMSProvider,
    InboundSMS,
    ProviderSendResult,
)
from grins_platform.services.sms.callrail_provider import (
    CallRailAuthError,
    CallRailError,
    CallRailProvider,
    CallRailRateLimitError,
    CallRailValidationError,
)
from grins_platform.services.sms.consent import (
    ConsentType,
    bulk_insert_attestation_consent,
    check_sms_consent,
)
from grins_platform.services.sms.csv_upload import (
    CsvParseResult,
    RejectedRow,
    StagedRecipient,
    match_recipients,
    parse_csv,
)
from grins_platform.services.sms.factory import get_sms_provider
from grins_platform.services.sms.ghost_lead import (
    create_or_get as create_or_get_ghost_lead,
)
from grins_platform.services.sms.null_provider import NullProvider
from grins_platform.services.sms.phone_normalizer import (
    PhoneNormalizationError,
    is_central_timezone,
    lookup_timezone,
    normalize_to_e164,
)
from grins_platform.services.sms.rate_limit_tracker import (
    CheckResult,
    RateLimitState,
    SMSRateLimitTracker,
)
from grins_platform.services.sms.recipient import Recipient, SourceType
from grins_platform.services.sms.segment_counter import Encoding, count_segments
from grins_platform.services.sms.state_machine import (
    InvalidStateTransitionError,
    RecipientState,
    orphan_recovery_query,
    transition,
)
from grins_platform.services.sms.templating import SafeDict, render_template
from grins_platform.services.sms.twilio_provider import TwilioProvider

__all__ = [
    "BaseSMSProvider",
    "CallRailAuthError",
    "CallRailError",
    "CallRailProvider",
    "CallRailRateLimitError",
    "CallRailValidationError",
    "CheckResult",
    "ConsentType",
    "CsvParseResult",
    "Encoding",
    "InboundSMS",
    "InvalidStateTransitionError",
    "NullProvider",
    "PhoneNormalizationError",
    "ProviderSendResult",
    "RateLimitState",
    "Recipient",
    "RecipientState",
    "RejectedRow",
    "SMSRateLimitTracker",
    "SafeDict",
    "SourceType",
    "StagedRecipient",
    "TwilioProvider",
    "bulk_insert_attestation_consent",
    "check_sms_consent",
    "count_segments",
    "create_or_get_ghost_lead",
    "get_sms_provider",
    "is_central_timezone",
    "lookup_timezone",
    "match_recipients",
    "normalize_to_e164",
    "orphan_recovery_query",
    "parse_csv",
    "render_template",
    "transition",
]
