// ============================================================
// AutoNudgeSchedule.tsx — rendered inside NowCard for pending_approval
// Drop at: frontend/src/features/sales/components/AutoNudgeSchedule.tsx
// ============================================================

import { useMemo } from 'react';
import { Clock, Repeat, PauseCircle } from 'lucide-react';
import { format } from 'date-fns';
import { NUDGE_CADENCE_DAYS, type NudgeStep } from '../types/pipeline';

interface AutoNudgeScheduleProps {
  estimateSentAt: string;       // ISO
  paused?: boolean;
}

const NUDGE_COPY: Record<number, { when: string; message: string } | null> = {
  0: { when: 'Initial estimate sent',        message: 'Initial estimate sent' },
  2: { when: 'Day 2',                        message: '"Did you receive the estimate? Any questions?"' },
  5: { when: 'Day 5',                        message: '"Just checking in on the estimate"' },
  8: { when: 'Day 8',                        message: '"Following up one more time"' },
};

export function AutoNudgeSchedule({ estimateSentAt, paused }: AutoNudgeScheduleProps) {
  const steps = useMemo(() => computeSteps(estimateSentAt), [estimateSentAt]);
  const sent = new Date(estimateSentAt);

  return (
    <div
      className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm space-y-1"
      data-testid="auto-nudge-schedule"
    >
      {paused && (
        <div
          className="-mx-3 -mt-3 mb-1 px-3 py-1.5 bg-slate-200 text-slate-700 text-xs font-medium rounded-t-lg"
          data-testid="auto-nudge-paused-banner"
        >
          <PauseCircle className="inline h-3.5 w-3.5 mr-1 -mt-0.5" />
          Paused. Resume to continue auto-follow-up.
        </div>
      )}

      <div className="text-slate-900 font-semibold">
        <Clock className="inline h-3.5 w-3.5 mr-1 -mt-0.5" />
        Auto follow-up schedule{' '}
        <span className="text-slate-500 font-normal">· SMS + email</span>
      </div>

      {steps.map((step) => (
        <NudgeRow
          key={step.dayOffset}
          step={step}
          paused={paused}
          sentDate={sent}
        />
      ))}
    </div>
  );
}

function NudgeRow({
  step, paused, sentDate,
}: {
  step: NudgeStep;
  paused?: boolean;
  sentDate: Date;
}) {
  const strike = paused && (step.state === 'next' || step.state === 'future' || step.state === 'loop');

  const base = 'flex items-start gap-1.5';
  const toneClass = {
    done:   'text-emerald-700',
    next:   'text-amber-700 bg-amber-50 -mx-3 px-3 py-1 font-semibold rounded',
    future: 'text-slate-500',
    loop:   'text-slate-700 italic pt-2 mt-1 border-t border-slate-200',
  }[step.state];
  const lead = {
    done: '✓',
    next: '⏰',
    future: '·',
    loop: '🔁',
  }[step.state];

  const when = step.dayOffset >= 0
    ? `Day ${step.dayOffset} · ${format(addDays(sentDate, step.dayOffset), 'MMM d')}${step.dayOffset > 0 ? ' 9 AM' : ''}`
    : 'Every Monday · 9 AM';
  const msg = step.dayOffset >= 0 ? NUDGE_COPY[step.dayOffset]?.message : '"Reply A to approve, R to reject" — one-letter reply auto-updates the pipeline';

  return (
    <div
      className={`${base} ${toneClass} ${strike ? 'line-through opacity-60' : ''}`}
      data-testid={`auto-nudge-row-${step.dayOffset}`}
      data-state={step.state}
    >
      <span aria-hidden className="w-4 shrink-0 text-center">{lead}</span>
      <span>
        <span className="font-medium">{when}</span>
        {msg && <span className="text-inherit opacity-90"> · {msg}</span>}
      </span>
    </div>
  );
}

// ────────── Logic ──────────

function computeSteps(estimateSentAt: string): NudgeStep[] {
  const now = Date.now();
  const sent = new Date(estimateSentAt).getTime();
  const dayNum = Math.floor((now - sent) / 86_400_000);

  // Find the next-upcoming offset (first offset > dayNum)
  const offsets = [...NUDGE_CADENCE_DAYS];
  const nextIdx = offsets.findIndex(o => o > dayNum);

  const steps: NudgeStep[] = offsets.map((o, i) => ({
    dayOffset: o,
    state: o < dayNum
      ? 'done'
      : i === nextIdx
        ? 'next'
        : 'future',
    when: '',   // rendered from NUDGE_COPY at render time
    message: '',
  }));

  steps.push({
    dayOffset: -1,
    state: 'loop',
    when: 'Every Monday 9 AM',
    message: '',
  });

  return steps;
}

function addDays(d: Date, n: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}
