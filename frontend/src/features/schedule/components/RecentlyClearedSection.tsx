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
import { Clock } from 'lucide-react';

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
      <div className="bg-slate-50 rounded-xl p-4 border border-slate-100" data-testid="recently-cleared-section">
        <div className="flex items-center gap-2 mb-3">
          <Clock className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-700">Recently Cleared</h3>
        </div>
        <div className="space-y-2">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-50 rounded-xl p-4 border border-slate-100" data-testid="recently-cleared-section">
        <div className="flex items-center gap-2 mb-3">
          <Clock className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-700">Recently Cleared</h3>
        </div>
        <p className="text-sm text-slate-400">
          Failed to load recent clears
        </p>
      </div>
    );
  }

  const hasClears = recentClears && recentClears.length > 0;

  return (
    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100" data-testid="recently-cleared-section">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-700">Recently Cleared</h3>
        </div>
        {hasClears && (
          <button
            className="text-slate-400 hover:text-slate-600 text-sm"
            onClick={() => {/* TODO: Implement clear all */}}
            data-testid="clear-all-btn"
          >
            Clear All
          </button>
        )}
      </div>
      {!hasClears ? (
        <p
          className="text-sm text-slate-400"
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
    </div>
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
      className="flex items-center justify-between p-2 bg-white rounded-lg"
      data-testid="recently-cleared-item"
    >
      <div className="flex flex-col gap-1">
        <span className="font-medium text-slate-700" data-testid="recently-cleared-date">
          {formattedDate}
        </span>
        <div className="flex items-center gap-2 text-sm text-slate-500">
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
      <button
        className="text-teal-600 hover:text-teal-700 text-sm font-medium"
        onClick={() => onViewDetails?.(audit.id)}
        data-testid="restore-job-btn"
      >
        Restore
      </button>
    </div>
  );
}

export default RecentlyClearedSection;
