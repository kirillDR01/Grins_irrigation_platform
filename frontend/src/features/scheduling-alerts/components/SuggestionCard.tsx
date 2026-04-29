import { formatDistanceToNow } from 'date-fns';
import type { ResolutionOption, SchedulingAlert } from '../types';
import { useDismissAlert, useResolveAlert } from '../hooks/useAlerts';

interface SuggestionCardProps {
  alert: SchedulingAlert;
}

export function SuggestionCard({ alert }: SuggestionCardProps) {
  const resolve = useResolveAlert();
  const dismiss = useDismissAlert();

  const handleAccept = (option: ResolutionOption) => {
    resolve.mutate({
      id: alert.id,
      action: option.action,
      parameters: option.parameters,
    });
  };

  const handleDismiss = () => {
    dismiss.mutate({ id: alert.id });
  };

  const timeAgo = formatDistanceToNow(new Date(alert.created_at), {
    addSuffix: true,
  });

  const primaryOption = alert.resolution_options[0];
  const secondaryOptions = alert.resolution_options.slice(1);

  return (
    <div
      data-testid={`suggestion-card-${alert.id}`}
      className="border-l-4 border-green-500 bg-green-50 rounded-r-lg p-4 space-y-2"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-green-700 uppercase tracking-wide">
          💡 SUGGESTION — {alert.alert_type.replace(/_/g, ' ')}
        </span>
        <span className="text-xs text-gray-500">{timeAgo}</span>
      </div>
      <p className="text-sm font-medium text-gray-900">{alert.title}</p>
      <p className="text-sm text-gray-600">{alert.description}</p>
      <div className="flex flex-wrap gap-2 pt-1">
        {primaryOption && (
          <button
            onClick={() => handleAccept(primaryOption)}
            disabled={resolve.isPending}
            className="px-3 py-1 text-xs font-medium rounded-md bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
          >
            {primaryOption.label}
          </button>
        )}
        {secondaryOptions.map((option) => (
          <button
            key={option.action}
            onClick={() => handleAccept(option)}
            disabled={resolve.isPending}
            className="px-3 py-1 text-xs font-medium rounded-md bg-white border border-green-600 text-green-700 hover:bg-green-50 disabled:opacity-50"
          >
            {option.label}
          </button>
        ))}
        <button
          onClick={handleDismiss}
          disabled={dismiss.isPending}
          className="px-3 py-1 text-xs font-medium rounded-md bg-white border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50"
        >
          Leave as-is
        </button>
      </div>
    </div>
  );
}
