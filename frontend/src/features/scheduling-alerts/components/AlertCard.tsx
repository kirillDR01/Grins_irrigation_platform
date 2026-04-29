import { formatDistanceToNow } from 'date-fns';
import type { ResolutionOption, SchedulingAlert } from '../types';
import { useResolveAlert } from '../hooks/useAlerts';

interface AlertCardProps {
  alert: SchedulingAlert;
}

export function AlertCard({ alert }: AlertCardProps) {
  const resolve = useResolveAlert();

  const handleAction = (option: ResolutionOption) => {
    resolve.mutate({
      id: alert.id,
      action: option.action,
      parameters: option.parameters,
    });
  };

  const timeAgo = formatDistanceToNow(new Date(alert.created_at), {
    addSuffix: true,
  });

  return (
    <div
      data-testid={`alert-card-${alert.id}`}
      className="border-l-4 border-red-500 bg-red-50 rounded-r-lg p-4 space-y-2"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-red-700 uppercase tracking-wide">
          ⚠ ALERT — {alert.alert_type.replace(/_/g, ' ')}
        </span>
        <span className="text-xs text-gray-500">{timeAgo}</span>
      </div>
      <p className="text-sm font-medium text-gray-900">{alert.title}</p>
      <p className="text-sm text-gray-600">{alert.description}</p>
      {alert.resolution_options.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {alert.resolution_options.map((option) => (
            <button
              key={option.action}
              onClick={() => handleAction(option)}
              disabled={resolve.isPending}
              className="px-3 py-1 text-xs font-medium rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
