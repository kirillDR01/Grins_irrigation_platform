/**
 * AppointmentModal — high-fidelity appointment detail modal.
 * Composes all sub-components and preserves all existing functionality.
 * Requirements: 1.1–1.8, 6.1, 6.4–6.6, 15.1–15.8, 16.1–16.4, 18.5–18.6, 19.1–19.5
 */

import { useEffect, useRef, useState } from 'react';
import { format, formatDistanceToNow } from 'date-fns';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  AlertCircle,
  AlertTriangle,
  CalendarClock,
  Check,
  Clock,
  RefreshCw,
  Send,
} from 'lucide-react';
import { invoiceApi } from '@/features/invoices/api/invoiceApi';
import type { Invoice as InvoiceWithLink } from '@/features/invoices/types';
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
import { useModalState, deriveStep } from '../../hooks/useModalState';
import { useAppointmentNotes } from '../../hooks/useAppointmentNotes';
import { useCustomerPhotos } from '@/features/customers';
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
import { SubSheetHeader } from './SubSheetHeader';
import { PaymentSheetWrapper } from './PaymentSheetWrapper';
import { EstimateSheetWrapper } from './EstimateSheetWrapper';
import { PhotosPanel } from './PhotosPanel';
import { NotesPanel } from './NotesPanel';
import { ReviewConfirmDialog } from './ReviewConfirmDialog';

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

  const {
    data: appointment,
    isLoading,
    error,
    isFetching,
  } = useAppointment(appointmentId);
  const {
    data: timeline,
    isLoading: timelineLoading,
    error: timelineError,
  } = useAppointmentTimeline(appointmentId);

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

  // Invoice for this appointment's job — drives PaidStatePill, link-sent
  // indicator, and CG-6 polling. Plan §Phase 3.3 / 3.5.
  const { data: jobInvoices } = useQuery({
    queryKey: ['invoices', 'by-job', job?.id ?? ''],
    queryFn: async (): Promise<InvoiceWithLink[]> => {
      const response = await invoiceApi.list({
        job_id: job!.id,
        page_size: 50,
      });
      return response.items;
    },
    enabled: !!job?.id,
    refetchInterval: (query) => {
      const items = query.state.data;
      if (!items || items.length === 0) return false;
      const inv = items.find((i) => i.status !== 'cancelled') ?? items[0];
      // CG-6: poll every 4s while a Payment Link is outstanding so the
      // PaidStatePill flips automatically when the webhook lands. Stops
      // on terminal states (PAID / REFUNDED / DISPUTED).
      if (
        (inv.status === 'sent' || inv.status === 'overdue') &&
        (inv.payment_link_sent_count ?? 0) > 0
      ) {
        return 4000;
      }
      return false;
    },
    refetchIntervalInBackground: false,
  });
  const invoice =
    jobInvoices?.find((i) => i.status !== 'cancelled') ?? jobInvoices?.[0] ?? null;

  const { data: tags } = useCustomerTags(job?.customer_id);

  // V2: photo and note counts for SecondaryActionsStrip badges
  const { data: photos } = useCustomerPhotos(job?.customer_id ?? '');
  const { data: notes } = useAppointmentNotes(appointmentId);
  const photoCount = photos?.length ?? 0;
  const noteCount = (notes?.body?.length ?? 0) > 0 ? 1 : 0;

  const {
    openSheet,
    openSheetExclusive,
    closeSheet,
    openPanel,
    editingNotes,
    togglePanel,
    setEditingNotes,
  } = useModalState();

  const cancelMutation = useCancelAppointment();
  const noShowMutation = useMarkAppointmentNoShow();
  const resolveRescheduleMutation = useResolveRescheduleRequest();
  const rescheduleFromRequestMutation = useRescheduleFromRequest();
  const markContactedMutation = useMarkContacted();
  const sendReminderMutation = useSendReminder();

  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [rescheduleTarget, setRescheduleTarget] =
    useState<PendingRescheduleRequest | null>(null);
  const [reminderConfirmOpen, setReminderConfirmOpen] = useState(false);
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);

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
        <div
          className="fixed inset-0 bg-[rgba(11,18,32,0.4)] backdrop-blur-[4px]"
          onClick={onClose}
        />
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
        <div
          className="fixed inset-0 bg-[rgba(11,18,32,0.4)] backdrop-blur-[4px]"
          onClick={onClose}
        />
        <div className="relative bg-white rounded-[18px] p-8 text-center">
          <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
          <p className="font-medium text-slate-800">Error loading appointment</p>
          <Button variant="ghost" size="sm" onClick={onClose} className="mt-3">
            Close
          </Button>
        </div>
      </div>
    );
  }

  const isDraft = appointment.status === 'draft';
  const isCompleted = appointment.status === 'completed';

  // Plan §Phase 3.4 guards.
  const serviceAgreementCovered = job?.service_agreement_active === true;
  // A "lead-only" appointment is one whose owning Job has no Customer
  // record yet (still a Lead). We approximate this by the absence of a
  // resolved customer object — backend rejects send-link in this case.
  const isLeadOnly = !!job && !customer;

  const willNotifyByDefault = [
    'scheduled',
    'confirmed',
    'en_route',
    'in_progress',
  ].includes(appointment.status);

  const pendingReschedule = timeline?.pending_reschedule_request ?? null;
  const needsReviewNoReply = timeline?.needs_review_reason === 'no_confirmation_response';
  const isOptedOut = timeline?.opt_out?.consent_given === false;

  const primaryProperty =
    customer?.properties?.find((p) => p.is_primary) ?? customer?.properties?.[0];

  const totalJobs = customerJobs?.items?.length ?? 0;
  const completedJobs =
    customerJobs?.items?.filter((j) => j.status === 'completed').length ?? 0;
  const historySummary =
    totalJobs > 0 ? `${completedJobs} of ${totalJobs} jobs completed` : undefined;

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
                      {formatDistanceToNow(new Date(pendingReschedule.created_at), {
                        addSuffix: true,
                      })}
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
                  <p className="text-sm font-medium text-slate-800">
                    No reply received yet.
                  </p>
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
              <SendConfirmationButton
                appointment={appointment}
                customerId={customer.id}
              />
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
            onReview={() => setReviewDialogOpen(true)}
            reviewEnabled={isCompleted && !!customer?.phone}
            reviewDisabledReason={
              !isCompleted
                ? 'Available after appointment is marked completed'
                : !customer?.phone
                  ? 'Customer has no phone number'
                  : undefined
            }
            photosOpen={openPanel === 'photos'}
            notesOpen={openPanel === 'notes'}
            photoCount={photoCount}
            noteCount={noteCount}
            onTogglePhotos={() => togglePanel('photos')}
            onToggleNotes={() => togglePanel('notes')}
          />

          {/* V2: Photos panel (conditional) */}
          {openPanel === 'photos' && job?.customer_id && (
            <div className="px-5">
              <PhotosPanel
                customerId={job.customer_id}
                appointmentId={appointmentId}
                jobId={job.id}
              />
            </div>
          )}

          {/* V2: Notes panel (conditional) */}
          {openPanel === 'notes' && (
            <div className="px-5">
              <NotesPanel
                appointmentId={appointmentId}
                editing={editingNotes}
                onSetEditing={setEditingNotes}
              />
            </div>
          )}

          {/* Payment / Estimate CTAs */}
          {(appointment.status === 'in_progress' || isCompleted) && (
            <div className="px-5 pb-4 space-y-2 flex-shrink-0">
              {/* Plan §Phase 3.3 — PaidStatePill: terminal states get a pill
                  instead of the Collect Payment CTA. */}
              {invoice && invoice.status === 'paid' && (
                <PaidStatePill invoice={invoice} variant="paid" />
              )}
              {invoice && invoice.status === 'refunded' && (
                <PaidStatePill invoice={invoice} variant="refunded" />
              )}
              {invoice && invoice.status === 'disputed' && (
                <PaidStatePill invoice={invoice} variant="disputed" />
              )}

              {/* Plan §Phase 3.3 — link-sent indicator when invoice still
                  open. Hidden once invoice reaches a terminal state. */}
              {invoice &&
                (invoice.status === 'sent' || invoice.status === 'overdue') &&
                (invoice.payment_link_sent_count ?? 0) > 0 && (
                  <LinkSentIndicator invoice={invoice} />
                )}

              {/* Plan §Phase 3.4 — hide CTA entirely for service-agreement
                  jobs, and don't repeat for already-paid invoices. */}
              {!serviceAgreementCovered &&
                !(invoice && ['paid', 'refunded'].includes(invoice.status)) && (
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => openSheetExclusive('payment')}
                      data-testid="collect-payment-cta"
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

              {serviceAgreementCovered && (
                <p
                  className="text-xs text-slate-500"
                  data-testid="service-agreement-payment-suppressed"
                >
                  Covered by service agreement — no payment required.
                </p>
              )}
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
          <div
            className="absolute inset-0 z-10 bg-white flex flex-col"
            data-testid="subsheet-tags"
          >
            <SubSheetHeader title="Edit tags" onBack={closeSheet} />
            <div className="flex-1 overflow-y-auto">
              <TagEditorSheet
                customerId={customer.id}
                customerName={`${customer.first_name} ${customer.last_name}`}
                onClose={closeSheet}
              />
            </div>
          </div>
        )}

        {/* Payment sheet */}
        {openSheet === 'payment' && (
          <div
            className="absolute inset-0 z-10 bg-white flex flex-col"
            data-testid="subsheet-payment"
          >
            <SubSheetHeader title="Collect payment" onBack={closeSheet} />
            <div className="flex-1 overflow-y-auto">
              <PaymentSheetWrapper
                appointmentId={appointmentId}
                jobId={job?.id}
                invoiceAmount={invoice?.total_amount}
                customerPhone={customer?.phone}
                customerEmail={customer?.email ?? undefined}
                customerExists={!isLeadOnly}
                serviceAgreementActive={serviceAgreementCovered}
                onClose={closeSheet}
              />
            </div>
          </div>
        )}

        {/* Estimate sheet */}
        {openSheet === 'estimate' && (
          <div
            className="absolute inset-0 z-10 bg-white flex flex-col"
            data-testid="subsheet-estimate"
          >
            <SubSheetHeader title="Create estimate" onBack={closeSheet} />
            <div className="flex-1 overflow-y-auto">
              <EstimateSheetWrapper
                appointmentId={appointmentId}
                onClose={closeSheet}
              />
            </div>
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
      <Dialog
        open={!!rescheduleTarget}
        onOpenChange={(open) => {
          if (!open) setRescheduleTarget(null);
        }}
      >
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

      {/* Send Review Request confirmation dialog */}
      <ReviewConfirmDialog
        appointmentId={appointmentId}
        customerName={
          customer ? `${customer.first_name} ${customer.last_name}` : 'customer'
        }
        customerPhone={customer?.phone ?? null}
        open={reviewDialogOpen}
        onOpenChange={setReviewDialogOpen}
      />

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
            <Button
              variant="ghost"
              onClick={() => setReminderConfirmOpen(false)}
              disabled={sendReminderMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSendReminder}
              disabled={sendReminderMutation.isPending}
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
          <p
            className="text-sm font-medium text-slate-800"
            data-testid="metric-travel-time"
          >
            {fmt(travelMinutes)}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 uppercase">Job</p>
          <p
            className="text-sm font-medium text-slate-800"
            data-testid="metric-job-duration"
          >
            {fmt(jobMinutes)}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 uppercase">Total</p>
          <p
            className="text-sm font-medium text-slate-800"
            data-testid="metric-total-time"
          >
            {fmt(totalMinutes)}
          </p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PaidStatePill / LinkSentIndicator — plan §Phase 3.3
// ---------------------------------------------------------------------------

interface PaidStatePillProps {
  invoice: InvoiceWithLink;
  variant: 'paid' | 'refunded' | 'disputed';
}

function PaidStatePill({ invoice, variant }: PaidStatePillProps) {
  const amount = invoice.paid_amount ?? invoice.total_amount;
  const formattedAmount = `$${Number(amount).toFixed(2)}`;
  // Link channel is "Payment Link" when payment_reference starts with
  // `stripe:` and the invoice has a Stripe link id. Fallback to the
  // generic payment_method label otherwise.
  const isStripeLink =
    !!invoice.stripe_payment_link_id ||
    invoice.payment_reference?.startsWith('stripe:') === true;
  const channelLabel = isStripeLink
    ? 'Payment Link'
    : (invoice.payment_method ?? 'manual');

  if (variant === 'paid') {
    const paidDate = invoice.paid_at
      ? format(new Date(invoice.paid_at), 'MMM d')
      : null;
    return (
      <div
        data-testid="paid-state-pill"
        className="flex items-center gap-2 rounded-md border border-green-100 bg-green-50 px-3 py-2"
      >
        <Check className="h-4 w-4 text-green-600 shrink-0" />
        <span className="text-sm text-green-800">
          Paid — {formattedAmount} via {channelLabel}
          {paidDate && ` on ${paidDate}`}
        </span>
      </div>
    );
  }

  if (variant === 'refunded') {
    return (
      <div
        data-testid="refunded-state-pill"
        className="flex items-center gap-2 rounded-md border border-purple-100 bg-purple-50 px-3 py-2"
      >
        <RefreshCw className="h-4 w-4 text-purple-600 shrink-0" />
        <span className="text-sm text-purple-800">
          Refunded — {formattedAmount}
        </span>
      </div>
    );
  }

  return (
    <div
      data-testid="disputed-state-pill"
      className="flex items-center gap-2 rounded-md border border-orange-100 bg-orange-50 px-3 py-2"
    >
      <AlertTriangle className="h-4 w-4 text-orange-600 shrink-0" />
      <span className="text-sm text-orange-800">
        Disputed — admin response required
      </span>
    </div>
  );
}

interface LinkSentIndicatorProps {
  invoice: InvoiceWithLink;
}

function LinkSentIndicator({ invoice }: LinkSentIndicatorProps) {
  const sent = invoice.payment_link_sent_count ?? 0;
  const lastSent = invoice.payment_link_sent_at
    ? format(new Date(invoice.payment_link_sent_at), 'MMM d, h:mm a')
    : null;
  return (
    <div
      data-testid="link-sent-indicator"
      className="flex items-center gap-2 rounded-md border border-violet-100 bg-violet-50 px-3 py-2"
    >
      <Clock className="h-4 w-4 text-violet-600 shrink-0" />
      <span className="text-sm text-violet-800">
        Link sent {sent} {sent === 1 ? 'time' : 'times'}
        {lastSent && `, last on ${lastSent}`} · waiting for payment
      </span>
    </div>
  );
}
