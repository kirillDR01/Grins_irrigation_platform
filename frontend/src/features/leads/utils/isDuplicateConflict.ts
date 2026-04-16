import axios, { type AxiosError } from 'axios';

import type { DuplicateConflictError } from '../types';

/**
 * Type guard for the 409 conflict response from
 * POST /api/v1/leads/{id}/convert (and any other lead endpoint that
 * triggers the Tier-1 duplicate guard — e.g., move-to-jobs, move-to-sales).
 *
 * The BE wraps the detail in FastAPI's ``{detail: {...}}`` envelope, so we
 * check the status and the ``detail.error === 'duplicate_found'`` marker.
 *
 * Validates: CR-6 (bughunt 2026-04-16).
 */
export function isDuplicateConflict(
  err: unknown,
): err is AxiosError<{ detail: DuplicateConflictError }> {
  if (!axios.isAxiosError(err)) return false;
  if (err.response?.status !== 409) return false;
  const detail = err.response?.data?.detail;
  return (
    !!detail &&
    typeof detail === 'object' &&
    (detail as DuplicateConflictError).error === 'duplicate_found' &&
    Array.isArray((detail as DuplicateConflictError).duplicates)
  );
}
