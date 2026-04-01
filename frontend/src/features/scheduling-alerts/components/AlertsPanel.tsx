/**
 * AlertsPanel — main panel rendering below the Schedule Overview.
 * Polls alerts via GET /api/v1/alerts/ at 30s intervals.
 * Renders AlertCard (red) and SuggestionCard (green) in a scrollable list.
 */

import { useAlerts } from '../hooks/useAlerts';
import { AlertCard } from './AlertCard';
import { SuggestionCard } from './SuggestionCard';

interface AlertsPanelProps {
  scheduleDate?: string;
  refetchInterval?: number;
}

export function AlertsPanel({
  scheduleDate,
  refetchInterval = 30_000,
}: AlertsPanelProps) {
  const { data: alerts, isLoading, error } = useAlerts(
    { schedule_date: scheduleDate, status: 'active' },
    refetchInterval
  );

  const criticalAlerts = alerts?.filter((a) => a.severity === 'critical') ?? [];
  const suggestions = alerts?.filter((a) => a.severity === 'suggestion') ?? [];
  const totalCount = (alerts?.length ?? 0);

  return (
    <div data-testid="alerts-panel" className="rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-gray-200 px-4 py-3">
        <h3 className="text-base font-semibold text-gray-900">Alerts &amp; Suggestions</h3>
        <span
          data-testid="alerts-count-badge"
          className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700"
        >
          {totalCount} {totalCount === 1 ? 'alert' : 'alerts'}
        </span>
      </div>

      {/* Content */}
      <div className="max-h-[500px] overflow-y-auto p-4">
        {isLoading && (
          <p className="text-center text-sm text-gray-400">Loading alerts…</p>
        )}

        {error && (
          <p className="text-center text-sm text-red-500">
            Failed to load alerts. Retrying…
          </p>
        )}

        {!isLoading && !error && totalCount === 0 && (
          <p className="text-center text-sm text-gray-400">
            No active alerts or suggestions.
          </p>
        )}

        <div className="flex flex-col gap-3">
          {criticalAlerts.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
          {suggestions.map((suggestion) => (
            <SuggestionCard key={suggestion.id} suggestion={suggestion} />
          ))}
        </div>
      </div>
    </div>
  );
}
