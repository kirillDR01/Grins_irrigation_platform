import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { WeekCalendar } from './WeekCalendar';
import type { EstimateBlock } from '../../types/pipeline';

const NOW = new Date(2026, 3, 21, 10, 35); // Tue Apr 21, 2026, 10:35 AM
const WEEK_START = new Date(2026, 3, 20); // Mon Apr 20

describe('WeekCalendar', () => {
  it('renders 7 day-header slots and the 28 row × 7 col grid', () => {
    render(
      <WeekCalendar
        weekStart={WEEK_START}
        now={NOW}
        estimates={[]}
        pick={null}
        loadingWeek={false}
        conflicts={[]}
        hasConflict={false}
        pickCustomerName="V P"
        onWeekChange={() => {}}
        onSlotClick={() => {}}
        onSlotDrag={() => {}}
      />,
    );
    expect(screen.getByTestId('schedule-visit-slot-0-0')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-visit-slot-6-27')).toBeInTheDocument();
  });

  it("marks today's column header with the today class", () => {
    const { container } = render(
      <WeekCalendar
        weekStart={WEEK_START}
        now={NOW}
        estimates={[]}
        pick={null}
        loadingWeek={false}
        conflicts={[]}
        hasConflict={false}
        pickCustomerName="V P"
        onWeekChange={() => {}}
        onSlotClick={() => {}}
        onSlotDrag={() => {}}
      />,
    );
    const todayCell = container.querySelector('[class*="today"]');
    expect(todayCell).not.toBeNull();
  });

  it('renders past slots with a "past" marker class', () => {
    render(
      <WeekCalendar
        weekStart={WEEK_START}
        now={NOW}
        estimates={[]}
        pick={null}
        loadingWeek={false}
        conflicts={[]}
        hasConflict={false}
        pickCustomerName="V P"
        onWeekChange={() => {}}
        onSlotClick={() => {}}
        onSlotDrag={() => {}}
      />,
    );
    // Mon (day 0) is past relative to Tue Apr 21 NOW.
    const monSlot = screen.getByTestId('schedule-visit-slot-0-0');
    expect(monSlot.className).toMatch(/past/);
  });

  it('renders an existing estimate block', () => {
    const block: EstimateBlock = {
      id: 'e1',
      date: '2026-04-22',
      startMin: 11 * 60,
      endMin: 12 * 60 + 30,
      customerName: 'K. Nakamura',
      jobSummary: 'Backflow',
      assignedToUserId: null,
    };
    render(
      <WeekCalendar
        weekStart={WEEK_START}
        now={NOW}
        estimates={[block]}
        pick={null}
        loadingWeek={false}
        conflicts={[]}
        hasConflict={false}
        pickCustomerName="V P"
        onWeekChange={() => {}}
        onSlotClick={() => {}}
        onSlotDrag={() => {}}
      />,
    );
    expect(screen.getByText('K. Nakamura')).toBeInTheDocument();
  });

  it('renders the pick block when pick is provided', () => {
    render(
      <WeekCalendar
        weekStart={WEEK_START}
        now={NOW}
        estimates={[]}
        pick={{ date: '2026-04-23', start: 14 * 60, end: 15 * 60 }}
        loadingWeek={false}
        conflicts={[]}
        hasConflict={false}
        pickCustomerName="V P"
        onWeekChange={() => {}}
        onSlotClick={() => {}}
        onSlotDrag={() => {}}
      />,
    );
    expect(screen.getByTestId('schedule-visit-pick')).toBeInTheDocument();
  });
});
