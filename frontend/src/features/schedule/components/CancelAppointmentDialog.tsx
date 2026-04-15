/**
 * CancelAppointmentDialog — confirmation dialog for cancelling an appointment.
 *
 * Admin picks one of three outcomes:
 *   - "Keep appointment" — closes the dialog, no change.
 *   - "Cancel (no text)" — cancels + skips the cancellation SMS.
 *   - "Cancel & text customer" — cancels + sends the SMS to the displayed phone.
 *
 * Both cancel paths are audit-logged server-side with the admin's choice
 * (notify_customer=true|false). See CR-2 / Req 8.10-8.11.
 */

import { AlertTriangle, Phone, User, Clock } from 'lucide-react';
import { format } from 'date-fns';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { parseLocalDate } from '@/shared/utils/dateUtils';

interface CancelAppointmentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  customerName: string | null;
  customerPhone: string | null;
  scheduledDate: string | null;
  timeWindowStart: string | null;
  timeWindowEnd: string | null;
  /** Whether the pre-cancel status will trigger an SMS (scheduled/confirmed/en_route/in_progress). */
  willNotifyByDefault: boolean;
  onConfirm: (notifyCustomer: boolean) => void;
  isLoading?: boolean;
}

export function CancelAppointmentDialog({
  open,
  onOpenChange,
  customerName,
  customerPhone,
  scheduledDate,
  timeWindowStart,
  timeWindowEnd,
  willNotifyByDefault,
  onConfirm,
  isLoading = false,
}: CancelAppointmentDialogProps) {
  const formattedDate = scheduledDate
    ? format(parseLocalDate(scheduledDate), 'EEEE, MMM d, yyyy')
    : null;
  const timeRange =
    timeWindowStart && timeWindowEnd
      ? `${timeWindowStart.slice(0, 5)} – ${timeWindowEnd.slice(0, 5)}`
      : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        data-testid="cancel-appointment-dialog"
        className="sm:max-w-lg p-0 gap-0 overflow-hidden"
      >
        {/* Header */}
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 shrink-0">
              <AlertTriangle
                className="h-6 w-6 text-amber-600"
                data-testid="cancel-appointment-warning"
              />
            </div>
            <div>
              <DialogTitle className="text-xl font-bold text-slate-800">
                Cancel this appointment?
              </DialogTitle>
              <DialogDescription className="text-sm text-slate-500 mt-1">
                Choose whether to text the customer.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Customer + appointment details */}
        <div className="px-6 py-5 space-y-4">
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-sm">
            <dt className="flex items-center gap-1.5 text-slate-500">
              <User className="h-4 w-4 text-slate-400" />
              Customer
            </dt>
            <dd
              className="text-slate-800 font-medium"
              data-testid="cancel-dialog-customer"
            >
              {customerName ?? 'Unknown customer'}
            </dd>

            <dt className="flex items-center gap-1.5 text-slate-500">
              <Phone className="h-4 w-4 text-slate-400" />
              Phone
            </dt>
            <dd
              className="text-slate-800 font-medium"
              data-testid="cancel-dialog-phone"
            >
              {customerPhone ?? '—'}
            </dd>

            {formattedDate && (
              <>
                <dt className="flex items-center gap-1.5 text-slate-500">
                  <Clock className="h-4 w-4 text-slate-400" />
                  Time
                </dt>
                <dd className="text-slate-800 font-medium">
                  {formattedDate}
                  {timeRange ? ` · ${timeRange}` : ''}
                </dd>
              </>
            )}
          </dl>

          {!willNotifyByDefault && (
            <div
              className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600"
              data-testid="cancel-dialog-no-sms-notice"
            >
              This appointment was never sent to the customer (draft), so no
              cancellation SMS would be sent either way.
            </div>
          )}
        </div>

        {/* Footer buttons */}
        <DialogFooter className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex-col gap-2 sm:flex-row sm:gap-3">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
            data-testid="cancel-dialog-keep"
            className="border-slate-300 text-slate-700 hover:bg-slate-100 sm:flex-1"
          >
            Keep appointment
          </Button>
          <Button
            variant="outline"
            onClick={() => onConfirm(false)}
            disabled={isLoading}
            data-testid="cancel-dialog-cancel-no-text"
            className="border-red-200 text-red-600 hover:bg-red-50 sm:flex-1"
          >
            Cancel (no text)
          </Button>
          <Button
            variant="destructive"
            onClick={() => onConfirm(true)}
            disabled={isLoading || !willNotifyByDefault || !customerPhone}
            data-testid="cancel-dialog-cancel-with-text"
            className="bg-red-500 hover:bg-red-600 sm:flex-1"
          >
            {isLoading ? 'Cancelling…' : 'Cancel & text customer'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
