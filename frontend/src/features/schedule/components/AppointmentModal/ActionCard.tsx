/**
 * ActionCard — single workflow action button with active/disabled/done states.
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.7, 18.2
 */

import { type ReactNode } from 'react';
import { Check } from 'lucide-react';
import { cn } from '@/shared/utils/cn';

interface ActionCardProps {
  label: string;
  icon: ReactNode;
  /** Stage accent color (Tailwind bg class, e.g. 'bg-blue-600') */
  stageColor: string;
  state: 'active' | 'disabled' | 'done';
  completedAt?: string | null;
  onClick?: () => void;
  'aria-label'?: string;
}

function formatTs(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

export function ActionCard({
  label,
  icon,
  stageColor,
  state,
  completedAt,
  onClick,
  'aria-label': ariaLabel,
}: ActionCardProps) {
  const isDone = state === 'done';
  const isDisabled = state === 'disabled';
  const isActive = state === 'active';

  return (
    <button
      type="button"
      onClick={isActive ? onClick : undefined}
      disabled={isDisabled}
      aria-label={ariaLabel ?? label}
      aria-live={isDone ? 'polite' : undefined}
      className={cn(
        'flex-1 min-h-[104px] rounded-[14px] border-[1.5px] flex flex-col items-center justify-center gap-2 px-2 py-3 transition-all duration-150',
        isActive && cn(stageColor, 'border-transparent text-white cursor-pointer hover:opacity-90'),
        isDisabled && 'bg-gray-50 border-[#E5E7EB] text-gray-400 opacity-40 cursor-not-allowed',
        isDone && 'bg-white border-green-400 text-[#0B1220]',
      )}
    >
      {isDone ? (
        <>
          <div className="w-9 h-9 rounded-full bg-green-100 flex items-center justify-center">
            <Check size={18} strokeWidth={2.5} className="text-green-600" />
          </div>
          <span className="text-[12px] font-bold text-center leading-tight">{label}</span>
          {completedAt && (
            <span className="text-[10px] font-mono text-[#6B7280]">{formatTs(completedAt)}</span>
          )}
        </>
      ) : (
        <>
          <div
            className={cn(
              'w-9 h-9 rounded-full flex items-center justify-center',
              isActive ? 'bg-white/20' : 'bg-gray-200',
            )}
          >
            <span className={cn('w-5 h-5 flex items-center justify-center [&>svg]:w-5 [&>svg]:h-5 [&>svg]:stroke-[2]', isActive ? 'text-white' : 'text-gray-400')}>
              {icon}
            </span>
          </div>
          <span className="text-[12px] font-bold text-center leading-tight">{label}</span>
        </>
      )}
    </button>
  );
}
