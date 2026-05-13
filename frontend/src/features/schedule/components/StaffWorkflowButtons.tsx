/**
 * Staff workflow buttons for appointment status transitions (Req 35, 36).
 * Sequential buttons: confirmed → "On My Way" (blue), en_route → "Job Started" (orange),
 * in_progress → "Job Complete" (green, disabled if no payment/invoice).
 */

import { Navigation, Play, CheckCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  useMarkAppointmentArrived,
  useMarkAppointmentCompleted,
} from '../hooks/useAppointmentMutations';
import { useOnMyWay } from '@/features/jobs/hooks';
import type { AppointmentStatus } from '../types';

interface StaffWorkflowButtonsProps {
  appointmentId: string;
  jobId: string;
  status: AppointmentStatus;
  hasPaymentOrInvoice?: boolean;
}

export function StaffWorkflowButtons({
  appointmentId,
  jobId,
  status,
  hasPaymentOrInvoice = false,
}: StaffWorkflowButtonsProps) {
  // Cluster D Item 5: canonical on-the-way is the job-side hook
  // (audited; rolls back `on_my_way_at` on SMS failure per bughunt L-2).
  const onMyWayMutation = useOnMyWay();
  const arrivedMutation = useMarkAppointmentArrived();
  const completedMutation = useMarkAppointmentCompleted();

  const handleOnMyWay = async () => {
    try {
      await onMyWayMutation.mutateAsync(jobId);
      toast.success('Status Updated', { description: 'You are now en route.' });
    } catch {
      toast.error('Error', { description: 'Failed to update status.' });
    }
  };

  const handleJobStarted = async () => {
    try {
      await arrivedMutation.mutateAsync(appointmentId);
      toast.success('Status Updated', { description: 'Job has started.' });
    } catch {
      toast.error('Error', { description: 'Failed to update status.' });
    }
  };

  const handleJobComplete = async () => {
    try {
      await completedMutation.mutateAsync(appointmentId);
      toast.success('Job Complete', { description: 'Appointment marked as completed.' });
    } catch {
      toast.error('Error', { description: 'Failed to complete job.' });
    }
  };

  const isCompleteDisabled = status === 'in_progress' && !hasPaymentOrInvoice;

  return (
    <div data-testid="staff-workflow-buttons" className="flex flex-col gap-2 md:flex-row md:flex-wrap">
      {status === 'confirmed' && (
        <Button
          onClick={handleOnMyWay}
          disabled={onMyWayMutation.isPending}
          size="sm"
          className="bg-blue-500 hover:bg-blue-600 text-white w-full min-h-[48px] text-sm md:w-auto md:min-h-0 md:h-8 md:text-xs"
          data-testid="on-my-way-btn"
        >
          {onMyWayMutation.isPending ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Navigation className="mr-1.5 h-3.5 w-3.5" />
          )}
          On My Way
        </Button>
      )}

      {status === 'en_route' && (
        <Button
          onClick={handleJobStarted}
          disabled={arrivedMutation.isPending}
          size="sm"
          className="bg-orange-500 hover:bg-orange-600 text-white w-full min-h-[48px] text-sm md:w-auto md:min-h-0 md:h-8 md:text-xs"
          data-testid="job-started-btn"
        >
          {arrivedMutation.isPending ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="mr-1.5 h-3.5 w-3.5" />
          )}
          Job Started
        </Button>
      )}

      {status === 'in_progress' && (
        <div className="group relative w-full md:w-auto md:inline-block">
          <Button
            onClick={handleJobComplete}
            disabled={completedMutation.isPending || isCompleteDisabled}
            size="sm"
            className="bg-green-500 hover:bg-green-600 text-white w-full min-h-[48px] text-sm md:w-auto md:min-h-0 md:h-8 md:text-xs disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="job-complete-btn"
          >
            {completedMutation.isPending ? (
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
            ) : (
              <CheckCircle className="mr-1.5 h-3.5 w-3.5" />
            )}
            Job Complete
          </Button>
          {isCompleteDisabled && (
            <div
              className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-slate-800 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10"
              data-testid="complete-tooltip"
            >
              Please collect payment or send an invoice before completing this job
              <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
