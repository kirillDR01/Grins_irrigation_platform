/**
 * RescheduleRequestsQueue component.
 * Admin queue showing customer reschedule requests from Y/R/C flow.
 *
 * Validates: CRM Changes Update 2 Req 25.1, 25.2, 25.3, 25.4
 */

import { useState } from 'react';
import { formatDistanceToNow, format } from 'date-fns';
import { toast } from 'sonner';
import { CalendarClock, Check, RefreshCw } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { getErrorMessage } from '@/core/api/client';
import { AppointmentForm } from './AppointmentForm';
import { useAppointment } from '../hooks/useAppointments';
import { useRescheduleFromRequest } from '../hooks/useAppointmentMutations';
import {
  useRescheduleRequests,
  useResolveRescheduleRequest,
  rescheduleKeys,
} from '../hooks/useRescheduleRequests';
import type { RescheduleRequestDetail } from '../types';
import { OptOutBadge, QueueFreshnessHeader } from '@/shared/components';

interface RescheduleRequestsQueueProps {
  onAppointmentClick?: (appointmentId: string) => void;
}

export function RescheduleRequestsQueue({
  onAppointmentClick,
}: RescheduleRequestsQueueProps) {
  const {
    data: requests,
    isLoading,
    error,
    dataUpdatedAt,
    isFetching,
  } = useRescheduleRequests('open');
  const queryClient = useQueryClient();
  const resolveMutation = useResolveRescheduleRequest();
  const rescheduleFromRequestMutation = useRescheduleFromRequest();
  const [rescheduleTarget, setRescheduleTarget] =
    useState<RescheduleRequestDetail | null>(null);

  // Fetch the appointment for the reschedule dialog
  const { data: targetAppointment } = useAppointment(rescheduleTarget?.appointment_id);

  const handleResolve = async (id: string) => {
    try {
      await resolveMutation.mutateAsync({ id });
      toast.success('Request resolved');
    } catch {
      toast.error('Failed to resolve request');
    }
  };

  const handleRescheduleSuccess = () => {
    if (rescheduleTarget) {
      resolveMutation.mutate({ id: rescheduleTarget.id });
    }
    setRescheduleTarget(null);
    toast.success('Reschedule sent — customer will receive a new confirmation request.');
  };

  /**
   * Admin-picked reschedule from an R-request (bughunt H-6).
   *
   * Routes through the new ``/reschedule-from-request`` endpoint so the
   * backend resets the appointment to SCHEDULED and fires SMS #1 (Y/R/C)
   * rather than the one-way "We moved your appointment to …" notice.
   */
  const handleRescheduleSubmit = async (payload: {
    scheduled_date: string;
    time_window_start: string;
    time_window_end: string;
    staff_id: string;
    notes?: string;
  }) => {
    if (!rescheduleTarget?.appointment_id) {
      throw new Error('Missing appointment id for reschedule');
    }
    const iso = `${payload.scheduled_date}T${payload.time_window_start}:00`;
    try {
      await rescheduleFromRequestMutation.mutateAsync({
        id: rescheduleTarget.appointment_id,
        new_scheduled_at: iso,
      });
    } catch (err) {
      toast.error('Failed to send reschedule', {
        description: getErrorMessage(err),
      });
      throw err;
    }
  };

  if (isLoading) {
    return (
      <div
        className="bg-slate-50 rounded-xl p-4 border border-slate-100"
        data-testid="reschedule-queue"
      >
        <div className="flex items-center gap-2 mb-3">
          <CalendarClock className="h-4 w-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-slate-700">Reschedule Requests</h3>
        </div>
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="bg-slate-50 rounded-xl p-4 border border-slate-100"
        data-testid="reschedule-queue"
      >
        <div className="flex items-center gap-2 mb-3">
          <CalendarClock className="h-4 w-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-slate-700">Reschedule Requests</h3>
        </div>
        <p className="text-sm text-slate-400">Failed to load requests</p>
      </div>
    );
  }

  const hasRequests = requests && requests.length > 0;

  return (
    <>
      <div
        className="bg-slate-50 rounded-xl p-4 border border-slate-100"
        data-testid="reschedule-queue"
      >
        <QueueFreshnessHeader
          icon={<CalendarClock className="h-4 w-4 text-amber-500" />}
          title="Reschedule Requests"
          badgeCount={hasRequests ? requests.length : undefined}
          badgeClassName="bg-amber-100 text-amber-700"
          dataUpdatedAt={dataUpdatedAt}
          isRefetching={isFetching}
          onRefresh={() =>
            queryClient.invalidateQueries({ queryKey: rescheduleKeys.all })
          }
          testId="refresh-reschedule-btn"
        />

        {!hasRequests ? (
          <p className="text-sm text-slate-400" data-testid="reschedule-queue-empty">
            No open reschedule requests
          </p>
        ) : (
          <div className="space-y-2" data-testid="reschedule-queue-list">
            {requests.map((req) => (
              <RescheduleRequestItem
                key={req.id}
                request={req}
                onReschedule={() => setRescheduleTarget(req)}
                onResolve={() => handleResolve(req.id)}
                onAppointmentClick={onAppointmentClick}
                isResolving={resolveMutation.isPending}
              />
            ))}
          </div>
        )}
      </div>

      {/* Reschedule dialog — opens appointment editor pre-filled */}
      <Dialog
        open={!!rescheduleTarget}
        onOpenChange={(open) => {
          if (!open) setRescheduleTarget(null);
        }}
      >
        <DialogContent
          className="max-w-lg max-h-[90vh] max-sm:max-h-[92vh] flex flex-col"
          aria-describedby="reschedule-dialog-desc"
        >
          <DialogHeader>
            <DialogTitle>Reschedule Appointment</DialogTitle>
            <p id="reschedule-dialog-desc" className="text-sm text-muted-foreground">
              {rescheduleTarget?.customer_name
                ? `Rescheduling for ${rescheduleTarget.customer_name}`
                : 'Choose a new date and time'}
              {rescheduleTarget?.raw_alternatives_text && (
                <span className="block mt-1 text-amber-600">
                  Customer requested: {rescheduleTarget.raw_alternatives_text}
                </span>
              )}
            </p>
          </DialogHeader>
          <div
            className="overflow-y-auto flex-1 min-h-0"
            data-testid="reschedule-dialog-scroll-body"
          >
            {rescheduleTarget && targetAppointment && (
              <AppointmentForm
                appointment={targetAppointment}
                onSuccess={handleRescheduleSuccess}
                onCancel={() => setRescheduleTarget(null)}
                submitOverride={handleRescheduleSubmit}
                submitLabel="Send Reschedule"
              />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

interface RescheduleRequestItemProps {
  request: RescheduleRequestDetail;
  onReschedule: () => void;
  onResolve: () => void;
  onAppointmentClick?: (appointmentId: string) => void;
  isResolving: boolean;
}

function RescheduleRequestItem({
  request,
  onReschedule,
  onResolve,
  onAppointmentClick,
  isResolving,
}: RescheduleRequestItemProps) {
  const timeAgo = formatDistanceToNow(new Date(request.created_at), {
    addSuffix: true,
  });

  // 2026-05-05 UX upgrade: surface the most-recent customer-supplied
  // free-text alternatives inline on the queue card so an admin does
  // not have to bounce to the Inbound Triage card to see "Tue 2pm or
  // Wed 3pm" after the original keyword "R". The backend appends each
  // follow-up reply to ``requested_alternatives.entries[]`` per
  // services/job_confirmation_service.py:_append_duplicate_open_request.
  const alternativeEntries = request.requested_alternatives?.entries ?? [];
  const latestAlternative = alternativeEntries[alternativeEntries.length - 1];

  return (
    <div
      className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-100"
      data-testid="reschedule-request-item"
    >
      <div className="flex flex-col gap-1 min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            className="font-medium text-slate-700 text-left hover:text-teal-600 truncate"
            onClick={() => onAppointmentClick?.(request.appointment_id)}
            data-testid="reschedule-customer-name"
          >
            {request.customer_name || 'Unknown Customer'}
          </button>
          <OptOutBadge customerId={request.customer_id} compact />
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
          {request.original_appointment_date && (
            <span>
              Original:{' '}
              {format(new Date(request.original_appointment_date), 'MMM d, yyyy')}
            </span>
          )}
          {request.original_appointment_staff && (
            <span>• {request.original_appointment_staff}</span>
          )}
          <span>• {timeAgo}</span>
        </div>
        {request.raw_alternatives_text && (
          <p className="text-xs text-amber-600 mt-0.5 truncate">
            &quot;{request.raw_alternatives_text}&quot;
          </p>
        )}
        {latestAlternative && (
          <p
            className="text-xs text-teal-700 mt-0.5 truncate"
            data-testid="reschedule-latest-alternative"
            title={
              alternativeEntries.length > 1
                ? `${alternativeEntries.length} customer messages received`
                : undefined
            }
          >
            <span className="font-medium">Customer suggested:</span> &ldquo;
            {latestAlternative.text}&rdquo;
            {alternativeEntries.length > 1 && (
              <span className="text-slate-400">
                {' '}
                (+{alternativeEntries.length - 1} earlier)
              </span>
            )}
          </p>
        )}
      </div>
      <div className="flex items-center gap-2 ml-3 shrink-0">
        <Button
          size="sm"
          variant="outline"
          onClick={onReschedule}
          className="border-teal-200 text-teal-600 hover:bg-teal-50"
          data-testid="reschedule-to-alternative-btn"
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          Reschedule
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={onResolve}
          disabled={isResolving}
          data-testid="mark-resolved-btn"
        >
          <Check className="h-3 w-3 mr-1" />
          Resolve
        </Button>
      </div>
    </div>
  );
}
