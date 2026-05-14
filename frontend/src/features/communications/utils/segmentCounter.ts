/**
 * SMS segment counter — GSM-7 vs UCS-2 detection and segment calculation.
 *
 * Mirrors backend `services/sms/segment_counter.py` exactly.
 * Validates: Requirements 15.9, 34, 43
 */

// --- Constants ---

export const SENDER_PREFIX = "Grin's Irrigation: ";
export const STOP_FOOTER = ' Reply STOP to opt out.';
export const ALLOWED_MERGE_FIELDS = ['first_name', 'last_name', 'next_appointment_date'] as const;

// --- GSM-7 character sets ---

const GSM7_BASIC = new Set(
  '@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ ÆæßÉ' +
  ' !"#¤%&\'()*+,-./0123456789:;<=>?' +
  '¡ABCDEFGHIJKLMNOPQRSTUVWXYZ' +
  'ÄÖÑܧ¿abcdefghijklmnopqrstuvwxyz' +
  'äöñüà',
);

const GSM7_EXTENSION = new Set('^{}\\[~]|€');

export type Encoding = 'GSM-7' | 'UCS-2';

function detectEncoding(text: string): Encoding {
  for (const ch of text) {
    if (!GSM7_BASIC.has(ch) && !GSM7_EXTENSION.has(ch)) return 'UCS-2';
  }
  return 'GSM-7';
}

function gsm7CharCount(text: string): number {
  let count = 0;
  for (const ch of text) {
    count += GSM7_EXTENSION.has(ch) ? 2 : 1;
  }
  return count;
}

/** Count SMS segments — matches backend `segment_counter.count_segments`. */
export function countSegments(
  text: string,
  options?: { includePrefix?: boolean; includeFooter?: boolean },
): { encoding: Encoding; segments: number; chars: number } {
  const prefix = (options?.includePrefix ?? true) ? SENDER_PREFIX : '';
  const footer = (options?.includeFooter ?? true) ? STOP_FOOTER : '';
  const full = `${prefix}${text}${footer}`;

  const encoding = detectEncoding(full);

  let chars: number;
  let segments: number;
  if (encoding === 'GSM-7') {
    chars = gsm7CharCount(full);
    segments = chars <= 160 ? 1 : Math.ceil(chars / 153);
  } else {
    chars = full.length;
    segments = chars <= 70 ? 1 : Math.ceil(chars / 67);
  }

  return { encoding, segments, chars };
}

// --- Merge-field helpers ---

const MERGE_FIELD_RE = /\{(\w+)\}/g;

export function findInvalidMergeFields(text: string): string[] {
  const invalid: string[] = [];
  let match: RegExpExecArray | null;
  const re = new RegExp(MERGE_FIELD_RE.source, MERGE_FIELD_RE.flags);
  while ((match = re.exec(text)) !== null) {
    if (!(ALLOWED_MERGE_FIELDS as readonly string[]).includes(match[1])) {
      invalid.push(match[1]);
    }
  }
  return [...new Set(invalid)];
}

/** Render merge fields in text using recipient data. Missing keys → empty string. */
export function renderTemplate(text: string, context: Record<string, string>): string {
  return text.replace(/\{(\w+)\}/g, (_, key: string) => context[key] ?? '');
}
