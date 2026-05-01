/**
 * AppointmentCard — single appointment surface for the resource-timeline.
 *
 * Two render variants:
 *  - `stacked` (week mode): full-width compact card stacked inside a cell.
 *  - `absolute` (day mode): absolute-positioned via inline `style`.
 *
 * Status drives border-style + opacity (parity with the legacy CalendarView
 * cues). Job type drives the colored left-border accent + label color.
 * Up to 3 lucide icons render in severity order: priority > no-reply >
 * reschedule > prepaid (💎 Gem).
 */

import type { CSSProperties, ReactElement } from 'react';
import { Star, BellRing, RefreshCcw, Gem } from 'lucide-react';
import { SendConfirmationButton } from '../SendConfirmationButton';
import { getJobTypeColor } from '../../utils/jobTypeColors';
import type { Appointment, AppointmentStatus } from '../../types';
import type { DragPayload } from './types';
import { formatTimeRange } from './utils';

export interface AppointmentCardProps {
  appointment: Appointment;
  /** Joined city from the appointment's property; null when not available. */
  customerCity?: string | null;
  variant: 'stacked' | 'absolute';
  /** When true, paints the clear-day red ring + ⚠️ prefix on the title. */
  isOnSelectedDate?: boolean;
  /** Inline style — used by `variant='absolute'` for left/width/top/height. */
  style?: CSSProperties;
  onAppointmentClick: (id: string) => void;
}

const STATUS_BORDER_STYLE: Record<
  AppointmentStatus,
  'solid' | 'dashed' | 'dotted'
> = {
  confirmed: 'solid',
  en_route: 'solid',
  in_progress: 'solid',
  completed: 'solid',
  pending: 'dashed',
  scheduled: 'dashed',
  cancelled: 'dashed',
  no_show: 'dashed',
  draft: 'dotted',
};

const STATUS_OPACITY: Record<AppointmentStatus, number> = {
  confirmed: 1,
  en_route: 1,
  in_progress: 1,
  completed: 1,
  pending: 0.65,
  scheduled: 0.65,
  cancelled: 0.65,
  no_show: 0.65,
  draft: 0.5,
};

export function AppointmentCard({
  appointment,
  customerCity,
  variant,
  isOnSelectedDate = false,
  style,
  onAppointmentClick,
}: AppointmentCardProps) {
  const palette = getJobTypeColor(appointment.job_type);
  const borderStyle = STATUS_BORDER_STYLE[appointment.status];
  const opacity = STATUS_OPACITY[appointment.status];
  const isDraft = appointment.status === 'draft';
  const hasServiceAgreement = !!appointment.service_agreement_id;

  // Severity-ordered icons, max 3 — priority > no-reply > reschedule > prepaid.
  type IconSpec = {
    key: 'priority' | 'no-reply' | 'reschedule' | 'prepaid';
    el: ReactElement;
  };
  const allIcons: IconSpec[] = [];
  if (appointment.priority_level !== null && appointment.priority_level > 0) {
    allIcons.push({
      key: 'priority',
      el: (
        <Star
          key="priority"
          className="size-3 text-amber-500 fill-amber-500"
          aria-label="High priority"
          data-testid="card-icon-priority"
        />
      ),
    });
  }
  if (appointment.reply_state?.has_no_reply_flag) {
    allIcons.push({
      key: 'no-reply',
      el: (
        <BellRing
          key="no-reply"
          className="size-3 text-rose-500"
          aria-label="Needs review"
          data-testid="card-icon-no-reply"
        />
      ),
    });
  }
  if (appointment.reply_state?.has_pending_reschedule) {
    allIcons.push({
      key: 'reschedule',
      el: (
        <RefreshCcw
          key="reschedule"
          className="size-3 text-blue-500"
          aria-label="Reschedule pending"
          data-testid="card-icon-reschedule"
        />
      ),
    });
  }
  if (hasServiceAgreement) {
    allIcons.push({
      key: 'prepaid',
      el: (
        <Gem
          key="prepaid"
          className="size-3 text-emerald-500"
          aria-label="Prepaid (service agreement)"
          data-testid="card-icon-prepaid"
        />
      ),
    });
  }
  const iconsToRender = allIcons.slice(0, 3);

  const titlePrefix = isOnSelectedDate ? '⚠️ ' : '';
  const customerLine = customerCity
    ? `${appointment.customer_name ?? ''} · ${customerCity}`
    : appointment.customer_name ?? '';

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
    const payload: DragPayload = {
      appointmentId: appointment.id,
      originStaffId: appointment.staff_id,
      originDate: appointment.scheduled_date,
      originStartTime: appointment.time_window_start,
      originEndTime: appointment.time_window_end,
    };
    e.dataTransfer.setData('application/json', JSON.stringify(payload));
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onAppointmentClick(appointment.id);
  };

  const ringClass = isOnSelectedDate
    ? 'ring-2 ring-red-500 ring-offset-1 animate-pulse'
    : '';

  // Variant-specific layout classes. Both share status-border + accent-left.
  const variantClass =
    variant === 'absolute'
      ? 'absolute rounded-md text-[11px] leading-tight overflow-hidden'
      : 'relative w-full rounded-md text-[11px] leading-tight';

  const inlineStyle: CSSProperties = {
    opacity,
    borderWidth: 2,
    borderStyle,
    borderColor: '#cbd5e1', // slate-300 baseline border
    borderLeftWidth: 4,
    ...style,
  };

  return (
    <div
      data-testid={`appt-card-${appointment.id}`}
      className={[
        variantClass,
        palette.bg,
        palette.border,
        'cursor-grab active:cursor-grabbing hover:shadow-sm transition-shadow',
        ringClass,
      ]
        .filter(Boolean)
        .join(' ')}
      style={inlineStyle}
      draggable
      onDragStart={handleDragStart}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onAppointmentClick(appointment.id);
        }
      }}
    >
      <div className="flex items-start gap-1 px-1.5 py-1">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1 text-[10px] text-slate-600">
            <span>
              {titlePrefix}
              {formatTimeRange(
                appointment.time_window_start,
                appointment.time_window_end
              )}
            </span>
          </div>
          <div
            className={`text-[12px] font-semibold truncate ${palette.text}`}
          >
            {appointment.job_type ?? 'Job'}
          </div>
          {customerLine && (
            <div className="text-[11px] text-slate-700 truncate">
              {customerLine}
            </div>
          )}
        </div>
        {isDraft ? (
          <SendConfirmationButton appointment={appointment} compact />
        ) : (
          iconsToRender.length > 0 && (
            <div
              className="flex items-center gap-0.5 shrink-0"
              data-testid={`card-icons-${appointment.id}`}
            >
              {iconsToRender.map((i) => i.el)}
            </div>
          )
        )}
      </div>
    </div>
  );
}
