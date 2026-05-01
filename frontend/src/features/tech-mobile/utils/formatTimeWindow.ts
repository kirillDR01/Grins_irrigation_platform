/**
 * Format an `HH:MM:SS` (or `HH:MM`) backend time window into a 12-hour
 * display string like `8:00 AM – 9:25 AM`. Pure string ops — no timezone
 * surprises.
 */
export function formatTimeWindow(start: string, end: string): string {
  return `${formatHHMMSS(start)} – ${formatHHMMSS(end)}`;
}

function formatHHMMSS(hms: string): string {
  const [hStr, mStr] = hms.split(':');
  const h = Number.parseInt(hStr, 10);
  const m = Number.parseInt(mStr, 10);
  const period = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return m === 0
    ? `${h12}:00 ${period}`
    : `${h12}:${m.toString().padStart(2, '0')} ${period}`;
}
