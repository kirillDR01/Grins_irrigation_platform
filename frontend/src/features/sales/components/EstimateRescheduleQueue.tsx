/**
 * EstimateRescheduleQueue — the sales-pipeline parallel of
 * ``RescheduleRequestsQueue``. Surfaces open R-replies on estimate
 * visits so the sales coordinator can act on them.
 *
 * Validates: sales-pipeline-estimate-visit-confirmation-lifecycle (OQ-2).
 */

import { useState } from 'react';
import { CalendarClock, Check, RefreshCw } from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { getErrorMessage } from '@/core/api/client';
import {
  useEstimateRescheduleRequests,
  useResolveEstimateReschedule,
} from '../hooks/useEstimateRescheduleRequests';

export function EstimateRescheduleQueue() {
  const { data: requests, isLoading, error } = useEstimateRescheduleRequests('open');
  const resolveMutation = useResolveEstimateReschedule();
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div
        className="bg-slate-50 rounded-xl p-4 border border-slate-100"
        data-testid="estimate-reschedule-queue"
      >
        <div className="flex items-center gap-2 mb-3">
          <CalendarClock className="h-4 w-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-slate-700">
            Estimate Reschedule Requests
          </h3>
        </div>
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="bg-red-50 rounded-xl p-4 border border-red-100"
        data-testid="estimate-reschedule-queue"
      >
        <p className="text-sm text-red-700">
          Could not load estimate reschedule requests: {getErrorMessage(error)}
        </p>
      </div>
    );
  }

  if (!requests || requests.length === 0) {
    // Mirror of the schedule-tab queue: render nothing when there are no
    // open requests so the page doesn't accumulate empty headers.
    return null;
  }

  const handleResolve = async (id: string) => {
    setResolvingId(id);
    try {
      await resolveMutation.mutateAsync(id);
      toast.success('Reschedule request resolved');
    } catch (err) {
      toast.error('Failed to resolve', {
        description: getErrorMessage(err),
      });
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div
      className="bg-amber-50 rounded-xl p-4 border border-amber-100"
      data-testid="estimate-reschedule-queue"
    >
      <div className="flex items-center gap-2 mb-3">
        <CalendarClock className="h-4 w-4 text-amber-600" />
        <h3 className="text-sm font-semibold text-slate-800">
          Estimate Reschedule Requests ({requests.length})
        </h3>
      </div>
      <div className="space-y-2">
        {requests.map((req) => (
          <div
            key={req.id}
            className="bg-white rounded-lg p-3 border border-slate-200"
            data-testid={`estimate-reschedule-card-${req.id}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-slate-900">
                  {req.customer_name || 'Unknown customer'}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {req.original_appointment_date
                    ? `Original: ${format(new Date(req.original_appointment_date + 'T12:00'), 'MMM d, yyyy')}`
                    : 'Original date unknown'}
                  {' · '}
                  {formatDistanceToNow(new Date(req.created_at), { addSuffix: true })}
                </p>
                {req.raw_alternatives_text && (
                  <p
                    className="text-xs text-slate-700 mt-2 whitespace-pre-line"
                    data-testid={`estimate-reschedule-alternatives-${req.id}`}
                  >
                    <span className="font-medium">Customer suggested:</span>{' '}
                    {req.raw_alternatives_text}
                  </p>
                )}
              </div>
              <div className="flex flex-col gap-1">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={resolvingId === req.id}
                  onClick={() => handleResolve(req.id)}
                  data-testid={`estimate-reschedule-resolve-${req.id}`}
                >
                  {resolvingId === req.id ? (
                    <RefreshCw className="h-3 w-3 animate-spin" />
                  ) : (
                    <Check className="h-3 w-3" />
                  )}
                  <span className="ml-1">Resolve</span>
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
