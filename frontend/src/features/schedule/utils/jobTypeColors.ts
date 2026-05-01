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
  /** Tailwind border class — used for the card's accent left border. */
  border: string;
  /** Tailwind text class for the job-type label. */
  text: string;
  /** CSS color string suitable as an SVG `fill` value (sparkline rects). */
  fill: string;
}

const NEUTRAL: JobTypePalette = {
  bg: 'bg-slate-50',
  border: 'border-slate-300',
  text: 'text-slate-900',
  fill: '#cbd5e1', // slate-300
};

const PALETTES: Record<string, JobTypePalette> = {
  'spring opening': {
    bg: 'bg-emerald-50',
    border: 'border-emerald-400',
    text: 'text-emerald-900',
    fill: '#34d399', // emerald-400
  },
  'fall closing': {
    bg: 'bg-orange-50',
    border: 'border-orange-400',
    text: 'text-orange-900',
    fill: '#fb923c', // orange-400
  },
  maintenance: {
    bg: 'bg-blue-50',
    border: 'border-blue-400',
    text: 'text-blue-900',
    fill: '#60a5fa', // blue-400
  },
  'backflow test': {
    bg: 'bg-teal-50',
    border: 'border-teal-400',
    text: 'text-teal-900',
    fill: '#2dd4bf', // teal-400
  },
  'new build': {
    bg: 'bg-purple-50',
    border: 'border-purple-400',
    text: 'text-purple-900',
    fill: '#c084fc', // purple-400
  },
  repair: {
    bg: 'bg-rose-50',
    border: 'border-rose-400',
    text: 'text-rose-900',
    fill: '#fb7185', // rose-400
  },
  diagnostic: {
    bg: 'bg-amber-50',
    border: 'border-amber-400',
    text: 'text-amber-900',
    fill: '#fbbf24', // amber-400
  },
  estimate: {
    bg: 'bg-indigo-50',
    border: 'border-indigo-400',
    text: 'text-indigo-900',
    fill: '#818cf8', // indigo-400
  },
};

export const JOB_TYPE_COLORS: Readonly<Record<string, JobTypePalette>> = PALETTES;

export function getJobTypeColor(
  jobType: string | null | undefined
): JobTypePalette {
  if (!jobType) return NEUTRAL;
  return PALETTES[jobType.trim().toLowerCase()] ?? NEUTRAL;
}
