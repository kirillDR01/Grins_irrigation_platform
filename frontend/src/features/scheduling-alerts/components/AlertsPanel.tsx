import { useAlerts } from '../hooks/useAlerts';
import type { SchedulingAlert } from '../types';
import { AlertCard } from './AlertCard';
import { SuggestionCard } from './SuggestionCard';

interface AlertsPanelProps {
  scheduleDate?: string;
}

export function AlertsPanel({ scheduleDate }: AlertsPanelProps) {
  const { data: alerts = [], isLoading, error } = useAlerts(
    scheduleDate ? { schedule_date: scheduleDate } : undefined
  );

  const hardAlerts = alerts.filter((a) => a.severity !== 'suggestion');
  const suggestions = alerts.filter((a) => a.severity === 'suggestion');
  const totalCount = alerts.length;

  return (
    <div data-testid="alerts-panel" className="space-y-3">
      <div className="flex items-center gap-2">
        <h2 className="text-base font-semibold text-gray-900">
          Alerts &amp; Suggestions
        </h2>
        {totalCount > 0 && (
          <span
            data-testid="alerts-count-badge"
            className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold rounded-full bg-red-100 text-red-700"
          >
            {totalCount} {totalCount === 1 ? 'alert' : 'alerts'}
          </span>
        )}
      </div>

      {isLoading && (
        <p className="text-sm text-gray-500">Loading alerts…</p>
      )}

      {error && (
        <p className="text-sm text-red-600">Failed to load alerts.</p>
      )}

      {!isLoading && !error && totalCount === 0 && (
        <p className="text-sm text-gray-500">No active alerts or suggestions.</p>
      )}

      <div className="space-y-2">
        {hardAlerts.map((alert: SchedulingAlert) => (
          <AlertCard key={alert.id} alert={alert} />
        ))}
        {suggestions.map((alert: SchedulingAlert) => (
          <SuggestionCard key={alert.id} alert={alert} />
        ))}
      </div>
    </div>
  );
}
