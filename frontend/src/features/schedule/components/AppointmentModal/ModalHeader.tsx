/**
 * ModalHeader — status badge, meta chips, job title, schedule line, close button.
 * Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 18.1
 */

import { type RefObject } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/shared/utils/cn';
import { appointmentStatusConfig } from '../../types';
import type { AppointmentStatus } from '../../types';

const HIDE_BADGE_STATUSES: AppointmentStatus[] = ['pending', 'draft'];

interface ModalHeaderProps {
  jobTitle: string;
  status: AppointmentStatus;
  propertyType?: string | null;
  appointmentId: string;
  scheduleLine?: string | null;
  onClose: () => void;
  closeButtonRef?: RefObject<HTMLButtonElement | null>;
}

export function ModalHeader({
  jobTitle,
  status,
  propertyType,
  appointmentId,
  scheduleLine,
  onClose,
  closeButtonRef,
}: ModalHeaderProps) {
  const statusCfg = appointmentStatusConfig[status];
  const showBadge = !HIDE_BADGE_STATUSES.includes(status);

  return (
    <div className="px-5 pt-5 pb-4 flex-shrink-0">
      {/* Top row: badge + close */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex flex-wrap items-center gap-2">
          {showBadge && (
            <span
              aria-label={`Status: ${statusCfg.label}`}
              className={cn(
                'inline-flex items-center px-3 py-1 rounded-full text-[12px] font-bold',
                statusCfg.bgColor,
                statusCfg.color,
              )}
            >
              {statusCfg.label}
            </span>
          )}
          {propertyType && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold bg-gray-100 text-gray-600">
              {propertyType}
            </span>
          )}
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold bg-gray-100 text-gray-500">
            #{appointmentId.slice(-6).toUpperCase()}
          </span>
        </div>
        <button
          ref={closeButtonRef}
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="w-11 h-11 flex items-center justify-center rounded-[12px] border-[1.5px] border-[#E5E7EB] bg-white hover:bg-gray-50 flex-shrink-0"
        >
          <X size={18} strokeWidth={2} />
        </button>
      </div>

      {/* Job title */}
      <h1 className="text-[26px] font-extrabold tracking-[-0.8px] text-[#0B1220] leading-tight mb-1">
        {jobTitle}
      </h1>

      {/* Schedule line */}
      {scheduleLine && (
        <p className="text-[15px] font-semibold text-[#4B5563]">{scheduleLine}</p>
      )}
    </div>
  );
}
