/**
 * Build a maps URL for a free-form address string. Picks Apple Maps on
 * iOS so taps open the native Maps app via universal links; otherwise
 * falls back to Google Maps (which the OS will route to whichever maps
 * app the user has set as default).
 */
export function buildMapsUrl(address: string): string {
  const q = encodeURIComponent(address);
  if (
    typeof navigator !== 'undefined' &&
    /iPhone|iPad|iPod/i.test(navigator.userAgent)
  ) {
    return `https://maps.apple.com/?daddr=${q}`;
  }
  return `https://www.google.com/maps/dir/?api=1&destination=${q}`;
}
