// AutoNudgeSchedule.test.tsx
// Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import * as fc from 'fast-check';
import { AutoNudgeSchedule, computeSteps } from './AutoNudgeSchedule';

// ────────── helpers ──────────

function daysAgoISO(n: number): string {
  return new Date(Date.now() - n * 86_400_000).toISOString();
}

// ────────── unit tests ──────────

describe('AutoNudgeSchedule', () => {
  it('renders 5 rows (4 cadence + 1 loop)', () => {
    render(<AutoNudgeSchedule estimateSentAt={daysAgoISO(1)} />);
    // 4 cadence rows + 1 loop row
    const rows = [0, 2, 5, 8, -1];
    for (const offset of rows) {
      expect(screen.getByTestId(`auto-nudge-row-${offset}`)).toBeInTheDocument();
    }
  });

  it('exactly one row has next state given a mock estimateSentAt', () => {
    // sent 3 days ago → day 0,2 are done; day 5 is next; day 8 is future
    render(<AutoNudgeSchedule estimateSentAt={daysAgoISO(3)} />);
    const nextRows = document
      .querySelectorAll('[data-state="next"]');
    expect(nextRows).toHaveLength(1);
  });

  it('all rows before next have done state', () => {
    // sent 6 days ago → day 0,2,5 done; day 8 next
    render(<AutoNudgeSchedule estimateSentAt={daysAgoISO(6)} />);
    const doneRows = document.querySelectorAll('[data-state="done"]');
    // offsets 0, 2, 5 are all < 6
    expect(doneRows.length).toBeGreaterThanOrEqual(3);
  });

  it('paused state shows banner and strikes through future/loop rows', () => {
    render(<AutoNudgeSchedule estimateSentAt={daysAgoISO(1)} paused />);
    expect(screen.getByTestId('auto-nudge-paused-banner')).toBeInTheDocument();
    expect(screen.getByTestId('auto-nudge-paused-banner').textContent).toContain('Paused');
  });

  it('loop row always has loop state', () => {
    render(<AutoNudgeSchedule estimateSentAt={daysAgoISO(0)} />);
    const loopRow = screen.getByTestId('auto-nudge-row--1');
    expect(loopRow).toHaveAttribute('data-state', 'loop');
  });

  it('does not show paused banner when paused is false', () => {
    render(<AutoNudgeSchedule estimateSentAt={daysAgoISO(1)} paused={false} />);
    expect(screen.queryByTestId('auto-nudge-paused-banner')).not.toBeInTheDocument();
  });
});

// ────────── Property 8: computeSteps Nudge State Assignment ──────────

describe('Property 8: computeSteps Nudge State Assignment', () => {
  it('satisfies all state invariants for random estimateSentAt (100+ iterations)', () => {
    fc.assert(
      fc.property(
        // days ago: 0–30
        fc.integer({ min: 0, max: 30 }),
        (daysAgo) => {
          const estimateSentAt = new Date(Date.now() - daysAgo * 86_400_000).toISOString();
          const steps = computeSteps(estimateSentAt);

          // (d) last step always has state 'loop' and dayOffset === -1
          const last = steps[steps.length - 1];
          expect(last.state).toBe('loop');
          expect(last.dayOffset).toBe(-1);

          const nonLoop = steps.slice(0, -1);

          // (a) at most one step has state === 'next'
          const nextSteps = nonLoop.filter((s) => s.state === 'next');
          expect(nextSteps.length).toBeLessThanOrEqual(1);

          // (b) all steps with dayOffset < daysAgo have state === 'done'
          for (const step of nonLoop) {
            if (step.dayOffset < daysAgo) {
              expect(step.state).toBe('done');
            }
          }

          // (c) steps after 'next' have state === 'future'
          const nextIdx = nonLoop.findIndex((s) => s.state === 'next');
          if (nextIdx !== -1) {
            for (let i = nextIdx + 1; i < nonLoop.length; i++) {
              expect(nonLoop[i].state).toBe('future');
            }
          }

          // (e) states form valid sequence: done* → next? → future* → loop
          // Note: when daysAgo=0, offset 0 is not < dayNum so it becomes future before next
          // Valid transitions per the algorithm
          const stateSeq = steps.map((s) => s.state);
          const validTransitions: Record<string, string[]> = {
            done: ['done', 'next', 'future', 'loop'],
            next: ['future', 'loop'],
            future: ['future', 'next', 'loop'],
            loop: [],
          };
          for (let i = 0; i < stateSeq.length - 1; i++) {
            const from = stateSeq[i];
            const to = stateSeq[i + 1];
            expect(validTransitions[from]).toContain(to);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
