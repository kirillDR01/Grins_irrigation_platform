import { AlertCircle } from 'lucide-react';
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
      {pick ? (
        <div
          data-testid="schedule-visit-pick-summary"
          className="mt-4 rounded-xl border border-slate-200 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.06)]"
        >
          <div className="mb-1.5 flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-300 bg-blue-100 px-2.5 py-0.5 text-[11.5px] font-bold uppercase tracking-tight text-blue-700">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-700" />
              Picked
            </span>
          </div>
          <div className="text-[15px] font-extrabold leading-tight tracking-tight text-slate-900">
            {fmtLongDate(pick.date)}
          </div>
          <div className="mt-0.5 font-mono text-[13px] font-semibold text-slate-800">
            {fmtHM(pick.start)} – {fmtHM(pick.end)}
          </div>
          <div className="mt-2 flex flex-wrap gap-2.5 border-t border-dashed border-slate-200 pt-2 text-[11.5px] text-slate-500">
            <span>
              <b className="font-semibold text-slate-800">Duration</b>{' '}
              <span className="font-bold text-slate-900">{fmtDur(pick.end - pick.start)}</span>
            </span>
          </div>
        </div>
      ) : (
        <div
          data-testid="schedule-visit-pick-summary"
          className="mt-4 flex items-center gap-2 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3.5 py-3 text-[12.5px] italic text-slate-500"
          style={{
            backgroundImage:
              'repeating-linear-gradient(135deg, transparent 0 6px, rgba(15,23,42,0.025) 6px 12px)',
          }}
        >
          No time picked yet — click or drag on the calendar →
        </div>
      )}

      {hasConflict && (
        <div
          role="alert"
          data-testid="schedule-visit-conflict-banner"
          className="mt-2.5 flex items-start gap-2.5 rounded-xl border border-red-300 bg-red-100 px-3 py-2.5 text-[12.5px] leading-snug text-red-900"
        >
          <AlertCircle size={16} strokeWidth={2.2} className="mt-0.5 flex-none text-red-700" />
          <span>
            <b className="font-bold text-red-700">Overlaps</b> with an existing estimate on
            the same day. You can still proceed, but double-check.
          </span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          data-testid="schedule-visit-error"
          className="mt-2.5 rounded-xl border border-red-300 bg-red-100 px-3 py-2.5 text-[12.5px] text-red-900"
        >
          {error}
        </div>
      )}
    </>
  );
}
