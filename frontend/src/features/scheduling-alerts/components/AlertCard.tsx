/**
 * AlertCard — individual alert (red/critical) with one-click resolution actions.
 */

import type { SchedulingAlert } from '../types';
import { useResolveAlert } from '../hooks/useAlerts';

interface AlertCardProps {
  alert: SchedulingAlert;
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

const ALERT_TYPE_LABELS: Record<string, string> = {
  double_booking: 'Double-Booking Conflict',
  skill_mismatch: 'Skill Mismatch',
  sla_risk: 'SLA Deadline at Risk',
  resource_behind: 'Resource Running Behind',
  severe_weather: 'Severe Weather',
};

export function AlertCard({ alert }: AlertCardProps) {
  const resolveAlert = useResolveAlert();

  const handleResolve = (action: string, parameters?: Record<string, unknown>) => {
    resolveAlert.mutate({ id: alert.id, data: { action, parameters } });
  };

  const typeLabel = ALERT_TYPE_LABELS[alert.alert_type] ?? alert.alert_type;

  return (
    <div
      data-testid={`alert-card-${alert.id}`}
      className="rounded-lg border border-red-200 bg-red-50 p-3"
    >
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-semibold text-red-800">
          ⚠ ALERT — {typeLabel}
        </span>
        <span className="text-xs text-red-400">{formatTimestamp(alert.created_at)}</span>
      </div>

      <h4 className="mb-1 text-sm font-medium text-red-900">{alert.title}</h4>
      <p className="mb-3 text-xs text-red-700">{alert.description}</p>

      {alert.resolution_options.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {alert.resolution_options.map((option) => (
            <button
              key={option.action}
              onClick={() => handleResolve(option.action, option.parameters)}
              disabled={resolveAlert.isPending}
              className="rounded-md border border-red-300 bg-white px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-50"
              title={option.description}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
