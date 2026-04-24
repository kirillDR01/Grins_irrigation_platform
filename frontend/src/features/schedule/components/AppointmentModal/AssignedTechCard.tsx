/**
 * AssignedTechCard — tech name, route number, optional reassign button.
 * Requirements: 10.1, 10.2
 */

import { User } from 'lucide-react';
import { LinkButton } from './LinkButton';

interface AssignedTechCardProps {
  techName: string;
  routeOrder?: number | null;
  canReassign?: boolean;
  onReassign?: () => void;
}

export function AssignedTechCard({
  techName,
  routeOrder,
  canReassign,
  onReassign,
}: AssignedTechCardProps) {
  return (
    <div className="rounded-[14px] border border-[#E5E7EB] bg-white px-4 py-3 flex items-center gap-3">
      <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
        <User size={16} className="text-gray-500" strokeWidth={2} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-extrabold tracking-[0.6px] text-[#9CA3AF] uppercase">
          Assigned Tech
        </p>
        <p className="text-[15px] font-bold text-[#0B1220] leading-tight">{techName}</p>
        {routeOrder != null && (
          <p className="text-[12px] font-semibold text-[#6B7280]">Route #{routeOrder}</p>
        )}
      </div>
      {canReassign && onReassign && (
        <LinkButton onClick={onReassign} className="flex-shrink-0 text-[13px]">
          Reassign
        </LinkButton>
      )}
    </div>
  );
}
