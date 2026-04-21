/**
 * Enriched appointment detail component (Req 40).
 * Shows customer info, job type, location with Google Maps link,
 * materials needed, estimated duration, customer history, special notes,
 * and "Get Directions" button.
 */

import { useState } from 'react';
import { format, formatDistanceToNow } from 'date-fns';
import { parseLocalDate } from '@/shared/utils/dateUtils';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Calendar,
  User,
  Briefcase,
  MapPin,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Navigation,
  Pencil,
  Phone,
  Mail,
  Package,
  History,
  FileText,
  Timer,
  ChevronDown,
  CalendarClock,
  Check,
  Ban,
  RefreshCw,
  Send,
} from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getErrorMessage } from '@/core/api/client';
import { appointmentKeys, useAppointment } from '../hooks/useAppointments';
import { useAppointmentTimeline } from '../hooks/useAppointmentTimeline';
import {
  useConfirmAppointment,
  useCancelAppointment,
  useMarkAppointmentNoShow,
  useRescheduleFromRequest,
} from '../hooks/useAppointmentMutations';
import { useResolveRescheduleRequest } from '../hooks/useRescheduleRequests';
import {
  useMarkContacted,
  useSendReminder,
} from '../hooks/useNoReplyReview';
import { appointmentStatusConfig } from '../types';
import type { Appointment, PendingRescheduleRequest } from '../types';
import { AppointmentCommunicationTimeline } from './AppointmentCommunicationTimeline';
import { AppointmentForm } from './AppointmentForm';
import { jobApi } from '@/features/jobs/api/jobApi';
import { customerApi } from '@/features/customers/api/customerApi';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { StaffWorkflowButtons } from './StaffWorkflowButtons';
import { PaymentCollector } from './PaymentCollector';
import { InvoiceCreator } from './InvoiceCreator';
import { EstimateCreator } from './EstimateCreator';
import { AppointmentNotes } from './AppointmentNotes';
import { ReviewRequest } from './ReviewRequest';
import { CancelAppointmentDialog } from './CancelAppointmentDialog';
import { SendConfirmationButton } from './SendConfirmationButton';

interface AppointmentDetailProps {
  appointmentId: string;
  onClose?: () => void;
  onEdit?: (appointment: Appointment) => void;
}

