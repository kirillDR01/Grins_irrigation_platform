import { describe, it, expect } from 'vitest';
import type { AppointmentStatus } from '@/features/schedule/types';
import { deriveCardState } from './cardState';

describe('deriveCardState', () => {
  // One assertion per AppointmentStatus literal so an enum widening
  // forces a test break.
  it('maps in_progress → current', () => {
    expect(deriveCardState('in_progress')).toBe('current');
  });

  it('maps completed → complete', () => {
    expect(deriveCardState('completed')).toBe('complete');
  });

  it('maps cancelled → hidden', () => {
    expect(deriveCardState('cancelled')).toBe('hidden');
  });

  it('maps no_show → hidden', () => {
    expect(deriveCardState('no_show')).toBe('hidden');
  });

  it('maps pending → upcoming', () => {
    expect(deriveCardState('pending')).toBe('upcoming');
  });

  it('maps draft → upcoming', () => {
    expect(deriveCardState('draft')).toBe('upcoming');
  });

  it('maps scheduled → upcoming', () => {
    expect(deriveCardState('scheduled')).toBe('upcoming');
  });

  it('maps confirmed → upcoming', () => {
    expect(deriveCardState('confirmed')).toBe('upcoming');
  });

  it('maps en_route → upcoming', () => {
    expect(deriveCardState('en_route')).toBe('upcoming');
  });

  it('covers every AppointmentStatus literal', () => {
    const all: AppointmentStatus[] = [
      'pending',
      'draft',
      'scheduled',
      'confirmed',
      'en_route',
      'in_progress',
      'completed',
      'cancelled',
      'no_show',
    ];
    for (const status of all) {
      expect(['current', 'upcoming', 'complete', 'hidden']).toContain(
        deriveCardState(status)
      );
    }
  });
});
