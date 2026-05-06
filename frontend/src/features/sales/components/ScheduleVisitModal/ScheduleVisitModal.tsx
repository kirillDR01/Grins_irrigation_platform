import { useEffect } from 'react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ArrowRight, X } from 'lucide-react';
import { track } from '@/shared/utils/track';
import { useScheduleVisit } from '../../hooks/useScheduleVisit';
import { PrefilledCustomerCard } from './PrefilledCustomerCard';
import { ScheduleFields } from './ScheduleFields';
import { WeekCalendar } from './WeekCalendar';
import { PickSummary } from './PickSummary';
import {
  fmtLongDate,
  fmtHM,
  formatShortName,
} from '../../lib/scheduleVisitUtils';
import { SALES_STATUS_CONFIG } from '../../types/pipeline';
import type { SalesEntry, SalesCalendarEvent } from '../../types/pipeline';

type Props = {
  entry: SalesEntry;
  /** Most recent event for this entry (for reschedule). Pass null for new bookings. */
  currentEvent: SalesCalendarEvent | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Optional default for the assignee dropdown. */
  defaultAssigneeId?: string | null;
};

export function ScheduleVisitModal({
  entry,
  currentEvent,
  open,
  onOpenChange,
  defaultAssigneeId,
}: Props) {
  const customerName = entry.customer_name ?? 'Unknown Customer';
  const jobSummary = entry.job_type ?? '';
  const s = useScheduleVisit({
    entry,
    customerId: entry.customer_id,
    customerName,
    jobSummary,
    currentEvent,
    defaultAssigneeId,
  });

  useEffect(() => {
    if (open)
      track('sales.schedule_visit.opened', {
        entryId: entry.id,
        status: entry.status,
      });
  }, [open, entry.id, entry.status]);

  const handleConfirm = async () => {
    const result = await s.submit();
    if (result.ok) {
      track('sales.schedule_visit.confirmed', { entryId: entry.id });
      toast.success(
        s.pick
          ? `Visit scheduled for ${fmtLongDate(s.pick.date)}, ${fmtHM(s.pick.start)}`
          : 'Scheduled',
      );
      onOpenChange(false);
    }
  };

  const handleOpenChange = (next: boolean) => {
    if (!next && s.isDirty) {
      const ok = window.confirm('Discard unsaved changes?');
      if (!ok) return;
      track('sales.schedule_visit.cancelled', {
        entryId: entry.id,
        dirty: true,
      });
    } else if (!next) {
      track('sales.schedule_visit.cancelled', {
        entryId: entry.id,
        dirty: false,
      });
    }
    onOpenChange(next);
  };

  const title = s.isReschedule
    ? 'Reschedule estimate visit'
    : 'Schedule estimate visit';
  const stageLabel = `Stage 1 · ${SALES_STATUS_CONFIG[entry.status].label}`;
  const idLabel = `SAL-${entry.id.slice(0, 4).toUpperCase()}`;
  const showLeadTag = !!entry.lead_id;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        data-testid="schedule-visit-modal"
        showCloseButton={false}
        className="sm:max-w-[1024px] p-0 rounded-[18px] border border-slate-200"
      >
        <header className="flex items-start gap-4 px-6 py-5 border-b border-slate-200 bg-white">
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-orange-300 bg-orange-100 px-2.5 py-0.5 text-[11.5px] font-bold leading-tight tracking-tight text-orange-700">
                <span className="h-1.5 w-1.5 rounded-full bg-orange-700" />
                {stageLabel}
              </span>
              <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-2.5 py-0.5 font-mono text-[11.5px] font-semibold tracking-tight text-slate-800">
                {idLabel}
              </span>
              {showLeadTag && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-100 px-2.5 py-0.5 text-[11.5px] font-bold leading-tight tracking-tight text-emerald-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-700" />
                  From lead
                </span>
              )}
            </div>
            <DialogTitle asChild>
              <h2 className="m-0 text-[22px] font-extrabold leading-[1.15] tracking-tight text-slate-900">
                {title}
              </h2>
            </DialogTitle>
            <DialogDescription asChild>
              <p className="mt-1 max-w-[680px] text-[13.5px] leading-relaxed text-slate-600">
                Customer details are pre-filled from the lead record. Pick a time on the
                calendar — click a slot to pin a start, or drag to set both start &amp;
                duration.
              </p>
            </DialogDescription>
          </div>
          <button
            type="button"
            onClick={() => handleOpenChange(false)}
            aria-label="Close"
            data-testid="close-modal-btn"
            className="inline-flex h-9 w-9 flex-none items-center justify-center rounded-[10px] border border-slate-200 bg-white text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900"
          >
            <X size={18} strokeWidth={2} />
          </button>
        </header>

        {/* Body — desktop two-col, mobile stack (customer → calendar → fields). */}
        <div className="grid grid-cols-1 md:grid-cols-[360px_1fr] items-stretch">
          <div className="order-1 min-w-0 border-slate-200 bg-slate-50 px-6 py-5 md:border-r">
            <PrefilledCustomerCard entry={entry} />
            <ScheduleFields
              pick={s.pick}
              durationMin={s.durationMin}
              assignedToUserId={s.assignedToUserId}
              internalNotes={s.internalNotes}
              onDateChange={s.setPickDate}
              onStartChange={s.setPickStart}
              onDurationChange={s.setPickDuration}
              onAssigneeChange={s.setAssignedToUserId}
              onNotesChange={s.setInternalNotes}
            />
            <PickSummary
              pick={s.pick}
              hasConflict={s.hasConflict}
              error={s.error}
            />
          </div>

          <div className="order-2 min-w-0 bg-white px-6 py-5">
            <WeekCalendar
              weekStart={s.weekStart}
              now={s.now}
              estimates={s.estimates}
              pick={s.pick}
              loadingWeek={s.loadingWeek}
              conflicts={s.conflicts}
              hasConflict={s.hasConflict}
              pickCustomerName={formatShortName(customerName)}
              onWeekChange={s.setWeekStart}
              onSlotClick={s.setPickFromCalendarClick}
              onSlotDrag={s.setPickFromCalendarDrag}
              onTrack={(_e, source) =>
                track('sales.schedule_visit.pick', {
                  entryId: entry.id,
                  source,
                })
              }
            />
          </div>
        </div>

        <DialogFooter className="border-t border-slate-200 bg-slate-50 px-6 py-4">
          <Button
            variant="ghost"
            onClick={() => handleOpenChange(false)}
            data-testid="schedule-visit-cancel-btn"
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!s.pick || s.submitting}
            data-testid="schedule-visit-confirm-btn"
            className="bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-100 disabled:bg-slate-300 disabled:text-white shadow-[0_1px_0_rgba(0,0,0,0.1),0_4px_8px_rgba(15,23,42,0.16)]"
          >
            {s.isReschedule ? (
              <>
                Update &amp; resend confirmation text
                <ArrowRight className="size-3.5" strokeWidth={2.5} aria-hidden="true" />
              </>
            ) : (
              <>
                Send confirmation text message
                <ArrowRight className="size-3.5" strokeWidth={2.5} aria-hidden="true" />
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