export function AppointmentDetail({
  appointmentId,
  onClose,
  onEdit,
}: AppointmentDetailProps) {
  const { data: appointment, isLoading, error } = useAppointment(appointmentId);
  const {
    data: timeline,
    isLoading: timelineLoading,
    error: timelineError,
  } = useAppointmentTimeline(appointmentId);

  const queryClient = useQueryClient();
  const confirmMutation = useConfirmAppointment();
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

  const invalidateTimeline = () => {
    queryClient.invalidateQueries({
      queryKey: appointmentKeys.timeline(appointmentId),
    });
    queryClient.invalidateQueries({
      queryKey: appointmentKeys.detail(appointmentId),
    });
  };

  // Fetch job details for enrichment (Req 40)
  const { data: job } = useQuery({
    queryKey: ['jobs', 'detail', appointment?.job_id],
    queryFn: () => jobApi.get(appointment!.job_id),
    enabled: !!appointment?.job_id,
  });

  // Fetch customer details for enrichment (Req 40)
  const { data: customer } = useQuery({
    queryKey: ['customers', 'detail', job?.customer_id],
    queryFn: () => customerApi.get(job!.customer_id),
    enabled: !!job?.customer_id,
  });

  // Fetch customer's job history for summary
  const { data: customerJobs } = useQuery({
    queryKey: ['jobs', 'list', { customer_id: job?.customer_id }],
    queryFn: () => jobApi.getByCustomer(job!.customer_id, { page_size: 100 }),
    enabled: !!job?.customer_id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <LoadingSpinner />
      </div>
    );
  }

  if (error || !appointment) {
    return (
      <div className="p-4 text-center">
        <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-2">
          <AlertCircle className="h-5 w-5 text-red-600" />
        </div>
        <p className="text-slate-800 font-medium text-sm">Error loading appointment</p>
        <p className="text-xs text-slate-500 mt-1">Please try again later</p>
      </div>
    );
  }

  const statusConfig = appointmentStatusConfig[appointment.status];
  const isPending = appointment.status === 'pending';
  const isDraft = appointment.status === 'draft';
  const isConfirmed = appointment.status === 'confirmed';
  const isEnRoute = appointment.status === 'en_route';
  const isInProgress = appointment.status === 'in_progress';
  const isCompleted = appointment.status === 'completed';
  const isTerminal = ['completed', 'cancelled', 'no_show'].includes(
    appointment.status
  );
  const isActiveWorkflow = isConfirmed || isEnRoute || isInProgress;

  // Track whether payment/invoice exists for Req 36
  // TODO: Wire to real data when backend provides it
  const hasPaymentOrInvoice = false;

  // Build address for Google Maps link
  const primaryProperty = customer?.properties?.find((p) => p.is_primary) ?? customer?.properties?.[0];
  const address = primaryProperty
    ? [primaryProperty.address, primaryProperty.city, primaryProperty.state, primaryProperty.zip_code]
        .filter(Boolean)
        .join(', ')
    : null;
  const mapsUrl = address
    ? `https://maps.google.com/?daddr=${encodeURIComponent(address)}`
    : null;

  // Customer history summary
  const totalJobs = customerJobs?.items?.length ?? 0;
  const completedJobs = customerJobs?.items?.filter((j) => j.status === 'completed').length ?? 0;
  const lastCompleted = customerJobs?.items
    ?.filter((j) => j.completed_at)
    ?.sort((a, b) => (b.completed_at! > a.completed_at! ? 1 : -1))?.[0];

  // Materials from job
  const materialsNeeded = job?.materials_required?.join(', ') || null;
  const estimatedDuration = job?.estimated_duration_minutes;

  const handleConfirm = async () => {
    await confirmMutation.mutateAsync(appointmentId);
  };
  const openCancelDialog = () => {
    setCancelDialogOpen(true);
  };
  const handleCancelConfirmed = async (notifyCustomer: boolean) => {
    await cancelMutation.mutateAsync({
      id: appointmentId,
      notifyCustomer,
    });
    setCancelDialogOpen(false);
    onClose?.();
  };
  const handleNoShow = async () => {
    await noShowMutation.mutateAsync(appointmentId);
  };

  // Draft appointments have never been sent to the customer; cancelling them
  // never sends an SMS. SCHEDULED/CONFIRMED/EN_ROUTE/IN_PROGRESS do.
  const willNotifyByDefault = [
    'scheduled',
    'confirmed',
    'en_route',
    'in_progress',
  ].includes(appointment.status);

  const pendingReschedule = timeline?.pending_reschedule_request ?? null;
  const needsReviewNoReply =
    timeline?.needs_review_reason === 'no_confirmation_response';
  const isOptedOut = timeline?.opt_out?.consent_given === false;

  const handleResolveReschedule = async () => {
    if (!pendingReschedule) return;
    try {
      await resolveRescheduleMutation.mutateAsync({ id: pendingReschedule.id });
      invalidateTimeline();
      toast.success('Reschedule request resolved');
    } catch (err) {
      toast.error('Failed to resolve request', {
        description: getErrorMessage(err),
      });
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
      toast.error('Failed to send reschedule', {
        description: getErrorMessage(err),
      });
      throw err;
    }
  };

  const handleRescheduleSuccess = () => {
    if (rescheduleTarget) {
      resolveRescheduleMutation.mutate({ id: rescheduleTarget.id });
    }
    setRescheduleTarget(null);
    invalidateTimeline();
    toast.success(
      'Reschedule sent — customer will receive a new confirmation request.',
    );
  };

  const handleMarkContacted = async () => {
    try {
      await markContactedMutation.mutateAsync(appointmentId);
      invalidateTimeline();
      toast.success('Marked as contacted');
    } catch (err) {
      toast.error('Failed to mark as contacted', {
        description: getErrorMessage(err),
      });
    }
  };

  const handleSendReminder = async () => {
    setReminderConfirmOpen(false);
    try {
      await sendReminderMutation.mutateAsync(appointmentId);
      invalidateTimeline();
      toast.success('Reminder SMS sent');
    } catch (err) {
      toast.error('Failed to send reminder', {
        description: getErrorMessage(err),
      });
    }
  };

  const optOutMethodLabel = timeline?.opt_out?.method ?? 'unknown';
  const optOutDateLabel = timeline?.opt_out?.recorded_at
    ? format(new Date(timeline.opt_out.recorded_at), 'MMM d, yyyy')
    : '';

  return (
    <div data-testid="appointment-detail" className="bg-white">
      {/* Header Section - Date & Status */}
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-violet-100">
              <Calendar className="h-4 w-4 text-violet-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">
                {format(parseLocalDate(appointment.scheduled_date), 'EEEE, MMMM d, yyyy')}
              </p>
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <Clock className="h-3 w-3" />
                <span>
                  {appointment.time_window_start.slice(0, 5)} - {appointment.time_window_end.slice(0, 5)}
                </span>
                {estimatedDuration && (
                  <span className="text-slate-400">• ~{estimatedDuration} min</span>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isOptedOut && (
              <Badge
                className="bg-red-100 text-red-700 px-2 py-0.5 rounded-full text-xs font-medium flex items-center gap-1"
                data-testid={`opt-out-badge-${appointmentId}`}
                title={`Opted out via ${optOutMethodLabel}${optOutDateLabel ? ` on ${optOutDateLabel}` : ''}`}
              >
                <Ban className="h-3 w-3" />
                Opted out
              </Badge>
            )}
            <Badge
              className={`${statusConfig.bgColor} ${statusConfig.color} px-2 py-0.5 rounded-full text-xs font-medium`}
              data-testid={`status-${appointment.status}`}
            >
              {statusConfig.label}
            </Badge>
          </div>
        </div>
      </div>

      {/* Gap 11 — Communication banners */}
      {pendingReschedule && (
        <div
          className="px-4 py-3 border-b border-amber-100 bg-amber-50"
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
                  data-testid={`reschedule-to-alternative-${appointmentId}-btn`}
                >
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Reschedule to Alternative
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleResolveReschedule}
                  disabled={resolveRescheduleMutation.isPending}
                  data-testid={`resolve-reschedule-${appointmentId}-btn`}
                >
                  <Check className="h-3 w-3 mr-1" />
                  Resolve without reschedule
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {needsReviewNoReply && (
        <div
          className="px-4 py-3 border-b border-slate-200 bg-slate-100"
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
                    data-testid={`call-customer-${appointmentId}-btn`}
                  >
                    <a href={`tel:${customer.phone}`}>
                      <Phone className="h-3 w-3 mr-1" />
                      Call Customer
                    </a>
                  </Button>
                )}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setReminderConfirmOpen(true)}
                  data-testid={`send-reminder-${appointmentId}-btn`}
                >
                  <Send className="h-3 w-3 mr-1" />
                  Send Reminder
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleMarkContacted}
                  disabled={markContactedMutation.isPending}
                  data-testid={`mark-contacted-${appointmentId}-btn`}
                >
                  <Check className="h-3 w-3 mr-1" />
                  Mark Contacted
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Content Section */}
      <div className="p-4 space-y-3">
        {/* Customer Info (Req 40) — collapsible on mobile */}
        {customer && (
          <details className="group p-3 bg-slate-50 rounded-xl" open data-testid="customer-info-section">
            <summary className="flex items-center gap-2 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
              <div className="w-7 h-7 rounded-full bg-teal-100 flex items-center justify-center">
                <User className="h-4 w-4 text-teal-600" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-800">
                  {customer.first_name} {customer.last_name}
                </p>
              </div>
              <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-open:rotate-180 md:hidden" />
            </summary>
            <div className="pl-9 space-y-1 mt-2">
              <div className="flex items-center gap-1.5 text-xs text-slate-600">
                <Phone className="h-3 w-3 text-slate-400" />
                <a href={`tel:${customer.phone}`} className="hover:text-teal-600">
                  {customer.phone}
                </a>
              </div>
              {customer.email && (
                <div className="flex items-center gap-1.5 text-xs text-slate-600">
                  <Mail className="h-3 w-3 text-slate-400" />
                  <a href={`mailto:${customer.email}`} className="hover:text-teal-600">
                    {customer.email}
                  </a>
                </div>
              )}
            </div>
          </details>
        )}

        {/* Location with Google Maps link (Req 40) */}
        <div className="flex flex-col gap-2 p-3 bg-slate-50 rounded-xl md:flex-row md:items-center md:justify-between" data-testid="location-section">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-white shadow-sm">
              <MapPin className="h-3.5 w-3.5 text-slate-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-800">
                {address || 'Property Address'}
              </p>
              <p className="text-xs text-slate-500">
                {appointment.route_order ? `Route #${appointment.route_order}` : 'Not in route'}
                {appointment.estimated_arrival && ` • ETA: ${appointment.estimated_arrival.slice(0, 5)}`}
              </p>
            </div>
          </div>
          {mapsUrl && (
            <Button
              variant="outline"
              size="sm"
              className="w-full min-h-[48px] text-sm text-teal-600 border-teal-200 hover:bg-teal-50 md:w-auto md:min-h-0 md:h-7 md:text-xs md:px-2"
              asChild
              data-testid="get-directions-btn"
            >
              <a href={mapsUrl} target="_blank" rel="noopener noreferrer">
                <Navigation className="h-4 w-4 mr-1.5 md:h-3 md:w-3 md:mr-1" />
                Get Directions
              </a>
            </Button>
          )}
        </div>

        {/* Job & Staff - Stacked on mobile, side by side on desktop */}
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {/* Job Info */}
          <div className="p-3 bg-slate-50 rounded-xl" data-testid="job-info-section">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-1.5 rounded-lg bg-white shadow-sm">
                <Briefcase className="h-3.5 w-3.5 text-slate-400" />
              </div>
              <p className="text-sm font-medium text-slate-800">
                {job?.job_type || 'Job'}
              </p>
            </div>
            <Link
              to={`/jobs/${appointment.job_id}`}
              className="text-teal-600 hover:text-teal-700 text-xs font-medium"
              data-testid="job-link"
            >
              View Details →
            </Link>
          </div>

          {/* Staff Info */}
          <div className="p-3 bg-slate-50 rounded-xl">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-6 h-6 rounded-full bg-teal-100 flex items-center justify-center">
                <User className="h-3.5 w-3.5 text-teal-600" />
              </div>
              <p className="text-sm font-medium text-slate-800">
                {appointment.staff_name || 'Staff'}
              </p>
            </div>
            <Link
              to={`/staff/${appointment.staff_id}`}
              className="text-teal-600 hover:text-teal-700 text-xs font-medium"
              data-testid="staff-link"
            >
              View Profile →
            </Link>
          </div>
        </div>

        {/* Materials Needed (Req 40) — collapsible on mobile */}
        {materialsNeeded && (
          <details className="group p-3 bg-slate-50 rounded-xl" open data-testid="materials-section">
            <summary className="flex items-center gap-2 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
              <Package className="h-3.5 w-3.5 text-slate-400" />
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex-1">
                Materials Needed
              </p>
              <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-open:rotate-180 md:hidden" />
            </summary>
            <p className="text-xs text-slate-600 pl-5 mt-1">{materialsNeeded}</p>
          </details>
        )}

        {/* Customer History Summary (Req 40) — collapsible on mobile */}
        {totalJobs > 0 && (
          <details className="group p-3 bg-slate-50 rounded-xl" open data-testid="customer-history-section">
            <summary className="flex items-center gap-2 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
              <History className="h-3.5 w-3.5 text-slate-400" />
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex-1">
                Customer History
              </p>
              <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-open:rotate-180 md:hidden" />
            </summary>
            <p className="text-xs text-slate-600 pl-5 mt-1">
              {completedJobs} of {totalJobs} jobs completed
              {lastCompleted?.completed_at && (
                <> • Last service: {format(new Date(lastCompleted.completed_at), 'MMM d, yyyy')}</>
              )}
            </p>
          </details>
        )}

        {/* Notes Section */}
        {appointment.notes && (
          <div className="p-3 bg-slate-50 rounded-xl" data-testid="notes-section">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="h-3.5 w-3.5 text-slate-400" />
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Notes</p>
            </div>
            <p className="text-xs text-slate-600 pl-5 line-clamp-3">{appointment.notes}</p>
          </div>
        )}

        {/* Communication Timeline (Gap 11) */}
        <AppointmentCommunicationTimeline
          data={timeline}
          isLoading={timelineLoading}
          error={timelineError}
        />

        {/* Timeline Section - Inline */}
        {(appointment.en_route_at || appointment.arrived_at || appointment.completed_at) && (
          <div className="flex items-center gap-4 text-xs text-slate-500">
            {appointment.en_route_at && (
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                <span>En Route {format(new Date(appointment.en_route_at), 'h:mm a')}</span>
              </div>
            )}
            {appointment.arrived_at && (
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-teal-500" />
                <span>Arrived {format(new Date(appointment.arrived_at), 'h:mm a')}</span>
              </div>
            )}
            {appointment.completed_at && (
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span>Completed {format(new Date(appointment.completed_at), 'h:mm a')}</span>
              </div>
            )}
          </div>
        )}

        {/* Duration Metrics — completed appointments only (Req 37) */}
        {isCompleted && appointment.en_route_at && appointment.arrived_at && appointment.completed_at && (
          <DurationMetrics
            enRouteAt={appointment.en_route_at}
            arrivedAt={appointment.arrived_at}
            completedAt={appointment.completed_at}
          />
        )}
      </div>

      {/* Staff Workflow Buttons (Req 35, 36) */}
      {isActiveWorkflow && (
        <div className="px-4 py-3 border-t border-slate-100 bg-slate-50/30">
          <StaffWorkflowButtons
            appointmentId={appointmentId}
            status={appointment.status}
            hasPaymentOrInvoice={hasPaymentOrInvoice}
          />
        </div>
      )}

      {/* On-Site Actions (Req 30-34) */}
      {(isInProgress || isCompleted) && (
        <div className="px-4 py-3 border-t border-slate-100 space-y-3">
          {/* Payment Collection (Req 30) */}
          {(isInProgress || isCompleted) && (
            <PaymentCollector appointmentId={appointmentId} />
          )}

          {/* Invoice Creation (Req 31) */}
          <InvoiceCreator
            appointmentId={appointmentId}
            customerName={customer ? `${customer.first_name} ${customer.last_name}` : null}
            jobType={job?.job_type}
          />

          {/* Estimate Creation (Req 32) */}
          <EstimateCreator appointmentId={appointmentId} />

          {/* Notes & Photos (Req 33) */}
          <AppointmentNotes
            appointmentId={appointmentId}
            initialNotes={appointment.notes}
          />

          {/* Google Review Request (Req 34) */}
          <ReviewRequest
            appointmentId={appointmentId}
            status={appointment.status}
          />
        </div>
      )}

      {/* Admin Action Buttons */}
      {!isTerminal && (
        <div className="px-4 py-3 border-t border-slate-100 bg-slate-50/30">
          <div className="flex flex-col gap-2 md:flex-row md:flex-wrap">
            {isDraft && (
              // bughunt M-1: use the canonical SendConfirmationButton so the
              // detail modal shares the calendar card's send behavior
              // (toast feedback, hook wiring, disabled state).
              <SendConfirmationButton appointment={appointment} />
            )}
            {isPending && (
              <Button
                onClick={handleConfirm}
                disabled={confirmMutation.isPending}
                size="sm"
                className="bg-teal-500 hover:bg-teal-600 text-white w-full min-h-[48px] text-sm md:w-auto md:min-h-0 md:h-8 md:text-xs"
                data-testid="confirm-btn"
              >
                <CheckCircle className="mr-1.5 h-3.5 w-3.5" />
                Confirm
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              className="border-slate-200 text-slate-700 hover:bg-slate-50 w-full min-h-[48px] text-sm md:w-auto md:min-h-0 md:h-8 md:text-xs"
              data-testid="edit-btn"
              onClick={() => onEdit?.(appointment)}
            >
              <Pencil className="mr-1.5 h-3.5 w-3.5" />
              Edit
            </Button>
            {(isPending || isConfirmed) && (
              <Button
                variant="outline"
                onClick={handleNoShow}
                disabled={noShowMutation.isPending}
                size="sm"
                className="border-slate-200 text-slate-700 hover:bg-slate-50 w-full min-h-[48px] text-sm md:w-auto md:min-h-0 md:h-8 md:text-xs"
                data-testid="no-show-btn"
              >
                <AlertCircle className="mr-1.5 h-3.5 w-3.5" />
                No Show
              </Button>
            )}
            {!isInProgress && !isEnRoute && (
              <Button
                variant="outline"
                onClick={openCancelDialog}
                disabled={cancelMutation.isPending}
                size="sm"
                className="border-red-200 text-red-600 hover:bg-red-50 w-full min-h-[48px] text-sm md:w-auto md:min-h-0 md:h-8 md:text-xs"
                data-testid="cancel-btn"
              >
                <XCircle className="mr-1.5 h-3.5 w-3.5" />
                Cancel
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Timestamps Footer */}
      <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/20">
        <div className="flex items-center justify-between text-[10px] text-slate-400">
          <span>Created: {format(new Date(appointment.created_at), 'PPp')}</span>
          <span>ID: {appointment.id.slice(0, 8)}...</span>
        </div>
      </div>

      <CancelAppointmentDialog
        open={cancelDialogOpen}
        onOpenChange={setCancelDialogOpen}
        customerName={
          customer ? `${customer.first_name} ${customer.last_name}` : null
        }
        customerPhone={customer?.phone ?? null}
        scheduledDate={appointment.scheduled_date}
        timeWindowStart={appointment.time_window_start}
        timeWindowEnd={appointment.time_window_end}
        willNotifyByDefault={willNotifyByDefault}
        onConfirm={handleCancelConfirmed}
        isLoading={cancelMutation.isPending}
      />

      {/* Reschedule-from-request dialog (Gap 11) */}
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

      {/* Send-reminder confirmation dialog (Gap 11) */}
      <Dialog
        open={reminderConfirmOpen}
        onOpenChange={setReminderConfirmOpen}
      >
        <DialogContent
          className="sm:max-w-md"
          data-testid={`send-reminder-confirm-dialog-${appointmentId}`}
        >
          <DialogHeader>
            <DialogTitle>Send reminder SMS?</DialogTitle>
            <DialogDescription>
              This will re-fire the Y/R/C confirmation prompt to the customer.
              Confirm the recipient before sending — on dev, only{' '}
              <strong>+19527373312</strong> may receive real SMS.
            </DialogDescription>
          </DialogHeader>
          <div className="bg-slate-50 rounded-lg p-4 space-y-1 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Customer</span>
              <span className="font-medium text-slate-800">
                {customer
                  ? `${customer.first_name} ${customer.last_name}`
                  : 'Unknown customer'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Phone</span>
              <span className="font-mono text-slate-800">
                {customer?.phone ?? '—'}
              </span>
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
              data-testid={`confirm-send-reminder-${appointmentId}-btn`}
            >
              <Send className="h-3 w-3 mr-1" />
              Send reminder
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Duration Metrics sub-component (Req 37)
// ---------------------------------------------------------------------------

interface DurationMetricsProps {
  enRouteAt: string;
  arrivedAt: string;
  completedAt: string;
}

/** Calculates and displays travel_time, job_duration, total_time for completed appointments. */
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
      <div className="flex items-center gap-2 mb-2">
        <Timer className="h-3.5 w-3.5 text-emerald-600" />
        <p className="text-xs font-semibold uppercase tracking-wider text-emerald-600">
          Duration Metrics
        </p>
      </div>
      <div className="grid grid-cols-3 gap-3 pl-5">
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
