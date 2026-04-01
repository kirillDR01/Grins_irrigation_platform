/**
 * ResourceAlertsList Component
 *
 * Mobile alerts for the Resource role: job added/removed,
 * route resequenced, special equipment, customer access.
 */

import {
  Plus,
  Minus,
  ArrowUpDown,
  Wrench,
  Key,
  CheckCircle2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useResourceAlerts, useMarkAlertRead } from '../hooks/useResourceSchedule';
import type { ResourceAlert, ResourceAlertType } from '../types';

// ── Alert type config ──────────────────────────────────────────────────

const ALERT_CONFIG: Record<
  ResourceAlertType,
  { icon: typeof Plus; color: string; bg: string }
> = {
  job_added: { icon: Plus, color: 'text-green-600', bg: 'bg-green-50' },
  job_removed: { icon: Minus, color: 'text-red-600', bg: 'bg-red-50' },
  route_resequenced: {
    icon: ArrowUpDown,
    color: 'text-blue-600',
    bg: 'bg-blue-50',
  },
  special_equipment: {
    icon: Wrench,
    color: 'text-amber-600',
    bg: 'bg-amber-50',
  },
  customer_access: { icon: Key, color: 'text-purple-600', bg: 'bg-purple-50' },
};

// ── Single alert card ──────────────────────────────────────────────────

function AlertItem({
  alert,
  onMarkRead,
}: {
  alert: ResourceAlert;
  onMarkRead: (id: string) => void;
}) {
  const config = ALERT_CONFIG[alert.alert_type] ?? ALERT_CONFIG.job_added;
  const Icon = config.icon;

  return (
    <div
      className={`rounded-xl border p-3 space-y-1.5 ${
        alert.is_read
          ? 'border-slate-100 bg-white opacity-60'
          : `border-slate-200 ${config.bg}`
      }`}
      data-testid={`resource-alert-${alert.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 flex-shrink-0 ${config.color}`} />
          <span className="font-medium text-slate-800 text-sm">
            {alert.title}
          </span>
        </div>
        {!alert.is_read && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-slate-400 hover:text-teal-500"
            onClick={() => onMarkRead(alert.id)}
            aria-label="Mark as read"
          >
            <CheckCircle2 className="h-4 w-4" />
          </Button>
        )}
      </div>
      <p className="text-xs text-slate-600 ml-6">{alert.description}</p>
      <p className="text-xs text-slate-400 ml-6">
        {new Date(alert.created_at).toLocaleTimeString()}
      </p>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────

export function ResourceAlertsList() {
  const { data: alerts, isLoading, error } = useResourceAlerts();
  const markRead = useMarkAlertRead();

  if (isLoading) {
    return (
      <div
        className="p-4 text-center text-slate-400 text-sm"
        data-testid="resource-alerts-list"
      >
        Loading alerts…
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="p-4 text-center text-red-500 text-sm"
        data-testid="resource-alerts-list"
      >
        Failed to load alerts
      </div>
    );
  }

  const items = alerts ?? [];
  const unreadCount = items.filter((a) => !a.is_read).length;

  return (
    <div className="space-y-3 p-4" data-testid="resource-alerts-list">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-slate-800">Alerts</h3>
        {unreadCount > 0 && (
          <span className="rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs font-medium">
            {unreadCount} new
          </span>
        )}
      </div>

      {items.length === 0 ? (
        <p className="text-center text-slate-400 text-sm py-6">
          No alerts right now
        </p>
      ) : (
        <div className="space-y-2">
          {items.map((alert) => (
            <AlertItem
              key={alert.id}
              alert={alert}
              onMarkRead={(id) => markRead.mutate(id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
