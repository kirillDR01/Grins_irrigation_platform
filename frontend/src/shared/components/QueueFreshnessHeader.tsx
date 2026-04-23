/**
 * QueueFreshnessHeader — shared header block for admin queues that
 * surface inbound customer replies. Shows a title + optional count badge,
 * a "Updated X ago" relative-time label backed by TanStack's
 * ``dataUpdatedAt`` timestamp, and a manual refresh button that triggers
 * an invalidation of the owning query key.
 *
 * Ticks every 15 s to keep the relative-time label live independent of
 * the query's own ``refetchInterval``.
 *
 * Validates: Gap 15 (Phase 2) — queue freshness UX.
 */

import { useEffect, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export interface QueueFreshnessHeaderProps {
  icon: React.ReactNode;
  title: string;
  badgeCount?: number;
  badgeClassName?: string;
  dataUpdatedAt: number;
  isRefetching: boolean;
  onRefresh: () => void;
  testId?: string;
}

export function QueueFreshnessHeader({
  icon,
  title,
  badgeCount,
  badgeClassName,
  dataUpdatedAt,
  isRefetching,
  onRefresh,
  testId,
}: QueueFreshnessHeaderProps) {
  // Force a re-render every 15 s so the relative-time label stays live
  // even when TanStack hasn't refetched.
  const [, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 15_000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        {icon}
        <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
        {typeof badgeCount === 'number' && badgeCount > 0 && (
          <Badge
            variant="secondary"
            className={badgeClassName}
          >
            {badgeCount}
          </Badge>
        )}
      </div>
      <div className="flex items-center gap-2">
        <span
          className="text-xs text-slate-400"
          data-testid="queue-last-updated"
        >
          {dataUpdatedAt > 0
            ? `Updated ${formatDistanceToNow(new Date(dataUpdatedAt), { addSuffix: true })}`
            : 'Updating…'}
        </span>
        <Button
          size="sm"
          variant="ghost"
          className="h-7 w-7 p-0"
          onClick={onRefresh}
          disabled={isRefetching}
          data-testid={testId ?? 'queue-refresh-btn'}
          aria-label="Refresh queue"
        >
          <RefreshCw
            className={cn('h-3 w-3', isRefetching && 'animate-spin')}
          />
        </Button>
      </div>
    </div>
  );
}
