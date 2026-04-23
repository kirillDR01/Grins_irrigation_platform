/**
 * NoReplyReviewQueue — admin triage queue for appointments whose
 * confirmation SMS went silent (bughunt H-7).
 *
 * Backed by the nightly ``flag_no_reply_confirmations`` APScheduler
 * job that writes ``Appointment.needs_review_reason = "no_confirmation_response"``
 * and an ``Alert(type=CONFIRMATION_NO_REPLY)`` row when no reply has
 * arrived for N days (default 3; BusinessSetting-tunable).
 *
 * Each row exposes three actions:
 *   - Call Customer — opens ``tel:`` URI using the customer's phone.
 *   - Send Reminder SMS — opens a confirm dialog showing the recipient
 *     phone prominently (safety rule: only ``+19527373312`` may receive
 *     real SMS on dev) and fires the send-reminder mutation.
 *   - Mark Contacted — clears ``needs_review_reason`` via the
 *     mark-contacted mutation so the row drops off the queue.
 *
 * Validates: bughunt 2026-04-16 finding H-7.
 */

import { useState } from 'react';
import { format, formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';
import { AlertCircle, Check, Phone, Send } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { getErrorMessage } from '@/core/api/client';
import {
  useMarkContacted,
  useNoReplyReviewList,
  useSendReminder,
  noReplyReviewKeys,
} from '../hooks/useNoReplyReview';
import type { NeedsReviewAppointment } from '../types';
import { OptOutBadge, QueueFreshnessHeader } from '@/shared/components';
import { useCustomerConsentStatus } from '@/features/customers/hooks/useConsentStatus';

interface NoReplyReviewQueueProps {
  onAppointmentClick?: (appointmentId: string) => void;
}

export function NoReplyReviewQueue({
  onAppointmentClick,
}: NoReplyReviewQueueProps) {
  const {
    data: rows,
    isLoading,
    error,
    dataUpdatedAt,
    isFetching,
  } = useNoReplyReviewList();
  const queryClient = useQueryClient();
  const markContactedMutation = useMarkContacted();
  const sendReminderMutation = useSendReminder();
  const [reminderTarget, setReminderTarget] =
    useState<NeedsReviewAppointment | null>(null);

  const handleMarkContacted = async (appointmentId: string) => {
    try {
      await markContactedMutation.mutateAsync(appointmentId);
      toast.success('Marked as contacted');
    } catch (err) {
      toast.error('Failed to mark as contacted', {
        description: getErrorMessage(err),
      });
    }
  };

  const handleConfirmSendReminder = async () => {
    if (!reminderTarget) return;
    const target = reminderTarget;
    setReminderTarget(null);
    try {
      await sendReminderMutation.mutateAsync(target.id);
      toast.success(
        `Reminder SMS sent to ${target.customer_name ?? 'customer'}`
      );
    } catch (err) {
      toast.error('Failed to send reminder', {
        description: getErrorMessage(err),
      });
    }
  };

  if (isLoading) {
    return (
      <div
        className="bg-slate-50 rounded-xl p-4 border border-slate-100"
        data-testid="no-reply-queue"
      >
        <div className="flex items-center gap-2 mb-3">
          <AlertCircle className="h-4 w-4 text-orange-500" />
          <h3 className="text-sm font-semibold text-slate-700">
            No-Reply Confirmations
          </h3>
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
        data-testid="no-reply-queue"
      >
        <div className="flex items-center gap-2 mb-3">
          <AlertCircle className="h-4 w-4 text-orange-500" />
          <h3 className="text-sm font-semibold text-slate-700">
            No-Reply Confirmations
          </h3>
        </div>
        <p className="text-sm text-slate-400">Failed to load queue</p>
      </div>
    );
  }

  const hasRows = rows && rows.length > 0;

  return (
    <>
      <div
        className="bg-slate-50 rounded-xl p-4 border border-slate-100"
        data-testid="no-reply-queue"
      >
        <QueueFreshnessHeader
          icon={<AlertCircle className="h-4 w-4 text-orange-500" />}
          title="No-Reply Confirmations"
          badgeCount={hasRows ? rows.length : undefined}
          badgeClassName="bg-orange-100 text-orange-700"
          dataUpdatedAt={dataUpdatedAt}
          isRefetching={isFetching}
          onRefresh={() =>
            queryClient.invalidateQueries({ queryKey: noReplyReviewKeys.all })
          }
          testId="refresh-no-reply-btn"
        />

        {!hasRows ? (
          <p
            className="text-sm text-slate-400"
            data-testid="no-reply-queue-empty"
          >
            No appointments awaiting confirmation
          </p>
        ) : (
          <div className="space-y-2" data-testid="no-reply-queue-list">
            {rows.map((row) => (
              <NoReplyRow
                key={row.id}
                row={row}
                onCallCustomer={undefined}
                onSendReminder={() => setReminderTarget(row)}
                onMarkContacted={() => handleMarkContacted(row.id)}
                onAppointmentClick={onAppointmentClick}
                isMarkingContacted={markContactedMutation.isPending}
              />
            ))}
          </div>
        )}
      </div>

      {/* Send Reminder confirmation dialog (safety-critical on dev) */}
      <Dialog
        open={!!reminderTarget}
        onOpenChange={(open) => {
          if (!open) setReminderTarget(null);
        }}
      >
        <DialogContent
          className="sm:max-w-md"
          data-testid="send-reminder-confirm-dialog"
        >
          <DialogHeader>
            <DialogTitle>Send reminder SMS?</DialogTitle>
            <DialogDescription>
              This will re-fire the Y/R/C confirmation prompt to the
              customer. Confirm the recipient before sending — on dev,
              only <strong>+19527373312</strong> may receive real SMS.
            </DialogDescription>
          </DialogHeader>
          {reminderTarget && (
            <div className="bg-slate-50 rounded-lg p-4 space-y-1 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Customer</span>
                <span
                  className="font-medium text-slate-800"
                  data-testid="reminder-confirm-customer"
                >
                  {reminderTarget.customer_name ?? 'Unknown customer'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Phone</span>
                <span
                  className="font-mono text-slate-800"
                  data-testid="reminder-confirm-phone"
                >
                  {reminderTarget.customer_phone ?? '—'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Appointment</span>
                <span className="text-slate-800">
                  {format(
                    new Date(reminderTarget.scheduled_date),
                    'MMM d, yyyy'
                  )}
                </span>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setReminderTarget(null)}
              disabled={sendReminderMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirmSendReminder}
              disabled={sendReminderMutation.isPending}
              data-testid="confirm-send-reminder-btn"
            >
              <Send className="h-3 w-3 mr-1" />
              Send reminder
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

interface NoReplyRowProps {
  row: NeedsReviewAppointment;
  onCallCustomer?: () => void;
  onSendReminder: () => void;
  onMarkContacted: () => void;
  onAppointmentClick?: (appointmentId: string) => void;
  isMarkingContacted: boolean;
}

function NoReplyRow({
  row,
  onSendReminder,
  onMarkContacted,
  onAppointmentClick,
  isMarkingContacted,
}: NoReplyRowProps) {
  const sinceLabel = row.confirmation_sent_at
    ? `${formatDistanceToNow(new Date(row.confirmation_sent_at))} since confirmation sent`
    : 'Awaiting reply';
  const appointmentLabel = `${format(
    new Date(row.scheduled_date),
    'MMM d, yyyy'
  )} • ${row.time_window_start.slice(0, 5)}–${row.time_window_end.slice(0, 5)}`;
  const { data: consentStatus } = useCustomerConsentStatus(row.customer_id);
  const optedOut = consentStatus?.is_opted_out === true;

  return (
    <div
      className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-100"
      data-testid={`no-reply-row-${row.id}`}
    >
      <div className="flex flex-col gap-1 min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            className="font-medium text-slate-700 text-left hover:text-teal-600 truncate"
            onClick={() => onAppointmentClick?.(row.id)}
            data-testid="no-reply-customer-name"
          >
            {row.customer_name ?? 'Unknown customer'}
          </button>
          <OptOutBadge customerId={row.customer_id} compact />
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
          {row.customer_phone && (
            <span className="font-mono">{row.customer_phone}</span>
          )}
          <span>• {appointmentLabel}</span>
          <span className="text-orange-600">• {sinceLabel}</span>
        </div>
      </div>
      <div className="flex items-center gap-2 ml-3 shrink-0">
        {row.customer_phone ? (
          <Button
            asChild
            size="sm"
            variant="outline"
            className="border-teal-200 text-teal-600 hover:bg-teal-50"
            data-testid={`call-customer-btn-${row.id}`}
          >
            <a href={`tel:${row.customer_phone}`}>
              <Phone className="h-3 w-3 mr-1" />
              Call
            </a>
          </Button>
        ) : (
          <Button
            size="sm"
            variant="outline"
            disabled
            data-testid={`call-customer-btn-${row.id}`}
            title="No phone on file"
          >
            <Phone className="h-3 w-3 mr-1" />
            Call
          </Button>
        )}
        <Button
          size="sm"
          variant="outline"
          onClick={onSendReminder}
          disabled={optedOut}
          title={
            optedOut
              ? 'Customer has opted out of SMS — reminder blocked'
              : 'Re-send the confirmation SMS as a reminder'
          }
          data-testid={`send-reminder-btn-${row.id}`}
        >
          <Send className="h-3 w-3 mr-1" />
          Send Reminder
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={onMarkContacted}
          disabled={isMarkingContacted}
          data-testid={`mark-contacted-btn-${row.id}`}
        >
          <Check className="h-3 w-3 mr-1" />
          Mark Contacted
        </Button>
      </div>
    </div>
  );
}
