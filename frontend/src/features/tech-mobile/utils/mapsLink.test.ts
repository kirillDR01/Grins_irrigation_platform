import { describe, it, expect, afterEach } from 'vitest';
import { buildMapsUrl } from './mapsLink';

const ORIGINAL_UA = navigator.userAgent;

function setUserAgent(ua: string): void {
  Object.defineProperty(navigator, 'userAgent', {
    value: ua,
    configurable: true,
  });
}

describe('buildMapsUrl', () => {
  afterEach(() => {
    setUserAgent(ORIGINAL_UA);
  });

  it('returns an Apple Maps URL on iPhone UA', () => {
    setUserAgent(
      'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15'
    );
    expect(buildMapsUrl('123 Main St, Eden Prairie, MN')).toBe(
      'https://maps.apple.com/?daddr=123%20Main%20St%2C%20Eden%20Prairie%2C%20MN'
    );
  });

  it('returns an Apple Maps URL on iPad UA', () => {
    setUserAgent('Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X)');
    expect(buildMapsUrl('Test')).toContain('maps.apple.com');
  });

  it('returns a Google Maps URL on Android UA', () => {
    setUserAgent('Mozilla/5.0 (Linux; Android 14; Pixel 8)');
    expect(buildMapsUrl('123 Main St')).toBe(
      'https://www.google.com/maps/dir/?api=1&destination=123%20Main%20St'
    );
  });

  it('returns a Google Maps URL on a desktop UA', () => {
    setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)');
    expect(buildMapsUrl('Anywhere')).toBe(
      'https://www.google.com/maps/dir/?api=1&destination=Anywhere'
    );
  });

  it('encodes spaces and commas safely', () => {
    setUserAgent('Mozilla/5.0 (Windows NT 10.0)');
    const url = buildMapsUrl('1 Foo, Bar');
    expect(url).toContain('1%20Foo%2C%20Bar');
  });
});
