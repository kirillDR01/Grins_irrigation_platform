/**
 * RecentlyClearedSection component.
 *
 * Displays recently cleared schedules from the last 24 hours.
 * Shows date, appointment count, timestamp, and view details action.
 *
 * Validates: Requirements 6.1-6.5
 */

import { useQuery } from '@tanstack/react-query';
import { format, formatDistanceToNow } from 'date-fns';
import { Clock, Eye, History } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

import { scheduleGenerationApi } from '../api/scheduleGenerationApi';
import type { ScheduleClearAuditResponse } from '../types';

interface RecentlyClearedSectionProps {
  /** Callback when view details is clicked */
  onViewDetails?: (auditId: string) => void;
}

/**
 * RecentlyClearedSection displays schedules cleared in the last 24 hours.
 */
export function RecentlyClearedSection({
  onViewDetails,
}: RecentlyClearedSectionProps) {
  const { data: recentClears, isLoading, error } = useQuery({
    queryKey: ['schedule', 'recent-clears'],
    queryFn: () => scheduleGenerationApi.getRecentClears(24),
    refetchInterval: 60000, // Refresh every minute
  });

  if (isLoading) {
    return (
      <Card data-testid="recently-cleared-section">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <History className="h-4 w-4" />
            Recently Cleared
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card data-testid="recently-cleared-section">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <History className="h-4 w-4" />
            Recently Cleared
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Failed to load recent clears
          </p>
        </CardContent>
      </Card>
    );
  }

  const hasClears = recentClears && recentClears.length > 0;

  return (
    <Card data-testid="recently-cleared-section">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <History className="h-4 w-4" />
          Recently Cleared
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!hasClears ? (
          <p
            className="text-sm text-muted-foreground"
            data-testid="recently-cleared-empty"
          >
            No schedules cleared in the last 24 hours
          </p>
        ) : (
          <div className="space-y-2" data-testid="recently-cleared-list">
            {recentClears.map((audit: ScheduleClearAuditResponse) => (
              <RecentClearItem
                key={audit.id}
                audit={audit}
                onViewDetails={onViewDetails}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface RecentClearItemProps {
  audit: ScheduleClearAuditResponse;
  onViewDetails?: (auditId: string) => void;
}

function RecentClearItem({ audit, onViewDetails }: RecentClearItemProps) {
  const formattedDate = format(new Date(audit.schedule_date), 'EEE, MMM d');
  const timeAgo = formatDistanceToNow(new Date(audit.cleared_at), {
    addSuffix: true,
  });

  return (
    <div
      className="flex items-center justify-between rounded-md border p-3"
      data-testid="recently-cleared-item"
    >
      <div className="flex flex-col gap-1">
        <span className="font-medium" data-testid="recently-cleared-date">
          {formattedDate}
        </span>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span data-testid="recently-cleared-count">
            {audit.appointment_count} appointment
            {audit.appointment_count !== 1 ? 's' : ''} cleared
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span data-testid="recently-cleared-time">{timeAgo}</span>
          </span>
        </div>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onViewDetails?.(audit.id)}
        data-testid="view-clear-details-btn"
      >
        <Eye className="mr-1 h-4 w-4" />
        Details
      </Button>
    </div>
  );
}

export default RecentlyClearedSection;
