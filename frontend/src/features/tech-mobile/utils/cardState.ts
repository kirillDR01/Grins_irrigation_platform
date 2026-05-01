import type { AppointmentStatus } from '@/features/schedule/types';

export type CardState = 'current' | 'upcoming' | 'complete' | 'hidden';

export function deriveCardState(status: AppointmentStatus): CardState {
  if (status === 'in_progress') return 'current';
  if (status === 'completed') return 'complete';
  if (status === 'cancelled' || status === 'no_show') return 'hidden';
  return 'upcoming';
}
