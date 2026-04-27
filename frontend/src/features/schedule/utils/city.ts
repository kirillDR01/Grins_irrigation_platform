/**
 * City normalization helpers for the Pick-Jobs facet rail.
 *
 * Multiple intake paths (Google Sheets imports, lead intake, manual entry)
 * write malformed values into ``properties.city`` (raw addresses, mixed
 * casing, embedded ``state + ZIP`` tails). These helpers run defensively
 * on the client so the City facet rail only displays canonical city names.
 *
 * Pure module — no React imports; co-located unit tests in ``city.test.ts``.
 */

// Match a state+ZIP token anywhere (e.g. "MN 55304", "TX 75001-1234").
const STATE_ZIP_ANYWHERE = /\b[A-Z]{2}\s+\d{5}(?:-\d{4})?\b/i;

// Street-suffix tokens. The trailing ``(?!\.)`` excludes "St." in "St. Paul"
// so legitimate cities with abbreviated proper-noun prefixes survive.
const STREET_SUFFIX_TOKEN_RE = new RegExp(
  '\\b(' +
    [
      'Street',
      'St',
      'Ave',
      'Avenue',
      'Dr',
      'Drive',
      'Ln',
      'Lane',
      'Rd',
      'Road',
      'Blvd',
      'Ct',
      'Court',
      'Way',
      'Ter',
      'Pl',
      'Place',
      'Pkwy',
      'Cir',
      'Circle',
      'Trl',
      'Trail',
    ].join('|') +
    ')\\b(?!\\.)',
  'i',
);

/**
 * Returns ``true`` if ``raw`` looks like a street address (digit prefix),
 * embeds a state+ZIP token, or contains a street-suffix word (e.g.
 * "Drive", "Ln") that isn't part of a proper-noun abbreviation like "St.".
 */
export function isAddressLike(raw: string): boolean {
  const trimmed = raw.trim();
  if (!trimmed) return false;
  if (/^\d/.test(trimmed)) return true;
  if (STATE_ZIP_ANYWHERE.test(trimmed)) return true;
  if (STREET_SUFFIX_TOKEN_RE.test(trimmed)) return true;
  return false;
}

/**
 * Trim, collapse whitespace, drop sentinel/empty/address-shaped values,
 * and title-case. Returns ``null`` when the input is unusable.
 *
 * Title-casing preserves embedded punctuation: "St. Paul" stays "St. Paul",
 * "OAK GROVE" becomes "Oak Grove".
 */
export function normalizeCity(raw: string | null | undefined): string | null {
  if (raw == null) return null;
  const trimmed = String(raw).trim();
  if (!trimmed) return null;

  if (isAddressLike(trimmed)) return null;

  // Collapse internal whitespace.
  const collapsed = trimmed.replace(/\s+/g, ' ');

  // Drop the sentinel "Unknown" (case-insensitive).
  if (collapsed.toLowerCase() === 'unknown') return null;

  // Title-case each whitespace-separated token while preserving punctuation.
  return collapsed.replace(
    /\w\S*/g,
    (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase(),
  );
}
