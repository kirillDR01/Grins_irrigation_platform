"""Zip code to city/state lookup utility.

Provides a lightweight mapping of US zip codes to city and state.
Uses a curated subset of Colorado zip codes (primary service area)
with fallback for unknown zips.

Validates: Requirement 12.5
"""

from __future__ import annotations

import re

# Colorado service area zip codes — primary market for Grins Irrigation
# Format: zip_code -> (city, state)
_ZIP_MAP: dict[str, tuple[str, str]] = {
    # Denver Metro
    "80002": ("Arvada", "CO"),
    "80003": ("Arvada", "CO"),
    "80004": ("Arvada", "CO"),
    "80005": ("Arvada", "CO"),
    "80007": ("Arvada", "CO"),
    "80010": ("Aurora", "CO"),
    "80011": ("Aurora", "CO"),
    "80012": ("Aurora", "CO"),
    "80013": ("Aurora", "CO"),
    "80014": ("Aurora", "CO"),
    "80015": ("Aurora", "CO"),
    "80016": ("Aurora", "CO"),
    "80017": ("Aurora", "CO"),
    "80018": ("Aurora", "CO"),
    "80019": ("Aurora", "CO"),
    "80020": ("Broomfield", "CO"),
    "80021": ("Broomfield", "CO"),
    "80022": ("Commerce City", "CO"),
    "80023": ("Broomfield", "CO"),
    "80030": ("Westminster", "CO"),
    "80031": ("Westminster", "CO"),
    "80033": ("Wheat Ridge", "CO"),
    "80034": ("Wheat Ridge", "CO"),
    "80101": ("Agate", "CO"),
    "80102": ("Bennett", "CO"),
    "80104": ("Castle Rock", "CO"),
    "80108": ("Castle Rock", "CO"),
    "80109": ("Castle Rock", "CO"),
    "80110": ("Englewood", "CO"),
    "80111": ("Englewood", "CO"),
    "80112": ("Englewood", "CO"),
    "80113": ("Englewood", "CO"),
    "80120": ("Littleton", "CO"),
    "80121": ("Littleton", "CO"),
    "80122": ("Littleton", "CO"),
    "80123": ("Littleton", "CO"),
    "80124": ("Lone Tree", "CO"),
    "80125": ("Littleton", "CO"),
    "80126": ("Highlands Ranch", "CO"),
    "80127": ("Littleton", "CO"),
    "80128": ("Littleton", "CO"),
    "80129": ("Highlands Ranch", "CO"),
    "80130": ("Highlands Ranch", "CO"),
    "80131": ("Louviers", "CO"),
    "80134": ("Parker", "CO"),
    "80138": ("Parker", "CO"),
}

# Denver proper
for _z in [
    "80201",
    "80202",
    "80203",
    "80204",
    "80205",
    "80206",
    "80207",
    "80208",
    "80209",
    "80210",
    "80211",
    "80212",
    "80214",
    "80215",
    "80216",
    "80217",
    "80218",
    "80219",
    "80220",
    "80221",
    "80222",
    "80223",
    "80224",
    "80226",
    "80227",
    "80228",
    "80229",
    "80230",
    "80231",
    "80232",
    "80233",
    "80234",
    "80235",
    "80236",
    "80237",
    "80238",
    "80239",
    "80241",
    "80246",
    "80247",
    "80249",
]:
    _ZIP_MAP[_z] = ("Denver", "CO")

# Boulder area
for _z in ["80301", "80302", "80303", "80304", "80305", "80310"]:
    _ZIP_MAP[_z] = ("Boulder", "CO")

# Longmont
for _z in ["80501", "80503", "80504"]:
    _ZIP_MAP[_z] = ("Longmont", "CO")

# Fort Collins
for _z in ["80521", "80524", "80525", "80526", "80528"]:
    _ZIP_MAP[_z] = ("Fort Collins", "CO")

# Loveland
for _z in ["80537", "80538"]:
    _ZIP_MAP[_z] = ("Loveland", "CO")

# Colorado Springs
for _z in [
    "80901",
    "80902",
    "80903",
    "80904",
    "80905",
    "80906",
    "80907",
    "80908",
    "80909",
    "80910",
    "80911",
    "80915",
    "80916",
    "80917",
    "80918",
    "80919",
    "80920",
    "80921",
    "80922",
    "80923",
    "80924",
    "80925",
    "80927",
    "80929",
    "80938",
    "80939",
]:
    _ZIP_MAP[_z] = ("Colorado Springs", "CO")

# Additional cities
_ZIP_MAP.update(
    {
        "80401": ("Golden", "CO"),
        "80403": ("Golden", "CO"),
        "80465": ("Morrison", "CO"),
        "80439": ("Evergreen", "CO"),
        "80433": ("Conifer", "CO"),
        "80470": ("Pine", "CO"),
        "80516": ("Erie", "CO"),
        "80027": ("Louisville", "CO"),
        "80026": ("Lafayette", "CO"),
        "80513": ("Berthoud", "CO"),
        "80550": ("Windsor", "CO"),
        "80534": ("Johnstown", "CO"),
        "80543": ("Milliken", "CO"),
        "80530": ("Frederick", "CO"),
        "80514": ("Dacono", "CO"),
        "80520": ("Firestone", "CO"),
        "80601": ("Brighton", "CO"),
        "80602": ("Brighton", "CO"),
        "80603": ("Brighton", "CO"),
        "80640": ("Henderson", "CO"),
        "80642": ("Hudson", "CO"),
        "80621": ("Fort Lupton", "CO"),
        "80631": ("Greeley", "CO"),
        "80634": ("Greeley", "CO"),
    },
)


def extract_zip_from_address(address: str) -> str | None:
    """Extract a 5-digit zip code from a full address string.

    Finds the last 5-digit number in the string, which is typically
    the zip code in a US address format.

    Args:
        address: Full address string (e.g. "1234 Elm St, Denver, CO 80209").

    Returns:
        The extracted 5-digit zip code, or None if not found.
    """
    matches = re.findall(r"\b(\d{5})\b", address)
    return matches[-1] if matches else None


def lookup_zip(zip_code: str) -> tuple[str | None, str | None]:
    """Look up city and state from a US zip code.

    Args:
        zip_code: 5-digit US zip code string.

    Returns:
        Tuple of (city, state) or (None, None) if not found.

    Validates: Requirement 12.5
    """
    normalized = zip_code.strip()[:5]
    result = _ZIP_MAP.get(normalized)
    if result is not None:
        return result
    return (None, None)
