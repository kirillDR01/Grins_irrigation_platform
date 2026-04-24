/**
 * TimelineStrip — 4-step progress indicator (Booked, En route, On site, Done).
 * Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
 */

import { Check } from 'lucide-react';
import { cn } from '@/shared/utils/cn';

const STEPS = ['Booked', 'En route', 'On site', 'Done'] as const;

interface TimelineStripProps {
  /** 0-based current step index (null = no active step) */
  currentStep: number | null;
  /** ISO timestamp strings for each step (index 0–3), null if not reached */
  timestamps: [string | null, string | null, string | null, string | null];
}

function formatTs(ts: string | null): string {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '—';
  }
}

export function TimelineStrip({ currentStep, timestamps }: TimelineStripProps) {
  return (
    <div
      className="px-5 py-4 flex-shrink-0 overflow-x-auto"
      style={{ minWidth: 0 }}
    >
      <div className="flex items-start" style={{ minWidth: '240px' }}>
        {STEPS.map((label, i) => {
          const isCompleted = currentStep !== null && i < currentStep;
          const isCurrent = currentStep === i;
          const isInactive = currentStep === null || i > currentStep;
          const isLast = i === STEPS.length - 1;

          return (
            <div key={label} className="flex items-start flex-1 min-w-[60px]">
              {/* Step + connector */}
              <div className="flex flex-col items-center flex-1">
                {/* Dot row */}
                <div className="flex items-center w-full">
                  {/* Left connector line */}
                  {i > 0 && (
                    <div
                      className={cn(
                        'flex-1 h-[2px]',
                        isCompleted || isCurrent ? 'bg-[#0B1220]' : 'bg-[#E5E7EB]',
                      )}
                    />
                  )}

                  {/* Dot */}
                  <div
                    className={cn(
                      'w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0',
                      isCompleted && 'bg-[#0B1220]',
                      isCurrent && 'bg-[#0B1220] ring-4 ring-blue-200',
                      isInactive && 'bg-white border-2 border-[#D1D5DB]',
                    )}
                  >
                    {isCompleted && (
                      <Check size={12} strokeWidth={3} className="text-white" />
                    )}
                    {isCurrent && (
                      <div className="w-2.5 h-2.5 rounded-full bg-blue-400" />
                    )}
                  </div>

                  {/* Right connector line */}
                  {!isLast && (
                    <div
                      className={cn(
                        'flex-1 h-[2px]',
                        isCompleted ? 'bg-[#0B1220]' : 'bg-[#E5E7EB]',
                      )}
                    />
                  )}
                </div>

                {/* Label + timestamp */}
                <div className="mt-1.5 text-center px-0.5">
                  <p
                    className={cn(
                      'text-[11px] font-semibold',
                      isCompleted || isCurrent ? 'text-[#0B1220]' : 'text-[#9CA3AF]',
                    )}
                  >
                    {label}
                  </p>
                  <p className="text-[10px] font-mono text-[#6B7280] mt-0.5">
                    {formatTs(timestamps[i])}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
