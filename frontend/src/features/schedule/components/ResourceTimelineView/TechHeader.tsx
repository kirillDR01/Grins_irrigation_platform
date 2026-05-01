/**
 * TechHeader — left-side row header for week / day mode.
 *
 * Renders a 4px colored accent bar (staffColors.ts hex), an avatar circle
 * with the tech's initials, the staff name, and the per-day or per-week
 * utilization %.
 */

import { getStaffColor } from '../../utils/staffColors';
import { getInitials } from './utils';
import type { Staff } from '@/features/staff/types';

export interface TechHeaderProps {
  staff: Staff;
  /** 0–100; rendered as `'{n}% utilized'`. Null while loading. */
  utilizationPct: number | null;
}

export function TechHeader({ staff, utilizationPct }: TechHeaderProps) {
  const color = getStaffColor(staff.name);
  const initials = getInitials(staff.name);

  return (
    <div
      data-testid={`tech-header-${staff.id}`}
      className="flex items-center gap-2 p-2 border-b border-slate-100"
      style={{ borderLeft: `4px solid ${color}` }}
    >
      <div
        className="flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold text-white shrink-0"
        style={{ backgroundColor: color }}
        aria-hidden
      >
        {initials}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[13px] font-semibold text-slate-900 truncate">
          {staff.name}
        </div>
        <div className="text-[11px] text-slate-600">
          {utilizationPct === null
            ? 'Loading…'
            : `${Math.round(utilizationPct)}% utilized`}
        </div>
      </div>
    </div>
  );
}
