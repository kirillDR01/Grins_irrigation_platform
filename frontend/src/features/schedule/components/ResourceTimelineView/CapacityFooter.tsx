/**
 * CapacityFooter — per-day capacity bar at the bottom of week mode.
 *
 * Color thresholds: orange ≥85%, teal otherwise. While the per-day
 * capacity query is loading, the cell renders a pulsing slate skeleton
 * rather than 0%, which would lie about the data state.
 */

export interface CapacityFooterProps {
  date: string;
  /** null while the per-day capacity query is loading. */
  capacityPct: number | null;
}

export function CapacityFooter({ date, capacityPct }: CapacityFooterProps) {
  if (capacityPct === null) {
    return (
      <div
        data-testid={`capacity-${date}`}
        className="h-6 bg-slate-100 rounded animate-pulse"
        aria-label="Capacity loading"
      />
    );
  }

  const pct = Math.max(0, Math.min(100, capacityPct));
  const isHigh = pct >= 85;
  const barColor = isHigh ? 'bg-orange-500' : 'bg-teal-500';
  const labelColor = isHigh ? 'text-orange-700' : 'text-teal-700';

  return (
    <div
      data-testid={`capacity-${date}`}
      className="flex items-center gap-1 px-1"
    >
      <div className="flex-1 h-2 bg-slate-100 rounded overflow-hidden">
        <div
          className={`h-full ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-[10px] font-semibold tabular-nums ${labelColor}`}>
        {Math.round(pct)}%
      </span>
    </div>
  );
}
