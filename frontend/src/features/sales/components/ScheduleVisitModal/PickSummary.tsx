import type { Pick } from '../../types/pipeline';
import { fmtHM, fmtDur, fmtLongDate } from '../../lib/scheduleVisitUtils';

type Props = {
  pick: Pick | null;
  hasConflict: boolean;
  error: string | null;
};

export function PickSummary({ pick, hasConflict, error }: Props) {
  return (
    <>
      <div
        data-testid="schedule-visit-pick-summary"
        className="mt-2 rounded border border-dashed border-amber-500 bg-amber-50 px-2.5 py-2 text-sm"
      >
        {pick ? (
          <>
            <strong>{fmtLongDate(pick.date)}</strong> · {fmtHM(pick.start)} –{' '}
            {fmtHM(pick.end)} ·{' '}
            <strong>{fmtDur(pick.end - pick.start)}</strong>
          </>
        ) : (
          <span className="italic text-slate-500">
            No time picked yet — click or drag on the calendar →
          </span>
        )}
      </div>
      {hasConflict && (
        <div
          role="alert"
          data-testid="schedule-visit-conflict-banner"
          className="mt-2 rounded border border-red-500 bg-red-50 px-2.5 py-2 text-sm text-red-900"
        >
          ⚠ <strong>Overlaps</strong> with an existing estimate. You can still
          proceed, but double-check.
        </div>
      )}
      {error && (
        <div
          role="alert"
          data-testid="schedule-visit-error"
          className="mt-2 rounded border border-red-500 bg-red-50 px-2.5 py-2 text-sm text-red-900"
        >
          {error}
        </div>
      )}
    </>
  );
}
