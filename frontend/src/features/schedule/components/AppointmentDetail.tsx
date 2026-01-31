/**
 * Appointment detail component.
 * Displays appointment information and allows status updates.
 */

import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Calendar,
  User,
  Briefcase,
  MapPin,
  CheckCircle,
  XCircle,
  AlertCircle,
  Play,
  Clock,
  Navigation,
  Pencil,
} from 'lucide-react';
import { useAppointment } from '../hooks/useAppointments';
import {
  useConfirmAppointment,
  useMarkAppointmentArrived,
  useMarkAppointmentCompleted,
  useCancelAppointment,
  useMarkAppointmentNoShow,
} from '../hooks/useAppointmentMutations';
import { appointmentStatusConfig } from '../types';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';

interface AppointmentDetailProps {
  appointmentId: string;
  onClose?: () => void;
}

export function AppointmentDetail({
  appointmentId,
  onClose,
}: AppointmentDetailProps) {
  const { data: appointment, isLoading, error } = useAppointment(appointmentId);

  const confirmMutation = useConfirmAppointment();
  const arrivedMutation = useMarkAppointmentArrived();
  const completedMutation = useMarkAppointmentCompleted();
  const cancelMutation = useCancelAppointment();
  const noShowMutation = useMarkAppointmentNoShow();

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
  const isConfirmed = appointment.status === 'confirmed';
  const isInProgress = appointment.status === 'in_progress';
  const isTerminal = ['completed', 'cancelled', 'no_show'].includes(
    appointment.status
  );

  const handleConfirm = async () => {
    await confirmMutation.mutateAsync(appointmentId);
  };

  const handleArrived = async () => {
    await arrivedMutation.mutateAsync(appointmentId);
  };

  const handleComplete = async () => {
    await completedMutation.mutateAsync(appointmentId);
  };

  const handleCancel = async () => {
    await cancelMutation.mutateAsync(appointmentId);
    onClose?.();
  };

  const handleNoShow = async () => {
    await noShowMutation.mutateAsync(appointmentId);
  };

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
                {format(new Date(appointment.scheduled_date), 'EEEE, MMMM d, yyyy')}
              </p>
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <Clock className="h-3 w-3" />
                <span>
                  {appointment.time_window_start.slice(0, 5)} - {appointment.time_window_end.slice(0, 5)}
                </span>
              </div>
            </div>
          </div>
          <Badge
            className={`${statusConfig.bgColor} ${statusConfig.color} px-2 py-0.5 rounded-full text-xs font-medium`}
            data-testid={`status-${appointment.status}`}
          >
            {statusConfig.label}
          </Badge>
        </div>
      </div>

      {/* Content Section - Compact Grid Layout */}
      <div className="p-4 space-y-3">
        {/* Customer & Location */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-white shadow-sm">
              <MapPin className="h-3.5 w-3.5 text-slate-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-800">Property Address</p>
              <p className="text-xs text-slate-500">
                {appointment.route_order ? `Route #${appointment.route_order}` : 'Not in route'}
                {appointment.estimated_arrival && ` • ETA: ${appointment.estimated_arrival.slice(0, 5)}`}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="text-teal-600 border-teal-200 hover:bg-teal-50 h-7 text-xs px-2"
          >
            <Navigation className="h-3 w-3 mr-1" />
            Directions
          </Button>
        </div>

        {/* Job & Staff - Side by Side */}
        <div className="grid grid-cols-2 gap-3">
          {/* Job Info */}
          <div className="p-3 bg-slate-50 rounded-xl">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-1.5 rounded-lg bg-white shadow-sm">
                <Briefcase className="h-3.5 w-3.5 text-slate-400" />
              </div>
              <p className="text-sm font-medium text-slate-800">Job</p>
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
              <p className="text-sm font-medium text-slate-800">Staff</p>
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

        {/* Notes Section - Compact */}
        {appointment.notes && (
          <div className="p-3 bg-slate-50 rounded-xl">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Notes</p>
            <p className="text-xs text-slate-600 line-clamp-2">{appointment.notes}</p>
          </div>
        )}

        {/* Timeline Section - Inline */}
        {(appointment.arrived_at || appointment.completed_at) && (
          <div className="flex items-center gap-4 text-xs text-slate-500">
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
      </div>

      {/* Action Buttons Section - Compact */}
      {!isTerminal && (
        <div className="px-4 py-3 border-t border-slate-100 bg-slate-50/30">
          <div className="flex flex-wrap gap-2">
            {isPending && (
              <Button
                onClick={handleConfirm}
                disabled={confirmMutation.isPending}
                size="sm"
                className="bg-teal-500 hover:bg-teal-600 text-white h-8 text-xs"
                data-testid="confirm-btn"
              >
                <CheckCircle className="mr-1.5 h-3.5 w-3.5" />
                Confirm
              </Button>
            )}

            {isConfirmed && (
              <Button
                onClick={handleArrived}
                disabled={arrivedMutation.isPending}
                size="sm"
                className="bg-teal-500 hover:bg-teal-600 text-white h-8 text-xs"
                data-testid="arrived-btn"
              >
                <Play className="mr-1.5 h-3.5 w-3.5" />
                Mark Arrived
              </Button>
            )}

            {isInProgress && (
              <Button
                onClick={handleComplete}
                disabled={completedMutation.isPending}
                size="sm"
                className="bg-emerald-500 hover:bg-emerald-600 text-white h-8 text-xs"
                data-testid="complete-btn"
              >
                <CheckCircle className="mr-1.5 h-3.5 w-3.5" />
                Complete
              </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              className="border-slate-200 text-slate-700 hover:bg-slate-50 h-8 text-xs"
              data-testid="edit-btn"
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
                className="border-slate-200 text-slate-700 hover:bg-slate-50 h-8 text-xs"
                data-testid="no-show-btn"
              >
                <AlertCircle className="mr-1.5 h-3.5 w-3.5" />
                No Show
              </Button>
            )}

            {!isInProgress && (
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={cancelMutation.isPending}
                size="sm"
                className="border-red-200 text-red-600 hover:bg-red-50 h-8 text-xs"
                data-testid="cancel-btn"
              >
                <XCircle className="mr-1.5 h-3.5 w-3.5" />
                Cancel
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Timestamps Footer - Minimal */}
      <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/20">
        <div className="flex items-center justify-between text-[10px] text-slate-400">
          <span>Created: {format(new Date(appointment.created_at), 'PPp')}</span>
          <span>ID: {appointment.id.slice(0, 8)}...</span>
        </div>
      </div>
    </div>
  );
}
