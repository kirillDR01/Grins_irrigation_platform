// ScheduleVisitModal.tsx
// Top-level scaffold. Uses the app's existing <Modal> + <Button> components.
// Composition only — all state lives in `useScheduleVisit`.
//
// See SPEC.md for behavior. See reference/ for visual ground truth.

import React from 'react';
import type { ScheduleVisitModalProps } from './data-shapes';
import { useScheduleVisit } from './useScheduleVisit';
import { PrefilledCustomerCard } from './PrefilledCustomerCard';
import { ScheduleFields } from './ScheduleFields';
import { WeekCalendar } from './WeekCalendar';
// import { Modal, Button } from '@/components';   // <- app components

export function ScheduleVisitModal({
  entry,
  onScheduled,
  onClose,
  defaultAssigneeId = 'me',
  now = new Date(),
}: ScheduleVisitModalProps) {
  const s = useScheduleVisit({ entry, defaultAssigneeId, now });

  const isReschedule = entry.status === 'estimate_scheduled';
  const title = isReschedule
    ? 'Reschedule estimate visit'
    : 'Schedule estimate visit';

  const handleConfirm = async () => {
    const updated = await s.submit();
    if (updated) onScheduled(updated);
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={title}
      subtitle="Auto-populated from the lead record. Pick a time on the calendar — click a slot for a start time, or drag to set both start & duration."
      width={960}
    >
      <div className="grid grid-cols-[340px_1fr] gap-[18px] items-start max-md:grid-cols-1">
        {/* LEFT */}
        <div className="min-w-0 max-md:order-3">
          <PrefilledCustomerCard customer={entry.customer} />
          <ScheduleFields
            pick={s.pick}
            durationMin={s.durationMin}
            assignedTo={s.assignedTo}
            internalNotes={s.internalNotes}
            onDateChange={s.setPickDate}
            onStartChange={s.setPickStart}
            onDurationChange={s.setPickDuration}
            onAssigneeChange={s.setAssignedTo}
            onNotesChange={s.setInternalNotes}
          />
          <PickSummary pick={s.pick} hasConflict={s.hasConflict} />
        </div>

        {/* RIGHT */}
        <div className="min-w-0 max-md:order-2">
          <WeekCalendar
            weekStart={s.weekStart}
            now={now}
            estimates={s.estimates}
            pick={s.pick}
            loadingWeek={s.loadingWeek}
            conflicts={s.conflicts}
            onWeekChange={s.setWeekStart}
            onSlotClick={s.setPickFromCalendarClick}
            onSlotDrag={s.setPickFromCalendarDrag}
          />
        </div>
      </div>

      {s.error ? <div role="alert" className="error-row">{s.error}</div> : null}

      <div className="m-actions">
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button
          variant="primary"
          disabled={!s.pick || s.submitting}
          onClick={handleConfirm}
        >
          {isReschedule
            ? '📅 Update appointment'
            : '📅 Confirm & advance to Send Estimate'}
        </Button>
      </div>
    </Modal>
  );
}

// ----------------------------------------------------------------------------
// Tiny in-file pieces that aren't worth their own files.

function PickSummary({
  pick,
  hasConflict,
}: {
  pick: ReturnType<typeof useScheduleVisit>['pick'];
  hasConflict: boolean;
}) {
  if (!pick) {
    return (
      <div className="pick-summary">
        <span className="none">No time picked yet — click or drag on the calendar →</span>
      </div>
    );
  }
  return (
    <>
      <div className="pick-summary">
        <strong>{fmtLongDate(pick.date)}</strong> · {fmtHM(pick.start)} – {fmtHM(pick.end)} ·{' '}
        <strong>{fmtDur(pick.end - pick.start)}</strong>
      </div>
      {hasConflict ? (
        <div role="alert" className="conflict-warn on">
          ⚠ <strong>Overlaps</strong> with an existing estimate. You can still proceed,
          but double-check.
        </div>
      ) : null}
    </>
  );
}

// ---- TEMP placeholders for app components. Delete on integration. ----
const Modal: React.FC<any> = ({ children }) => <div>{children}</div>;
const Button: React.FC<any> = (p) => <button {...p} />;

// ---- formatters (or import from a shared util) ----
function fmtHM(mins: number) {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  const ap = h >= 12 ? 'PM' : 'AM';
  const h12 = ((h + 11) % 12) + 1;
  return `${h12}:${String(m).padStart(2, '0')} ${ap}`;
}
function fmtDur(mins: number) {
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m === 0 ? `${h} hr` : `${h}h ${m}m`;
}
function fmtLongDate(iso: string) {
  return new Date(iso + 'T12:00').toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
