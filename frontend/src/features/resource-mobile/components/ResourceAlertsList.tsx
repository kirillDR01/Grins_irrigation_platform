/**
 * ResourceAlertsList — Mobile alerts for field resources.
 * Shows job changes, route resequencing, special equipment, and customer access alerts.
 */

import type { ResourceAlert } from '../types';

interface Props {
  alerts: ResourceAlert[];
  onDismiss: (alertId: string) => void;
}

const ALERT_ICONS: Record<string, string> = {
  job_added: '➕',
  job_removed: '➖',
  route_resequenced: '🔄',
  special_equipment: '🔧',
  customer_access: '🔑',
};

const ALERT_LABELS: Record<string, string> = {
  job_added: 'Job Added',
  job_removed: 'Job Removed',
  route_resequenced: 'Route Updated',
  special_equipment: 'Special Equipment',
  customer_access: 'Access Info',
};

export function ResourceAlertsList({ alerts, onDismiss }: Props) {
  return (
    <div data-testid="resource-alerts-list" className="flex flex-col gap-2 p-4">
      <h3 className="text-sm font-semibold text-gray-700">Alerts</h3>

      {alerts.length === 0 ? (
        <p className="text-sm text-gray-400 py-2">No alerts.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {alerts.map((alert) => (
            <li
              key={alert.id}
              data-testid={`resource-alert-${alert.id}`}
              className="bg-red-50 border border-red-200 rounded-xl p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2">
                  <span className="text-base" aria-hidden="true">
                    {ALERT_ICONS[alert.type] ?? '⚠️'}
                  </span>
                  <div>
                    <p className="text-xs font-semibold text-red-800">
                      {ALERT_LABELS[alert.type] ?? alert.type}
                    </p>
                    <p className="text-sm font-medium text-gray-900">{alert.title}</p>
                    <p className="text-xs text-gray-600 mt-0.5">{alert.description}</p>
                  </div>
                </div>
                <button
                  onClick={() => onDismiss(alert.id)}
                  className="flex-shrink-0 text-xs text-gray-400 hover:text-gray-600 transition-colors"
                  aria-label={`Dismiss alert: ${alert.title}`}
                >
                  ✕
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
