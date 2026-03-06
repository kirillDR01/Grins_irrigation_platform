import { memo } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/shared/utils/cn';
import { useSyncStatus } from '../hooks/useWorkRequests';

export const SyncStatusBar = memo(function SyncStatusBar() {
  const { data: status } = useSyncStatus();

  if (!status) return null;

  return (
    <div
      className="flex items-center gap-2 text-sm text-muted-foreground"
      data-testid="sync-status-bar"
    >
      <span
        className={cn(
          'inline-block h-2 w-2 rounded-full',
          status.is_running ? 'bg-green-500' : 'bg-gray-400'
        )}
        data-testid="sync-status-indicator"
      />
      <span data-testid="sync-status-text">
        {status.is_running ? 'Syncing' : 'Stopped'}
      </span>
      {status.last_sync && (
        <span data-testid="sync-last-time">
          · Last sync {formatDistanceToNow(new Date(status.last_sync), { addSuffix: true })}
        </span>
      )}
      {status.last_error && (
        <span className="text-red-600" data-testid="sync-error">
          · {status.last_error}
        </span>
      )}
    </div>
  );
});
