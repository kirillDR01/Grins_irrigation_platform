/**
 * Job-type colour palette for the resource-timeline AppointmentCard.
 *
 * Returns a triple `{ bg, border, text }` of Tailwind class strings so
 * the card can apply background tint, accent border, and matching text.
 * Lookup is case-insensitive — Job.job_type is a free-form String(50)
 * (no DB enum), so production data may arrive with mixed casing.
 *
 * Distinct from `job-type-colors.ts`, which returns a category enum
 * for the Pick Jobs pill. Two consumers, two shapes — kept separate.
 */

export interface JobTypePalette {
  /** Tailwind background class for the card surface. */
  bg: string;
  /** Tailwind border class — also used as the SVG sparkline rect fill. */
  border: string;
  /** Tailwind text class for the job-type label. */
  text: string;
}

const NEUTRAL: JobTypePalette = {
  bg: 'bg-slate-50',
  border: 'border-slate-300',
  text: 'text-slate-900',
};

const PALETTES: Record<string, JobTypePalette> = {
  'spring opening': {
    bg: 'bg-emerald-50',
    border: 'border-emerald-400',
    text: 'text-emerald-900',
  },
  'fall closing': {
    bg: 'bg-orange-50',
    border: 'border-orange-400',
    text: 'text-orange-900',
  },
  maintenance: {
    bg: 'bg-blue-50',
    border: 'border-blue-400',
    text: 'text-blue-900',
  },
  'backflow test': {
    bg: 'bg-teal-50',
    border: 'border-teal-400',
    text: 'text-teal-900',
  },
  'new build': {
    bg: 'bg-purple-50',
    border: 'border-purple-400',
    text: 'text-purple-900',
  },
  repair: {
    bg: 'bg-rose-50',
    border: 'border-rose-400',
    text: 'text-rose-900',
  },
  diagnostic: {
    bg: 'bg-amber-50',
    border: 'border-amber-400',
    text: 'text-amber-900',
  },
  estimate: {
    bg: 'bg-indigo-50',
    border: 'border-indigo-400',
    text: 'text-indigo-900',
  },
};

export const JOB_TYPE_COLORS: Readonly<Record<string, JobTypePalette>> = PALETTES;

export function getJobTypeColor(
  jobType: string | null | undefined
): JobTypePalette {
  if (!jobType) return NEUTRAL;
  return PALETTES[jobType.trim().toLowerCase()] ?? NEUTRAL;
}
