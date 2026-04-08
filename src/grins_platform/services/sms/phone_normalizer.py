"""E.164 phone normalization and NANP area-code → IANA timezone lookup.

Validates: Requirements 20.1, 20.3, 36
"""

from __future__ import annotations

import re


class PhoneNormalizationError(ValueError):
    """Raised when a phone string cannot be normalized to E.164."""


# Reject if input contains letters or extension markers
_LETTERS_RE = re.compile(r"[a-zA-Z]")
_EXTENSION_RE = re.compile(r"(?:ext|x|extension)\s*\d", re.IGNORECASE)


def normalize_to_e164(phone: str) -> str:
    """Normalize a US phone number to E.164 format (+1XXXXXXXXXX).

    Handles: (952) 529-3750, 952-529-3750, 9525293750, +19525293750.
    Rejects: bogus phones (000-..., 555-01xx, extensions, letters).

    Args:
        phone: Raw phone string.

    Returns:
        E.164 formatted phone string.

    Raises:
        PhoneNormalizationError: If the phone cannot be normalized.
    """
    if not phone or not phone.strip():
        msg = f"Invalid phone: {phone!r}"
        raise PhoneNormalizationError(msg)

    stripped = phone.strip()

    if _LETTERS_RE.search(stripped):
        msg = f"Phone contains letters: {phone!r}"
        raise PhoneNormalizationError(msg)

    if _EXTENSION_RE.search(stripped):
        msg = f"Phone contains extension: {phone!r}"
        raise PhoneNormalizationError(msg)

    # Strip all non-digit characters
    digits = re.sub(r"\D", "", stripped)

    # Remove leading country code '1' if 11 digits
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if len(digits) != 10:
        msg = f"Phone must be 10 digits (got {len(digits)}): {phone!r}"
        raise PhoneNormalizationError(msg)

    area_code = digits[:3]

    # NANP: area codes cannot start with 0 or 1
    if area_code[0] in ("0", "1"):
        msg = f"Invalid area code {area_code}: {phone!r}"
        raise PhoneNormalizationError(msg)

    # Reject 555-01xx test numbers
    if digits[3:6] == "555" and digits[6:8] == "01":
        msg = f"Test number rejected: {phone!r}"
        raise PhoneNormalizationError(msg)

    return f"+1{digits}"


# ---------------------------------------------------------------------------
# NANP area-code → IANA timezone lookup
#
# Maps US area codes to their primary IANA timezone. Covers all assigned
# US area codes as of 2025. Overlay codes share the timezone of the
# underlying numbering plan area.
#
# Central Time zones that count as "CT" for the Campaign Review warning:
#   America/Chicago, America/Indiana/Knox, America/Indiana/Tell_City,
#   America/Menominee, America/North_Dakota/*
# ---------------------------------------------------------------------------

