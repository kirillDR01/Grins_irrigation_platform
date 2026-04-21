// ActivityStrip unit tests — Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ActivityStrip } from './ActivityStrip';
import type { ActivityEvent } from '../types/pipeline';

describe('ActivityStrip', () => {
  it('returns null for empty events', () => {
    const { container } = render(<ActivityStrip events={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders correct glyphs per event kind', () => {
    const events: ActivityEvent[] = [
      { kind: 'estimate_sent', label: 'Estimate sent', tone: 'done' },
      { kind: 'nudge_sent', label: 'Nudge sent', tone: 'neutral' },
      { kind: 'approved', label: 'Approved', tone: 'done' },
    ];
    render(<ActivityStrip events={events} />);
    expect(screen.getByTestId('activity-event-estimate_sent').textContent).toContain('✉');
    expect(screen.getByTestId('activity-event-nudge_sent').textContent).toContain('⏰');
    expect(screen.getByTestId('activity-event-approved').textContent).toContain('✅');
  });

  it('applies tone classes correctly', () => {
    const events: ActivityEvent[] = [
      { kind: 'approved', label: 'Approved', tone: 'done' },
      { kind: 'nudge_next', label: 'Next nudge', tone: 'wait' },
      { kind: 'estimate_viewed', label: 'Viewed', tone: 'neutral' },
    ];
    render(<ActivityStrip events={events} />);
    expect(screen.getByTestId('activity-event-approved').className).toContain('text-slate-600');
    expect(screen.getByTestId('activity-event-nudge_next').className).toContain('text-amber-700');
    expect(screen.getByTestId('activity-event-nudge_next').className).toContain('font-medium');
    expect(screen.getByTestId('activity-event-estimate_viewed').className).toContain('text-slate-500');
  });

  it('renders · separators between events', () => {
    const events: ActivityEvent[] = [
      { kind: 'estimate_sent', label: 'Sent', tone: 'done' },
      { kind: 'estimate_viewed', label: 'Viewed', tone: 'neutral' },
      { kind: 'approved', label: 'Approved', tone: 'done' },
    ];
    render(<ActivityStrip events={events} />);
    const strip = screen.getByTestId('activity-strip');
    // 2 separators for 3 events
    const separators = strip.querySelectorAll('[aria-hidden]');
    // separators include glyphs (aria-hidden) + dot separators
    const dots = Array.from(separators).filter(el => el.textContent === '·');
    expect(dots).toHaveLength(2);
  });

  it('renders activity-strip data-testid', () => {
    const events: ActivityEvent[] = [
      { kind: 'moved_from_leads', label: 'Moved from leads', tone: 'neutral' },
    ];
    render(<ActivityStrip events={events} />);
    expect(screen.getByTestId('activity-strip')).toBeInTheDocument();
  });

  it('renders event data-testid per kind', () => {
    const events: ActivityEvent[] = [
      { kind: 'visit_scheduled', label: 'Visit scheduled', tone: 'done' },
      { kind: 'declined', label: 'Declined', tone: 'done' },
    ];
    render(<ActivityStrip events={events} />);
    expect(screen.getByTestId('activity-event-visit_scheduled')).toBeInTheDocument();
    expect(screen.getByTestId('activity-event-declined')).toBeInTheDocument();
  });
});
