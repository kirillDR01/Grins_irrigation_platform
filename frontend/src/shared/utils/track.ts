/**
 * Telemetry stub. No SDK is wired in this codebase yet.
 * When a real SDK lands, swap the body of this function — every caller stays put.
 */
export function track(
  event: string,
  payload: Record<string, unknown> = {},
): void {
  console.info(`[track] ${event}`, payload);
}