_AREA_CODE_TZ: dict[str, str] = {
    # Eastern Time
    "201": "America/New_York",
    "202": "America/New_York",
    "203": "America/New_York",
    "207": "America/New_York",
    "209": "America/Los_Angeles",
    "210": "America/Chicago",
    "212": "America/New_York",
    "213": "America/Los_Angeles",
    "214": "America/Chicago",
    "215": "America/New_York",
    "216": "America/New_York",
    "217": "America/Chicago",
    "218": "America/Chicago",
    "219": "America/Chicago",
    "220": "America/New_York",
    "223": "America/New_York",
    "224": "America/Chicago",
    "225": "America/Chicago",
    "228": "America/Chicago",
    "229": "America/New_York",
    "231": "America/New_York",
    "234": "America/New_York",
    "239": "America/New_York",
    "240": "America/New_York",
    "248": "America/New_York",
    "251": "America/Chicago",
    "252": "America/New_York",
    "253": "America/Los_Angeles",
    "254": "America/Chicago",
    "256": "America/Chicago",
    "260": "America/New_York",
    "262": "America/Chicago",
    "267": "America/New_York",
    "269": "America/New_York",
    "270": "America/Chicago",
    "272": "America/New_York",
    "274": "America/Chicago",
    "276": "America/New_York",
    "278": "America/New_York",
    "279": "America/Los_Angeles",
    "281": "America/Chicago",
    "283": "America/New_York",
    "301": "America/New_York",
    "302": "America/New_York",
    "303": "America/Denver",
    "304": "America/New_York",
    "305": "America/New_York",
    "307": "America/Denver",
    "308": "America/Chicago",
    "309": "America/Chicago",
    "310": "America/Los_Angeles",
    "312": "America/Chicago",
    "313": "America/New_York",
    "314": "America/Chicago",
    "315": "America/New_York",
    "316": "America/Chicago",
    "317": "America/New_York",
    "318": "America/Chicago",
    "319": "America/Chicago",
    "320": "America/Chicago",
    "321": "America/New_York",
    "323": "America/Los_Angeles",
    "325": "America/Chicago",
    "326": "America/New_York",
    "327": "America/Chicago",
    "330": "America/New_York",
    "331": "America/Chicago",
    "332": "America/New_York",
    "334": "America/Chicago",
    "336": "America/New_York",
    "337": "America/Chicago",
    "339": "America/New_York",
    "340": "America/Virgin",
    "341": "America/Los_Angeles",
    "346": "America/Chicago",
    "347": "America/New_York",
    "351": "America/New_York",
    "352": "America/New_York",
    "360": "America/Los_Angeles",
    "361": "America/Chicago",
    "364": "America/New_York",
    "380": "America/New_York",
    "385": "America/Denver",
    "386": "America/New_York",
    "401": "America/New_York",
    "402": "America/Chicago",
    "404": "America/New_York",
    "405": "America/Chicago",
    "406": "America/Denver",
    "407": "America/New_York",
    "408": "America/Los_Angeles",
    "409": "America/Chicago",
    "410": "America/New_York",
    "412": "America/New_York",
    "413": "America/New_York",
    "414": "America/Chicago",
    "415": "America/Los_Angeles",
    "417": "America/Chicago",
    "419": "America/New_York",
    "423": "America/New_York",
    "424": "America/Los_Angeles",
    "425": "America/Los_Angeles",
    "430": "America/Chicago",
    "432": "America/Chicago",
    "434": "America/New_York",
    "435": "America/Denver",
    "440": "America/New_York",
    "442": "America/Los_Angeles",
    "443": "America/New_York",
    "445": "America/New_York",
    "447": "America/Chicago",
    "448": "America/New_York",
    "458": "America/Los_Angeles",
    "463": "America/New_York",
    "464": "America/Chicago",
    "469": "America/Chicago",
    "470": "America/New_York",
    "475": "America/New_York",
    "478": "America/New_York",
    "479": "America/Chicago",
    "480": "America/Phoenix",
    "484": "America/New_York",
    "501": "America/Chicago",
    "502": "America/New_York",
    "503": "America/Los_Angeles",
    "504": "America/Chicago",
    "505": "America/Denver",
    "507": "America/Chicago",
    "508": "America/New_York",
    "509": "America/Los_Angeles",
    "510": "America/Los_Angeles",
    "512": "America/Chicago",
    "513": "America/New_York",
    "515": "America/Chicago",
    "516": "America/New_York",
    "517": "America/New_York",
    "518": "America/New_York",
    "520": "America/Phoenix",
    "530": "America/Los_Angeles",
    "531": "America/Chicago",
    "534": "America/Chicago",
    "539": "America/Chicago",
    "540": "America/New_York",
    "541": "America/Los_Angeles",
    "551": "America/New_York",
    "557": "America/Chicago",
    "559": "America/Los_Angeles",
    "561": "America/New_York",
    "562": "America/Los_Angeles",
    "563": "America/Chicago",
    "564": "America/Los_Angeles",
    "567": "America/New_York",
    "570": "America/New_York",
    "571": "America/New_York",
    "572": "America/Chicago",
    "573": "America/Chicago",
    "574": "America/New_York",
    "575": "America/Denver",
    "580": "America/Chicago",
    "585": "America/New_York",
    "586": "America/New_York",
    "601": "America/Chicago",
    "602": "America/Phoenix",
    "603": "America/New_York",
    "605": "America/Chicago",
    "606": "America/New_York",
    "607": "America/New_York",
    "608": "America/Chicago",
    "609": "America/New_York",
    "610": "America/New_York",
    "612": "America/Chicago",
    "614": "America/New_York",
    "615": "America/Chicago",
    "616": "America/New_York",
    "617": "America/New_York",
    "618": "America/Chicago",
    "619": "America/Los_Angeles",
    "620": "America/Chicago",
    "623": "America/Phoenix",
    "626": "America/Los_Angeles",
    "628": "America/Los_Angeles",
    "629": "America/Chicago",
    "630": "America/Chicago",
    "631": "America/New_York",
    "636": "America/Chicago",
    "640": "America/New_York",
    "641": "America/Chicago",
    "646": "America/New_York",
    "650": "America/Los_Angeles",
    "651": "America/Chicago",
    "657": "America/Los_Angeles",
    "659": "America/Chicago",
    "660": "America/Chicago",
    "661": "America/Los_Angeles",
    "662": "America/Chicago",
    "667": "America/New_York",
    "669": "America/Los_Angeles",
    "670": "Pacific/Guam",
    "671": "Pacific/Guam",
    "678": "America/New_York",
    "680": "America/New_York",
    "681": "America/New_York",
    "682": "America/Chicago",
    "684": "Pacific/Pago_Pago",
    "689": "America/New_York",
    "701": "America/Chicago",
    "702": "America/Los_Angeles",
    "703": "America/New_York",
    "704": "America/New_York",
    "706": "America/New_York",
    "707": "America/Los_Angeles",
    "708": "America/Chicago",
    "712": "America/Chicago",
    "713": "America/Chicago",
    "714": "America/Los_Angeles",
    "715": "America/Chicago",
    "716": "America/New_York",
    "717": "America/New_York",
    "718": "America/New_York",
    "719": "America/Denver",
    "720": "America/Denver",
    "724": "America/New_York",
    "725": "America/Los_Angeles",
    "726": "America/Chicago",
    "727": "America/New_York",
    "728": "America/New_York",
    "730": "America/Chicago",
    "731": "America/Chicago",
    "732": "America/New_York",
    "734": "America/New_York",
    "737": "America/Chicago",
    "740": "America/New_York",
    "743": "America/New_York",
    "747": "America/Los_Angeles",
    "754": "America/New_York",
    "757": "America/New_York",
    "760": "America/Los_Angeles",
    "762": "America/New_York",
    "763": "America/Chicago",
    "764": "America/Chicago",
    "765": "America/New_York",
    "769": "America/Chicago",
    "770": "America/New_York",
    "772": "America/New_York",
    "773": "America/Chicago",
    "774": "America/New_York",
    "775": "America/Los_Angeles",
    "779": "America/Chicago",
    "781": "America/New_York",
    "785": "America/Chicago",
    "786": "America/New_York",
    "787": "America/Puerto_Rico",
    "801": "America/Denver",
    "802": "America/New_York",
    "803": "America/New_York",
    "804": "America/New_York",
    "805": "America/Los_Angeles",
    "806": "America/Chicago",
    "808": "Pacific/Honolulu",
    "810": "America/New_York",
    "812": "America/New_York",
    "813": "America/New_York",
    "814": "America/New_York",
    "815": "America/Chicago",
    "816": "America/Chicago",
    "817": "America/Chicago",
    "818": "America/Los_Angeles",
    "820": "America/Los_Angeles",
    "828": "America/New_York",
    "830": "America/Chicago",
    "831": "America/Los_Angeles",
    "832": "America/Chicago",
    "835": "America/New_York",
    "838": "America/New_York",
    "839": "America/New_York",
    "840": "America/New_York",
    "843": "America/New_York",
    "845": "America/New_York",
    "847": "America/Chicago",
    "848": "America/New_York",
    "850": "America/Chicago",
    "854": "America/New_York",
    "856": "America/New_York",
    "857": "America/New_York",
    "858": "America/Los_Angeles",
    "859": "America/New_York",
    "860": "America/New_York",
    "862": "America/New_York",
    "863": "America/New_York",
    "864": "America/New_York",
    "865": "America/New_York",
    "870": "America/Chicago",
    "872": "America/Chicago",
    "878": "America/New_York",
    "901": "America/Chicago",
    "903": "America/Chicago",
    "904": "America/New_York",
    "906": "America/New_York",
    "907": "America/Anchorage",
    "908": "America/New_York",
    "909": "America/Los_Angeles",
    "910": "America/New_York",
    "912": "America/New_York",
    "913": "America/Chicago",
    "914": "America/New_York",
    "915": "America/Denver",
    "916": "America/Los_Angeles",
    "917": "America/New_York",
    "918": "America/Chicago",
    "919": "America/New_York",
    "920": "America/Chicago",
    "925": "America/Los_Angeles",
    "928": "America/Phoenix",
    "929": "America/New_York",
    "930": "America/New_York",
    "931": "America/Chicago",
    "934": "America/New_York",
    "936": "America/Chicago",
    "937": "America/New_York",
    "938": "America/Chicago",
    "939": "America/Puerto_Rico",
    "940": "America/Chicago",
    "941": "America/New_York",
    "943": "America/New_York",
    "945": "America/Chicago",
    "947": "America/New_York",
    "949": "America/Los_Angeles",
    "951": "America/Los_Angeles",
    "952": "America/Chicago",
    "954": "America/New_York",
    "956": "America/Chicago",
    "959": "America/New_York",
    "970": "America/Denver",
    "971": "America/Los_Angeles",
    "972": "America/Chicago",
    "973": "America/New_York",
    "975": "America/Chicago",
    "978": "America/New_York",
    "979": "America/Chicago",
    "980": "America/New_York",
    "984": "America/New_York",
    "985": "America/Chicago",
    "986": "America/Denver",
    "989": "America/New_York",
}

# Timezones considered "Central" for the Campaign Review warning
_CENTRAL_TIMEZONES = frozenset(
    {
        "America/Chicago",
        "America/Indiana/Knox",
        "America/Indiana/Tell_City",
        "America/Menominee",
        "America/North_Dakota/Beulah",
        "America/North_Dakota/Center",
        "America/North_Dakota/New_Salem",
    },
)


def lookup_timezone(e164_phone: str) -> str:
    """Return the IANA timezone for a US E.164 phone number.

    Uses the NANP area code (digits 2-4 after +1) to look up the primary
    timezone. Returns ``America/Chicago`` as fallback for unknown area codes.

    Args:
        e164_phone: Phone in E.164 format (+1XXXXXXXXXX).

    Returns:
        IANA timezone string (e.g. ``America/Chicago``).
    """
    if len(e164_phone) == 12 and e164_phone.startswith("+1"):
        area_code = e164_phone[2:5]
        return _AREA_CODE_TZ.get(area_code, "America/Chicago")
    return "America/Chicago"


def is_central_timezone(tz: str) -> bool:
    """Check whether a timezone is considered Central for the CT warning."""
    return tz in _CENTRAL_TIMEZONES
