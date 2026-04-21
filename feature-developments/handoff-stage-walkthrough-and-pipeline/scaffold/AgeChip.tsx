// ============================================================
// ageChip.tsx — age-in-stage chip + threshold helpers
// Drop at: frontend/src/features/sales/components/AgeChip.tsx
// ============================================================

import type { AgeBucket, StageAge } from '../types/pipeline';

interface AgeChipProps {
  age: StageAge;
  stageKey: string;   // for aria-label, e.g. "pending_approval"
  'data-testid'?: string;
}

const BUCKET_STYLES: Record<AgeBucket, { ring: string; glyph: string; label: string }> = {
  fresh: {
    ring: 'text-emerald-700 bg-emerald-50 border-emerald-500',
    glyph: '●',
    label: 'FRESH',
  },
  stale: {
    ring: 'text-amber-700 bg-amber-50 border-amber-500',
    glyph: '⚡',
    label: 'STALE',
  },
  stuck: {
    ring: 'text-red-700 bg-red-50 border-red-500',
    glyph: '⚡',
    label: 'STUCK',
  },
};

export function AgeChip({ age, stageKey, ...rest }: AgeChipProps) {
  const s = BUCKET_STYLES[age.bucket];
  return (
    <span
      className={[
        'ml-2 inline-flex items-center gap-1 rounded-full border-[1.5px] px-2 py-0.5',
        'text-[11px] font-semibold uppercase tracking-[0.04em] leading-none',
        s.ring,
      ].join(' ')}
      aria-label={`${s.label} — ${age.days} days in ${stageKey.replace(/_/g, ' ')}`}
      data-testid={rest['data-testid']}
      data-bucket={age.bucket}
    >
      <span aria-hidden>{s.glyph}</span>
      <span>{Math.max(1, age.days)}d</span>
    </span>
  );
}
