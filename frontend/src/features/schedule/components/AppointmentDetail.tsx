/**
 * Appointment detail component.
 * Displays appointment information and allows status updates.
 */

import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
      <div className="flex items-center justify-center h-48">
        <LoadingSpinner />
      </div>
    );
  }

  if (error || !appointment) {
    return (
      <div className="p-6 text-center">
        <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-3">
          <AlertCircle className="h-6 w-6 text-red-600" />
        </div>
        <p className="text-slate-800 font-medium">Error loading appointment</p>
        <p className="text-sm text-slate-500 mt-1">Please try again later</p>
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
    <div data-testid="appointment-detail" className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      {/* Header Section */}
      <div className="p-6 border-b border-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-violet-100">
              <Calendar className="h-5 w-5 text-violet-600" />
            </div>
            <div>
              <p className="text-lg font-bold text-slate-800">
                {format(new Date(appointment.scheduled_date), 'EEEE, MMMM d, yyyy')}
              </p>
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Clock className="h-4 w-4" />
                <span>
                  {appointment.time_window_start.slice(0, 5)} - {appointment.time_window_end.slice(0, 5)}
                </span>
              </div>
            </div>
          </div>
          <Badge
            className={`${statusConfig.bgColor} ${statusConfig.color} px-3 py-1 rounded-full text-xs font-medium`}
            data-testid={`status-${appointment.status}`}
          >
            {statusConfig.label}
          </Badge>
        </div>
      </div>

      {/* Content Section */}
      <div className="p-6 space-y-6">
        {/* Customer Info Section */}
        <div className="space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Customer & Location</h3>
          <Card className="bg-slate-50 border-slate-100 rounded-2xl">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-white shadow-sm">
                  <MapPin className="h-4 w-4 text-slate-400" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-slate-800">Property Address</p>
                  <p className="text-sm text-slate-500 mt-1">
                    {appointment.route_order ? `Route Order: #${appointment.route_order}` : 'Not assigned to route'}
                  </p>
                  {appointment.estimated_arrival && (
                    <p className="text-sm text-slate-500 mt-1">
                      ETA: {appointment.estimated_arrival.slice(0, 5)}
                    </p>
                  )}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-teal-600 border-teal-200 hover:bg-teal-50"
                >
                  <Navigation className="h-4 w-4 mr-1" />
                  Directions
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Job Info Section */}
        <div className="space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Job Information</h3>
          <Card className="bg-slate-50 border-slate-100 rounded-2xl">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-white shadow-sm">
                    <Briefcase className="h-4 w-4 text-slate-400" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-800">Job Details</p>
                    <p className="text-sm text-slate-500">View full job information</p>
                  </div>
                </div>
                <Link
                  to={`/jobs/${appointment.job_id}`}
                  className="text-teal-600 hover:text-teal-700 text-sm font-medium flex items-center gap-1"
                  data-testid="job-link"
                >
                  View Job →
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Staff Assignment Section */}
        <div className="space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Staff Assignment</h3>
          <Card className="bg-slate-50 border-slate-100 rounded-2xl">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center">
                    <User className="h-5 w-5 text-teal-600" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-800">Assigned Technician</p>
                    <p className="text-sm text-slate-500">View staff profile</p>
                  </div>
                </div>
                <Link
                  to={`/staff/${appointment.staff_id}`}
                  className="text-teal-600 hover:text-teal-700 text-sm font-medium flex items-center gap-1"
                  data-testid="staff-link"
                >
                  View Staff →
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Notes Section */}
        {appointment.notes && (
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Notes</h3>
            <Card className="bg-slate-50 border-slate-100 rounded-2xl">
              <CardContent className="p-4">
                <p className="text-sm text-slate-600">{appointment.notes}</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Timeline Section */}
        {(appointment.arrived_at || appointment.completed_at) && (
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Timeline</h3>
            <div className="space-y-2">
              {appointment.arrived_at && (
                <div className="flex items-center gap-3 text-sm">
                  <div className="w-2 h-2 rounded-full bg-teal-500" />
                  <span className="text-slate-600">
                    Arrived at {format(new Date(appointment.arrived_at), 'h:mm a')}
                  </span>
                </div>
              )}
              {appointment.completed_at && (
                <div className="flex items-center gap-3 text-sm">
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />
                  <span className="text-slate-600">
                    Completed at {format(new Date(appointment.completed_at), 'h:mm a')}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons Section */}
      {!isTerminal && (
        <div className="p-6 border-t border-slate-100 bg-slate-50/50">
          <div className="flex flex-wrap gap-2">
            {isPending && (
              <Button
                onClick={handleConfirm}
                disabled={confirmMutation.isPending}
                className="bg-teal-500 hover:bg-teal-600 text-white"
                data-testid="confirm-btn"
              >
                <CheckCircle className="mr-2 h-4 w-4" />
                Confirm
              </Button>
            )}

            {isConfirmed && (
              <Button
                onClick={handleArrived}
                disabled={arrivedMutation.isPending}
                className="bg-teal-500 hover:bg-teal-600 text-white"
                data-testid="arrived-btn"
              >
                <Play className="mr-2 h-4 w-4" />
                Mark Arrived
              </Button>
            )}

            {isInProgress && (
              <Button
                onClick={handleComplete}
                disabled={completedMutation.isPending}
                className="bg-emerald-500 hover:bg-emerald-600 text-white"
                data-testid="complete-btn"
              >
                <CheckCircle className="mr-2 h-4 w-4" />
                Mark Complete
              </Button>
            )}

            <Button
              variant="outline"
              className="border-slate-200 text-slate-700 hover:bg-slate-50"
              data-testid="edit-btn"
            >
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </Button>

            {(isPending || isConfirmed) && (
              <Button
                variant="outline"
                onClick={handleNoShow}
                disabled={noShowMutation.isPending}
                className="border-slate-200 text-slate-700 hover:bg-slate-50"
                data-testid="no-show-btn"
              >
                <AlertCircle className="mr-2 h-4 w-4" />
                No Show
              </Button>
            )}

            {!isInProgress && (
              <Button
                variant="outline"
                onClick={handleCancel}
                disabled={cancelMutation.isPending}
                className="border-red-200 text-red-600 hover:bg-red-50"
                data-testid="cancel-btn"
              >
                <XCircle className="mr-2 h-4 w-4" />
                Cancel
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Timestamps Footer */}
      <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/30">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>Created: {format(new Date(appointment.created_at), 'PPpp')}</span>
          <span>ID: {appointment.id.slice(0, 8)}...</span>
        </div>
      </div>
    </div>
  );
}
