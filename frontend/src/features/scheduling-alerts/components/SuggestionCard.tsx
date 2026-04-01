/**
 * SuggestionCard — individual suggestion (green) with accept/dismiss.
 */

import type { SchedulingAlert } from '../types';
import { useResolveAlert, useDismissAlert } from '../hooks/useAlerts';

interface SuggestionCardProps {
  suggestion: SchedulingAlert;
}

function formatTimestamp(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

const SUGGESTION_TYPE_LABELS: Record<string, string> = {
  route_swap: 'Route Swap',
  underutilized: 'Underutilized Resource',
  customer_preference: 'Customer Prefers Different Resource',
  overtime_avoidable: 'Overtime Avoidable',
  high_revenue: 'High-Revenue Job Available',
};

export function SuggestionCard({ suggestion }: SuggestionCardProps) {
  const resolveAlert = useResolveAlert();
  const dismissAlert = useDismissAlert();

  const handleAccept = (action: string, parameters?: Record<string, unknown>) => {
    resolveAlert.mutate({ id: suggestion.id, data: { action, parameters } });
  };

  const handleDismiss = () => {
    dismissAlert.mutate({ id: suggestion.id });
  };

  const typeLabel = SUGGESTION_TYPE_LABELS[suggestion.alert_type] ?? suggestion.alert_type;
  const isPending = resolveAlert.isPending || dismissAlert.isPending;

  return (
    <div
      data-testid={`suggestion-card-${suggestion.id}`}
      className="rounded-lg border border-green-200 bg-green-50 p-3"
    >
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-semibold text-green-800">
          💡 SUGGESTION — {typeLabel}
        </span>
        <span className="text-xs text-green-400">
          {formatTimestamp(suggestion.created_at)}
        </span>
      </div>

      <h4 className="mb-1 text-sm font-medium text-green-900">{suggestion.title}</h4>
      <p className="mb-3 text-xs text-green-700">{suggestion.description}</p>

      <div className="flex flex-wrap gap-2">
        {suggestion.resolution_options.map((option, idx) => (
          <button
            key={option.action}
            onClick={() => handleAccept(option.action, option.parameters)}
            disabled={isPending}
            className={
              idx === 0
                ? 'rounded-md bg-green-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50'
                : 'rounded-md border border-green-300 bg-white px-2.5 py-1 text-xs font-medium text-green-700 hover:bg-green-100 disabled:opacity-50'
            }
            title={option.description}
          >
            {option.label}
          </button>
        ))}
        <button
          onClick={handleDismiss}
          disabled={isPending}
          className="rounded-md border border-gray-300 bg-white px-2.5 py-1 text-xs font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
        >
          Leave as-is
        </button>
      </div>
    </div>
  );
}
