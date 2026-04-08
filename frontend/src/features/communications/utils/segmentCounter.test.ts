import { describe, it, expect } from 'vitest';
import { countSegments, findInvalidMergeFields, renderTemplate, SENDER_PREFIX, STOP_FOOTER } from './segmentCounter';

describe('countSegments', () => {
  const overhead = SENDER_PREFIX.length + STOP_FOOTER.length; // 19 + 22 = 41

  it('returns GSM-7 encoding for plain ASCII text', () => {
    const { encoding } = countSegments('Hello');
    expect(encoding).toBe('GSM-7');
  });

  it('returns UCS-2 encoding when emoji present', () => {
    const { encoding } = countSegments('Hello 😀');
    expect(encoding).toBe('UCS-2');
  });

  it('counts single segment for short GSM-7 message', () => {
    // 'Hi' = 2 chars + 41 overhead = 43 chars, well under 160
    const { segments, chars } = countSegments('Hi');
    expect(segments).toBe(1);
    expect(chars).toBe(2 + overhead);
  });

  it('counts multiple segments for long GSM-7 message', () => {
    // 160 - overhead = 119 chars body fits in 1 segment
    // 120 chars body + 41 overhead = 161 → 2 segments (ceil(161/153))
    const body = 'A'.repeat(120);
    const { segments } = countSegments(body);
    expect(segments).toBe(2);
  });

  it('boundary: exactly 160 GSM-7 chars = 1 segment', () => {
    const bodyLen = 160 - overhead;
    const { segments, chars } = countSegments('A'.repeat(bodyLen));
    expect(chars).toBe(160);
    expect(segments).toBe(1);
  });

  it('boundary: 161 GSM-7 chars = 2 segments (ceil(161/153))', () => {
    const bodyLen = 161 - overhead;
    const { segments, chars } = countSegments('A'.repeat(bodyLen));
    expect(chars).toBe(161);
    expect(segments).toBe(2);
  });

  it('UCS-2: short emoji message = 1 segment', () => {
    const { segments } = countSegments('😀', { includePrefix: false, includeFooter: false });
    // '😀' is 2 chars (surrogate pair), under 70
    expect(segments).toBe(1);
  });

  it('UCS-2: over 70 chars uses 67-char segments', () => {
    // Create a body that with prefix+footer exceeds 70 UCS-2 chars
    const body = '你'.repeat(50); // 50 + 41 overhead = 91 chars → ceil(91/67) = 2
    const { segments, encoding } = countSegments(body);
    expect(encoding).toBe('UCS-2');
    expect(segments).toBe(2);
  });

  it('GSM-7 extension chars count as 2', () => {
    // '{' and '}' are GSM-7 extension, each counts as 2
    const { chars } = countSegments('{}', { includePrefix: false, includeFooter: false });
    expect(chars).toBe(4); // 2 extension chars × 2 each
  });

  it('respects includePrefix/includeFooter options', () => {
    const withBoth = countSegments('Hi');
    const withoutBoth = countSegments('Hi', { includePrefix: false, includeFooter: false });
    expect(withBoth.chars).toBeGreaterThan(withoutBoth.chars);
    expect(withoutBoth.chars).toBe(2);
  });
});

describe('findInvalidMergeFields', () => {
  it('returns empty for valid fields', () => {
    expect(findInvalidMergeFields('Hi {first_name}!')).toEqual([]);
  });

  it('detects invalid merge fields', () => {
    expect(findInvalidMergeFields('Hi {foo}!')).toEqual(['foo']);
  });

  it('deduplicates invalid fields', () => {
    expect(findInvalidMergeFields('{foo} and {foo}')).toEqual(['foo']);
  });

  it('returns empty for no merge fields', () => {
    expect(findInvalidMergeFields('Hello world')).toEqual([]);
  });

  it('allows all three valid fields', () => {
    expect(findInvalidMergeFields('{first_name} {last_name} {next_appointment_date}')).toEqual([]);
  });
});

describe('renderTemplate', () => {
  it('replaces known fields', () => {
    expect(renderTemplate('Hi {first_name}!', { first_name: 'John' })).toBe('Hi John!');
  });

  it('replaces missing fields with empty string', () => {
    expect(renderTemplate('Hi {first_name}!', {})).toBe('Hi !');
  });

  it('handles multiple fields', () => {
    expect(renderTemplate('{first_name} {last_name}', { first_name: 'A', last_name: 'B' })).toBe('A B');
  });
});
