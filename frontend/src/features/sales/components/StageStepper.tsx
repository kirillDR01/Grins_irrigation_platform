// StageStepper.tsx — 5-step stage indicator
// Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 16.2, 16.8

import { MoreHorizontal, X, Calendar } from 'lucide-react';
import { STAGES, STAGE_INDEX, type StageKey } from '../types/pipeline';

interface StageStepperProps {
  currentStage: StageKey;
  onOverrideClick: () => void;
  onMarkLost: () => void;
  visitScheduled?: boolean;
  visitLabel?: string;
}

type StepState = 'done' | 'active' | 'waiting' | 'future';

export function StageStepper({
  currentStage,
  onOverrideClick,
  onMarkLost,
  visitScheduled,
  visitLabel,
}: StageStepperProps) {
  const currentIdx = STAGE_INDEX[currentStage];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4" data-testid="stage-stepper">
      {/* Phase row */}
      <div className="grid grid-cols-[1fr_2fr_2fr] text-[11px] uppercase tracking-[0.08em] text-slate-400 mb-3 px-2">
        <span>Plan</span>
        <span>Sign</span>
        <span>Close</span>
      </div>

      {/* Stepper row */}
      <div className="flex items-start">
        {STAGES.map((s, i) => {
          const state: StepState =
            i < currentIdx
              ? 'done'
              : i === currentIdx
                ? s.key === 'pending_approval'
                  ? 'waiting'
                  : 'active'
                : 'future';
          const isLast = i === STAGES.length - 1;
          return (
            <div key={s.key} className="flex-1 flex items-start">
              <Step
                state={state}
                index={i}
                label={s.shortLabel}
                stageKey={s.key}
                badge={
                  s.key === 'schedule_estimate' && visitScheduled
                    ? `📅 ${visitLabel ?? 'Scheduled'}`
                    : undefined
                }
              />
              {!isLast && <Connector done={i < currentIdx} />}
            </div>
          );
        })}
      </div>

      {/* Footer row */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100">
        <button
          type="button"
          onClick={onOverrideClick}
          data-testid="stage-stepper-override"
          className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1"
        >
          <MoreHorizontal className="h-3.5 w-3.5" />
          change stage manually
        </button>
        <button
          type="button"
          onClick={onMarkLost}
          data-testid="stage-stepper-mark-lost"
          className="text-xs text-red-600 hover:text-red-700 flex items-center gap-1"
        >
          <X className="h-3.5 w-3.5" />
          Mark Lost
        </button>
      </div>
    </div>
  );
}

function Step({
  state,
  index,
  label,
  stageKey,
  badge,
}: {
  state: StepState;
  index: number;
  label: string;
  stageKey: string;
  badge?: string;
}) {
  const dotClass = {
    done: 'bg-emerald-500 text-white',
    active: 'bg-slate-900 text-white',
    waiting:
      'border-2 border-dashed border-amber-400 text-amber-600 bg-amber-50 motion-safe:animate-pulse',
    future: 'border border-slate-300 text-slate-400 bg-white',
  }[state];

  const labelClass = {
    done: 'text-emerald-700',
    active: 'text-slate-900 font-semibold',
    waiting: 'text-amber-700 font-semibold',
    future: 'text-slate-400',
  }[state];

  return (
    <div
      className="flex flex-col items-center text-center gap-1 min-w-0"
      data-testid={`stage-step-${stageKey}`}
      data-state={state}
    >
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${dotClass}`}
      >
        {state === 'done' ? '✓' : index + 1}
      </div>
      <span className={`text-[11px] ${labelClass} max-w-[96px] truncate`}>{label}</span>
      {badge && (
        <span className="mt-0.5 text-[10px] rounded-full bg-slate-100 text-slate-600 px-1.5 py-0.5 inline-flex items-center gap-1">
          <Calendar className="h-3 w-3" />
          {badge.replace(/^📅\s*/, '')}
        </span>
      )}
    </div>
  );
}

function Connector({ done }: { done: boolean }) {
  return (
    <div className={`h-[2px] flex-1 mt-[13px] ${done ? 'bg-emerald-500' : 'bg-slate-200'}`} />
  );
}
