/**
 * AppointmentModal — high-fidelity appointment detail modal.
 * Composes all sub-components and preserves all existing functionality.
 * Requirements: 1.1–1.8, 6.1, 6.4–6.6, 15.1–15.8, 16.1–16.4, 18.5–18.6, 19.1–19.5
 */

import { useEffect, useRef, useState } from 'react';
import { format, formatDistanceToNow } from 'date-fns';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { AlertCircle, CalendarClock, Check, RefreshCw, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { OptOutBadge } from '@/shared/components';
import { getErrorMessage } from '@/core/api/client';
import { jobApi } from '@/features/jobs/api/jobApi';
import { customerApi } from '@/features/customers/api/customerApi';
import { appointmentKeys, useAppointment } from '../../hooks/useAppointments';
import { useAppointmentTimeline } from '../../hooks/useAppointmentTimeline';
import {
  useCancelAppointment,
  useMarkAppointmentNoShow,
  useRescheduleFromRequest,
} from '../../hooks/useAppointmentMutations';
import { useResolveRescheduleRequest } from '../../hooks/useRescheduleRequests';
import { useMarkContacted, useSendReminder } from '../../hooks/useNoReplyReview';
import { useCustomerTags } from '../../hooks/useCustomerTags';
import { useModalState } from '../../hooks/useModalState';
import { deriveStep } from '../../hooks/useModalState';
import type { Appointment, PendingRescheduleRequest } from '../../types';
import { AppointmentCommunicationTimeline } from '../AppointmentCommunicationTimeline';
import { AppointmentForm } from '../AppointmentForm';
import { CancelAppointmentDialog } from '../CancelAppointmentDialog';
import { SendConfirmationButton } from '../SendConfirmationButton';
import { ModalHeader } from './ModalHeader';
import { TimelineStrip } from './TimelineStrip';
import { ActionTrack } from './ActionTrack';
import { SecondaryActionsStrip } from './SecondaryActionsStrip';
import { CustomerHero } from './CustomerHero';
import { PropertyDirectionsCard } from './PropertyDirectionsCard';
import { ScopeMaterialsCard } from './ScopeMaterialsCard';
import { AssignedTechCard } from './AssignedTechCard';
import { ModalFooter } from './ModalFooter';
import { TagEditorSheet } from './TagEditorSheet';
import { PaymentSheetWrapper } from './PaymentSheetWrapper';
import { EstimateSheetWrapper } from './EstimateSheetWrapper';

interface AppointmentModalProps {
  appointmentId: string;
  open: boolean;
  onClose: () => void;
  onEdit?: (appointment: Appointment) => void;
}

export function AppointmentModal({
  appointmentId,
  open,
  onClose,
  onEdit,
}: AppointmentModalProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const queryClient = useQueryClient();

  const { data: appointment, isLoading, error, isFetching } = useAppointment(appointmentId);
  const { data: timeline, isLoading: timelineLoading, error: timelineError } =
    useAppointmentTimeline(appointmentId);

  const { data: job } = useQuery({
    queryKey: ['jobs', 'detail', appointment?.job_id],
    queryFn: () => jobApi.get(appointment!.job_id),
    enabled: !!appointment?.job_id,
  });

  const { data: customer } = useQuery({
    queryKey: ['customers', 'detail', job?.customer_id],
    queryFn: () => customerApi.get(job!.customer_id),
    enabled: !!job?.customer_id,
  });

  const { data: customerJobs } = useQuery({
    queryKey: ['jobs', 'list', { customer_id: job?.customer_id }],
    queryFn: () => jobApi.getByCustomer(job!.customer_id, { page_size: 100 }),
    enabled: !!job?.customer_id,
  });

  const { data: tags } = useCustomerTags(job?.customer_id);

  const { openSheet, openSheetExclusive, closeSheet } = useModalState();

  const cancelMutation = useCancelAppointment();
  const noShowMutation = useMarkAppointmentNoShow();
  const resolveRescheduleMutation = useResolveRescheduleRequest();
  const rescheduleFromRequestMutation = useRescheduleFromRequest();
  const markContactedMutation = useMarkContacted();
  const sendReminderMutation = useSendReminder();

  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [rescheduleTarget, setRescheduleTarget] = useState<PendingRescheduleRequest | null>(null);
  const [reminderConfirmOpen, setReminderConfirmOpen] = useState(false);

  // Focus close button on open (req 1.5)
  useEffect(() => {
    if (open) {
      setTimeout(() => closeButtonRef.current?.focus(), 50);
    }
  }, [open]);

  const invalidateTimeline = () => {
    queryClient.invalidateQueries({ queryKey: appointmentKeys.timeline(appointmentId) });
    queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(appointmentId) });
  };

  if (!open) return null;

  if (isLoading) {
    return (
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Loading appointment"
        className="fixed inset-0 z-50 flex items-center justify-center"
      >
        <div className="fixed inset-0 bg-[rgba(11,18,32,0.4)] backdrop-blur-[4px]" onClick={onClose} />
        <div className="relative bg-white rounded-[18px] p-8 flex items-center justify-center">
          <LoadingSpinner />
        </div>
      </div>
    );
  }

  if (error || !appointment) {
    return (
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Error loading appointment"
        className="fixed inset-0 z-50 flex items-center justify-center"
      >
        <div className="fixed inset-0 bg-[rgba(11,18,32,0.4)] backdrop-blur-[4px]" onClick={onClose} />
        <div className="relative bg-white rounded-[18px] p-8 text-center">
          <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
          <p className="font-medium text-slate-800">Error loading appointment</p>
          <Button variant="ghost" size="sm" onClick={onClose} className="mt-3">Close</Button>
        </div>
      </div>
    );
  }

  const isDraft = appointment.status === 'draft';
  const isCompleted = appointment.status === 'completed';

  const willNotifyByDefault = ['scheduled', 'confirmed', 'en_route', 'in_progress'].includes(
    appointment.status,
  );

  const pendingReschedule = timeline?.pending_reschedule_request ?? null;
  const needsReviewNoReply = timeline?.needs_review_reason === 'no_confirmation_response';
  const isOptedOut = timeline?.opt_out?.consent_given === false;

  const primaryProperty =
    customer?.properties?.find((p) => p.is_primary) ?? customer?.properties?.[0];

  const totalJobs = customerJobs?.items?.length ?? 0;
  const completedJobs = customerJobs?.items?.filter((j) => j.status === 'completed').length ?? 0;
  const historySummary =
    totalJobs > 0
      ? `${completedJobs} of ${totalJobs} jobs completed`
      : undefined;

  const jobTitle = job?.job_type
    ? job.job_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
    : 'Appointment';

  const scheduleLine = appointment.scheduled_date
    ? `${format(new Date(appointment.scheduled_date + 'T00:00:00'), 'EEEE, MMMM d')} · ${appointment.time_window_start.slice(0, 5)}–${appointment.time_window_end.slice(0, 5)}`
    : undefined;

  const step = deriveStep(appointment.status);
  const timestamps: [string | null, string | null, string | null, string | null] = [
    appointment.created_at,
    appointment.en_route_at,
    appointment.arrived_at,
    appointment.completed_at,
  ];

  const handleCancelConfirmed = async (notifyCustomer: boolean) => {
    await cancelMutation.mutateAsync({ id: appointmentId, notifyCustomer });
    setCancelDialogOpen(false);
    onClose();
  };

  const handleNoShow = async () => {
    await noShowMutation.mutateAsync(appointmentId);
  };

  const handleResolveReschedule = async () => {
    if (!pendingReschedule) return;
    try {
      await resolveRescheduleMutation.mutateAsync({ id: pendingReschedule.id });
      invalidateTimeline();
      toast.success('Reschedule request resolved');
    } catch (err) {
      toast.error('Failed to resolve request', { description: getErrorMessage(err) });
    }
  };

  const handleRescheduleSubmit = async (payload: {
    scheduled_date: string;
    time_window_start: string;
    time_window_end: string;
    staff_id: string;
    notes?: string;
  }) => {
    if (!rescheduleTarget) throw new Error('No reschedule target');
    const iso = `${payload.scheduled_date}T${payload.time_window_start}:00`;
    try {
      await rescheduleFromRequestMutation.mutateAsync({
        id: rescheduleTarget.appointment_id,
        new_scheduled_at: iso,
      });
    } catch (err) {
      toast.error('Failed to send reschedule', { description: getErrorMessage(err) });
      throw err;
    }
  };

  const handleRescheduleSuccess = () => {
    if (rescheduleTarget) {
      resolveRescheduleMutation.mutate({ id: rescheduleTarget.id });
    }
    setRescheduleTarget(null);
    invalidateTimeline();
    toast.success('Reschedule sent — customer will receive a new confirmation request.');
  };

  const handleMarkContacted = async () => {
    try {
      await markContactedMutation.mutateAsync(appointmentId);
      invalidateTimeline();
      toast.success('Marked as contacted');
    } catch (err) {
      toast.error('Failed to mark as contacted', { description: getErrorMessage(err) });
    }
  };

  const handleSendReminder = async () => {
    setReminderConfirmOpen(false);
    try {
      await sendReminderMutation.mutateAsync(appointmentId);
      invalidateTimeline();
      toast.success('Reminder SMS sent');
    } catch (err) {
      toast.error('Failed to send reminder', { description: getErrorMessage(err) });
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-[rgba(11,18,32,0.4)] backdrop-blur-[4px]"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="appointment-modal-title"
        data-testid="appointment-modal"
        className={[
          'fixed z-50 bg-white border border-[#E5E7EB] shadow-2xl overflow-hidden flex flex-col',
          // Desktop: fixed 560px centered; Mobile: full-width bottom sheet
          'sm:rounded-[18px] sm:w-[560px] sm:max-h-[90vh]',
          'sm:top-1/2 sm:left-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2',
          // Mobile bottom sheet
          'max-sm:rounded-t-[20px] max-sm:rounded-b-none max-sm:w-full max-sm:bottom-0 max-sm:left-0 max-sm:right-0 max-sm:max-h-[92vh]',
        ].join(' ')}
        onKeyDown={(e) => {
          if (e.key === 'Escape') onClose();
        }}
      >
        {/* Mobile grab handle */}
        <div className="sm:hidden flex justify-center pt-3 pb-1 flex-shrink-0">
          <div className="w-11 h-[5px] rounded-full bg-[#D1D5DB]" />
        </div>

        {/* Scrollable body */}
        <div className="overflow-y-auto flex-1 flex flex-col">
          {/* Header */}
          <ModalHeader
            jobTitle={jobTitle}
            status={appointment.status}
            propertyType={primaryProperty?.property_type ?? null}
            appointmentId={appointment.id}
            scheduleLine={scheduleLine}
            onClose={onClose}
            closeButtonRef={closeButtonRef}
          />

          {/* Opt-out badge */}
          {isOptedOut && (
            <div className="px-5 pb-2 flex-shrink-0">
              <OptOutBadge customerId={job?.customer_id ?? ''} />
            </div>
          )}

          {/* Reschedule banner */}
          {pendingReschedule && (
            <div
              className="mx-5 mb-3 px-4 py-3 rounded-[12px] border border-amber-200 bg-amber-50 flex-shrink-0"
              data-testid={`reschedule-banner-${appointmentId}`}
            >
              <div className="flex items-start gap-2">
                <CalendarClock className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-amber-900">
                    Customer requested reschedule{' '}
                    <span className="text-xs text-amber-700">
                      {formatDistanceToNow(new Date(pendingReschedule.created_at), { addSuffix: true })}
                    </span>
                  </p>
                  {pendingReschedule.raw_alternatives_text && (
                    <p className="text-xs text-amber-800 mt-0.5">
                      &quot;{pendingReschedule.raw_alternatives_text}&quot;
                    </p>
                  )}
                  <div className="mt-2 flex items-center gap-2 flex-wrap">
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-teal-200 text-teal-700 hover:bg-teal-50"
                      onClick={() => setRescheduleTarget(pendingReschedule)}
                    >
                      <RefreshCw className="h-3 w-3 mr-1" />
                      Reschedule to Alternative
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleResolveReschedule}
                      disabled={resolveRescheduleMutation.isPending}
                    >
                      <Check className="h-3 w-3 mr-1" />
                      Resolve without reschedule
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* No-reply banner */}
          {needsReviewNoReply && (
            <div
              className="mx-5 mb-3 px-4 py-3 rounded-[12px] border border-slate-200 bg-slate-100 flex-shrink-0"
              data-testid={`no-reply-banner-${appointmentId}`}
            >
              <div className="flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-orange-500 mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800">No reply received yet.</p>
                  <div className="mt-2 flex items-center gap-2 flex-wrap">
                    {customer?.phone && (
                      <Button
                        asChild
                        size="sm"
                        variant="outline"
                        className="border-teal-200 text-teal-600 hover:bg-teal-50"
                      >
                        <a href={`tel:${customer.phone}`}>Call Customer</a>
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setReminderConfirmOpen(true)}
                    >
                      <Send className="h-3 w-3 mr-1" />
                      Send Reminder
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleMarkContacted}
                      disabled={markContactedMutation.isPending}
                    >
                      <Check className="h-3 w-3 mr-1" />
                      Mark Contacted
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Draft: send confirmation */}
          {isDraft && customer && (
            <div className="px-5 pb-3 flex-shrink-0">
              <SendConfirmationButton appointment={appointment} customerId={customer.id} />
            </div>
          )}

          {/* Timeline strip */}
          <TimelineStrip currentStep={step} timestamps={timestamps} />

          {/* Action track */}
          <ActionTrack
            appointmentId={appointmentId}
            status={appointment.status}
            arrivedAt={appointment.arrived_at}
            enRouteAt={appointment.en_route_at}
            completedAt={appointment.completed_at}
          />

          {/* Secondary actions */}
          <SecondaryActionsStrip
            tagsOpen={openSheet === 'tags'}
            onEditTags={() => openSheetExclusive('tags')}
          />

          {/* Payment / Estimate CTAs */}
          {(appointment.status === 'in_progress' || isCompleted) && (
            <div className="px-5 pb-4 flex gap-2 flex-shrink-0">
              <Button
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={() => openSheetExclusive('payment')}
              >
                Collect Payment
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="flex-1"
                onClick={() => openSheetExclusive('estimate')}
              >
                Create Estimate
              </Button>
            </div>
          )}

          {/* Customer hero */}
          {customer && (
            <div className="px-5 pb-4">
              <CustomerHero
                customerId={customer.id}
                firstName={customer.first_name}
                lastName={customer.last_name}
                phone={customer.phone}
                email={customer.email}
                tags={tags}
                historySummary={historySummary}
              />
            </div>
          )}

          {/* Property directions */}
          {primaryProperty && (
            <div className="px-5 pb-4">
              <PropertyDirectionsCard
                street={primaryProperty.address}
                city={primaryProperty.city}
                state={primaryProperty.state}
                zip={primaryProperty.zip_code}
                latitude={primaryProperty.latitude}
                longitude={primaryProperty.longitude}
              />
            </div>
          )}

          {/* Scope & materials */}
          {job && (
            <div className="px-5 pb-4">
              <ScopeMaterialsCard
                scope={job.description ?? jobTitle}
                durationMinutes={job.estimated_duration_minutes}
                priority={job.priority_level}
                materials={job.materials_required ?? undefined}
              />
            </div>
          )}

          {/* Assigned tech */}
          {appointment.staff_name && (
            <div className="px-5 pb-4">
              <AssignedTechCard
                techName={appointment.staff_name}
                routeOrder={appointment.route_order}
              />
            </div>
          )}

          {/* Communication timeline */}
          <div className="px-5 pb-4">
            <AppointmentCommunicationTimeline
              data={timeline}
              isLoading={timelineLoading}
              error={timelineError}
            />
          </div>

          {/* Duration metrics (completed only) */}
          {isCompleted &&
            appointment.en_route_at &&
            appointment.arrived_at &&
            appointment.completed_at && (
              <div className="px-5 pb-4">
                <DurationMetrics
                  enRouteAt={appointment.en_route_at}
                  arrivedAt={appointment.arrived_at}
                  completedAt={appointment.completed_at}
                />
              </div>
            )}

          {/* Refresh indicator */}
          <div className="px-5 pb-2 flex items-center justify-end gap-2 flex-shrink-0">
            <Button
              size="sm"
              variant="ghost"
              className="h-6 w-6 p-0"
              disabled={isFetching}
              onClick={invalidateTimeline}
              aria-label="Refresh appointment data"
            >
              <RefreshCw className={`h-3 w-3 ${isFetching ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {/* Footer */}
        <ModalFooter
          status={appointment.status}
          onEdit={() => onEdit?.(appointment)}
          onNoShow={handleNoShow}
          onCancel={() => setCancelDialogOpen(true)}
        />

        {/* Tag editor sheet */}
        {openSheet === 'tags' && customer && (
          <div className="absolute inset-0 z-10">
            <TagEditorSheet
              customerId={customer.id}
              customerName={`${customer.first_name} ${customer.last_name}`}
              onClose={closeSheet}
            />
          </div>
        )}

        {/* Payment sheet */}
        {openSheet === 'payment' && (
          <div className="absolute inset-0 z-10">
            <PaymentSheetWrapper
              appointmentId={appointmentId}
              customerPhone={customer?.phone}
              customerEmail={customer?.email ?? undefined}
              onClose={closeSheet}
            />
          </div>
        )}

        {/* Estimate sheet */}
        {openSheet === 'estimate' && (
          <div className="absolute inset-0 z-10">
            <EstimateSheetWrapper appointmentId={appointmentId} onClose={closeSheet} />
          </div>
        )}
      </div>

      {/* Cancel dialog */}
      <CancelAppointmentDialog
        open={cancelDialogOpen}
        onOpenChange={setCancelDialogOpen}
        customerName={customer ? `${customer.first_name} ${customer.last_name}` : null}
        customerPhone={customer?.phone ?? null}
        scheduledDate={appointment.scheduled_date}
        timeWindowStart={appointment.time_window_start}
        timeWindowEnd={appointment.time_window_end}
        willNotifyByDefault={willNotifyByDefault}
        onConfirm={handleCancelConfirmed}
        isLoading={cancelMutation.isPending}
      />

      {/* Reschedule dialog */}
      <Dialog open={!!rescheduleTarget} onOpenChange={(open) => { if (!open) setRescheduleTarget(null); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Reschedule Appointment</DialogTitle>
            {rescheduleTarget?.raw_alternatives_text && (
              <p className="text-sm text-amber-600">
                Customer requested: {rescheduleTarget.raw_alternatives_text}
              </p>
            )}
          </DialogHeader>
          {rescheduleTarget && (
            <AppointmentForm
              appointment={appointment}
              onSuccess={handleRescheduleSuccess}
              onCancel={() => setRescheduleTarget(null)}
              submitOverride={handleRescheduleSubmit}
              submitLabel="Send Reschedule"
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Send reminder confirmation dialog */}
      <Dialog open={reminderConfirmOpen} onOpenChange={setReminderConfirmOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Send reminder SMS?</DialogTitle>
            <DialogDescription>
              This will re-fire the Y/R/C confirmation prompt to the customer.
            </DialogDescription>
          </DialogHeader>
          <div className="bg-slate-50 rounded-lg p-4 space-y-1 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Customer</span>
              <span className="font-medium text-slate-800">
                {customer ? `${customer.first_name} ${customer.last_name}` : 'Unknown'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Phone</span>
              <span className="font-mono text-slate-800">{customer?.phone ?? '—'}</span>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setReminderConfirmOpen(false)} disabled={sendReminderMutation.isPending}>
              Cancel
            </Button>
            <Button onClick={handleSendReminder} disabled={sendReminderMutation.isPending}>
              <Send className="h-3 w-3 mr-1" />
              Send reminder
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ---------------------------------------------------------------------------
// DurationMetrics sub-component (Req 37)
// ---------------------------------------------------------------------------

interface DurationMetricsProps {
  enRouteAt: string;
  arrivedAt: string;
  completedAt: string;
}

function DurationMetrics({ enRouteAt, arrivedAt, completedAt }: DurationMetricsProps) {
  const enRoute = new Date(enRouteAt).getTime();
  const arrived = new Date(arrivedAt).getTime();
  const completed = new Date(completedAt).getTime();

  const travelMinutes = Math.round((arrived - enRoute) / 60_000);
  const jobMinutes = Math.round((completed - arrived) / 60_000);
  const totalMinutes = Math.round((completed - enRoute) / 60_000);

  const fmt = (mins: number): string => {
    if (mins < 60) return `${mins}m`;
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
  };

  return (
    <div className="p-3 bg-emerald-50 rounded-xl" data-testid="duration-metrics-section">
      <p className="text-xs font-semibold uppercase tracking-wider text-emerald-600 mb-2">
        Duration Metrics
      </p>
      <div className="grid grid-cols-3 gap-3">
        <div>
          <p className="text-[10px] text-slate-500 uppercase">Travel</p>
          <p className="text-sm font-medium text-slate-800" data-testid="metric-travel-time">
            {fmt(travelMinutes)}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 uppercase">Job</p>
          <p className="text-sm font-medium text-slate-800" data-testid="metric-job-duration">
            {fmt(jobMinutes)}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 uppercase">Total</p>
          <p className="text-sm font-medium text-slate-800" data-testid="metric-total-time">
            {fmt(totalMinutes)}
          </p>
        </div>
      </div>
    </div>
  );
}
