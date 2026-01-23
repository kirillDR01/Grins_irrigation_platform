/**
 * Appointment detail component.
 * Displays appointment information and allows status updates.
 */

import { format } from 'date-fns';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  Calendar,
  User,
  Briefcase,
  MapPin,
  CheckCircle,
  XCircle,
  AlertCircle,
  Play,
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
      <div className="p-4 text-center text-red-600">
        Error loading appointment details
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
    <div data-testid="appointment-detail" className="space-y-6">
      {/* Status Badge */}
      <div className="flex items-center justify-between">
        <Badge
          className={`${statusConfig.bgColor} ${statusConfig.color} text-sm px-3 py-1`}
          data-testid={`status-${appointment.status}`}
        >
          {statusConfig.label}
        </Badge>
        <span className="text-sm text-muted-foreground">
          ID: {appointment.id.slice(0, 8)}...
        </span>
      </div>

      {/* Main Info */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              Date & Time
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-semibold">
              {format(new Date(appointment.scheduled_date), 'EEEE, MMMM d, yyyy')}
            </p>
            <p className="text-muted-foreground">
              {appointment.time_window_start.slice(0, 5)} -{' '}
              {appointment.time_window_end.slice(0, 5)}
            </p>
            {appointment.estimated_arrival && (
              <p className="text-sm text-muted-foreground mt-1">
                ETA: {appointment.estimated_arrival.slice(0, 5)}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <MapPin className="h-4 w-4" />
              Route Info
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-semibold">
              Route Order: {appointment.route_order ?? 'Not assigned'}
            </p>
            {appointment.arrived_at && (
              <p className="text-sm text-muted-foreground">
                Arrived: {format(new Date(appointment.arrived_at), 'h:mm a')}
              </p>
            )}
            {appointment.completed_at && (
              <p className="text-sm text-muted-foreground">
                Completed: {format(new Date(appointment.completed_at), 'h:mm a')}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* References */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Briefcase className="h-4 w-4" />
              Job
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Link
              to={`/jobs/${appointment.job_id}`}
              className="text-primary hover:underline font-mono text-sm"
              data-testid="job-link"
            >
              View Job →
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <User className="h-4 w-4" />
              Staff
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Link
              to={`/staff/${appointment.staff_id}`}
              className="text-primary hover:underline font-mono text-sm"
              data-testid="staff-link"
            >
              View Staff →
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Notes */}
      {appointment.notes && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">{appointment.notes}</p>
          </CardContent>
        </Card>
      )}

      <Separator />

      {/* Actions */}
      {!isTerminal && (
        <div className="flex flex-wrap gap-2">
          {isPending && (
            <Button
              onClick={handleConfirm}
              disabled={confirmMutation.isPending}
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
              className="bg-green-600 hover:bg-green-700"
              data-testid="complete-btn"
            >
              <CheckCircle className="mr-2 h-4 w-4" />
              Mark Complete
            </Button>
          )}

          {(isPending || isConfirmed) && (
            <Button
              variant="outline"
              onClick={handleNoShow}
              disabled={noShowMutation.isPending}
              data-testid="no-show-btn"
            >
              <AlertCircle className="mr-2 h-4 w-4" />
              No Show
            </Button>
          )}

          {!isInProgress && (
            <Button
              variant="destructive"
              onClick={handleCancel}
              disabled={cancelMutation.isPending}
              data-testid="cancel-btn"
            >
              <XCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          )}
        </div>
      )}

      {/* Timestamps */}
      <div className="text-xs text-muted-foreground">
        <p>Created: {format(new Date(appointment.created_at), 'PPpp')}</p>
        <p>Updated: {format(new Date(appointment.updated_at), 'PPpp')}</p>
      </div>
    </div>
  );
}
