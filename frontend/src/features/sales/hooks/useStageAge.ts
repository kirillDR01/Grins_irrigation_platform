// ============================================================
// useStageAge.ts — derive StageAge from a SalesEntry
// Drop at: frontend/src/features/sales/hooks/useStageAge.ts
//
// TODO(backend): replace `updated_at` fallback with a proper
// `stage_entered_at` column on the entry so edits don't reset
// the age clock.
// ============================================================

import { useMemo } from 'react';
import {
  AGE_THRESHOLDS,
  type SalesEntry,
  type StageAge,
  type AgeBucket,
} from '../types/pipeline';

function computeStageAge(entry: SalesEntry, now: number): StageAge {
  if (entry.status === 'closed_won' || entry.status === 'closed_lost') {
    return { days: 0, bucket: 'fresh', needsFollowup: false };
  }

  const stageKey =
    entry.status === 'estimate_scheduled' ? 'schedule_estimate' : entry.status;
  const thresholds = AGE_THRESHOLDS[stageKey as keyof typeof AGE_THRESHOLDS];
  const ref = entry.updated_at ?? entry.created_at;
  const days = Math.floor((now - new Date(ref).getTime()) / 86_400_000);

  let bucket: AgeBucket = 'fresh';
  if (days > thresholds.staleMax) bucket = 'stuck';
  else if (days > thresholds.freshMax) bucket = 'stale';

  return { days, bucket, needsFollowup: bucket === 'stuck' };
}

export function useStageAge(entry: SalesEntry): StageAge {
  const now = Date.now();
  return useMemo(
    () => computeStageAge(entry, now),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [entry.status, entry.updated_at, entry.created_at, now],
  );
}

/** Given a set of rows, count how many are stuck. Memoise at call site. */
export function countStuck(rows: SalesEntry[]): number {
  let n = 0;
  for (const r of rows) {
    if (r.status === 'closed_won' || r.status === 'closed_lost') continue;
    const stageKey =
      r.status === 'estimate_scheduled' ? 'schedule_estimate' : r.status;
    const thresholds = AGE_THRESHOLDS[stageKey as keyof typeof AGE_THRESHOLDS];
    const ref = r.updated_at ?? r.created_at;
    const days = Math.floor((Date.now() - new Date(ref).getTime()) / 86_400_000);
    if (days > thresholds.staleMax) n++;
  }
  return n;
}
