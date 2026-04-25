import { useEffect } from 'react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
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
    // On failure, error is shown inline via PickSummary; modal stays open.
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
  const confirmLabel = s.isReschedule
    ? '📅 Update appointment'
    : '📅 Confirm & advance to Send Estimate';

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        data-testid="schedule-visit-modal"
        className="sm:max-w-[960px]"
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Auto-populated from the lead record. Pick a time on the calendar —
            click a slot for a start time, or drag to set both start &amp;
            duration.
          </DialogDescription>
        </DialogHeader>

        {/* Mobile (<720px): customer card → calendar → fields, in that order (SPEC §2). */}
        <div className="grid grid-cols-1 md:grid-cols-[340px_1fr] gap-[18px] items-start">
          <div className="min-w-0 order-1 md:order-1">
            <PrefilledCustomerCard entry={entry} />
          </div>
          <div className="min-w-0 order-2 md:row-span-2 md:order-2">
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
          <div className="min-w-0 order-3 md:order-3">
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
        </div>

        <DialogFooter className="mt-4">
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
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
