/**
 * Pure colour-class mapper for job-type pills on the Pick Jobs page.
 *
 * Backend enum at `src/grins_platform/api/v1/schedule.py:486` produces the
 * canonical lowercase strings below. Anything else (future variants,
 * unexpected values) falls through to the neutral pill so the UI never
 * crashes on unknown data.
 */

export type JobTypeColor = 'spring' | 'fall' | 'mid' | 'neutral';

const JOB_TYPE_COLORS: Record<string, JobTypeColor> = {
  spring_startup: 'spring',
  fall_winterization: 'fall',
  mid_season_inspection: 'mid',
};

export function getJobTypeColorClass(jobType: string): JobTypeColor {
  return JOB_TYPE_COLORS[jobType] ?? 'neutral';
}
