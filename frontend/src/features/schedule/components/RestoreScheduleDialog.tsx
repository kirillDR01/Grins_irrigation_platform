/**
 * RestoreScheduleDialog component.
 *
 * Displays audit details for a cleared schedule and allows restoration.
 * Shows the date, appointment count, and list of appointments that will be restored.
 *
 * Validates: Requirements 6.4-6.5
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import { Calendar, Clock, User, Briefcase, RotateCcw, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { useMemo } from 'react';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';

import { scheduleGenerationApi } from '../api/scheduleGenerationApi';
import { appointmentKeys } from '../hooks/useAppointments';
import { jobApi } from '@/features/jobs/api/jobApi';
import { staffApi } from '@/features/staff/api/staffApi';
import { customerApi } from '@/features/customers/api/customerApi';

interface RestoreScheduleDialogProps {
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** The audit ID to show details for */
  auditId: string | null;
}

/**
 * RestoreScheduleDialog shows audit details and allows schedule restoration.
 */
export function RestoreScheduleDialog({
  open,
  onOpenChange,
  auditId,
}: RestoreScheduleDialogProps) {
  const queryClient = useQueryClient();

  // Fetch audit details
  const {
    data: auditDetails,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['schedule', 'clear-audit', auditId],
    queryFn: () => scheduleGenerationApi.getClearDetails(auditId!),
    enabled: !!auditId && open,
  });

  // Fetch all jobs to get job details (max page_size is 100)
  const { data: jobsData } = useQuery({
    queryKey: ['jobs', 'all'],
    queryFn: () => jobApi.list({ page_size: 100 }),
    enabled: !!auditDetails && open,
  });

  // Fetch all staff to get staff names
  const { data: staffData } = useQuery({
    queryKey: ['staff', 'all'],
    queryFn: () => staffApi.list({ page_size: 100 }),
    enabled: !!auditDetails && open,
  });

  // Fetch all customers to get customer names (max page_size is 100)
  const { data: customersData } = useQuery({
    queryKey: ['customers', 'all'],
    queryFn: () => customerApi.list({ page_size: 100 }),
    enabled: !!auditDetails && open,
  });

  // Create lookup maps for jobs, staff, and customers
  const customersMap = useMemo(() => {
    const map = new Map<string, string>();
    if (customersData?.items) {
      for (const customer of customersData.items) {
        map.set(customer.id, `${customer.first_name} ${customer.last_name}`);
      }
    }
    return map;
  }, [customersData]);

  const jobsMap = useMemo(() => {
    const map = new Map<string, { type: string; customerName: string }>();
    if (jobsData?.items) {
      for (const job of jobsData.items) {
        const customerName = customersMap.get(job.customer_id) || 'Unknown Customer';
        map.set(job.id, {
          type: job.job_type || 'Unknown',
          customerName,
        });
      }
    }
    return map;
  }, [jobsData, customersMap]);

  const staffMap = useMemo(() => {
    const map = new Map<string, string>();
    if (staffData?.items) {
      for (const staff of staffData.items) {
        map.set(staff.id, staff.name);
      }
    }
    return map;
  }, [staffData]);

  // Restore mutation
  const restoreMutation = useMutation({
    mutationFn: () => scheduleGenerationApi.restoreSchedule(auditId!),
    onSuccess: (data) => {
      // Invalidate appointment queries to refresh the calendar
      queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
      // Invalidate recent clears to remove this audit from the list
      queryClient.invalidateQueries({ queryKey: ['schedule', 'recent-clears'] });
      // Invalidate jobs to reflect status changes
      queryClient.invalidateQueries({ queryKey: ['jobs'] });

      toast.success('Schedule Restored', {
        description: `Restored ${data.appointments_restored} appointments and updated ${data.jobs_updated} jobs.`,
      });
      onOpenChange(false);
    },
    onError: (error: Error) => {
      toast.error('Restore Failed', {
        description: error.message || 'Failed to restore schedule',
      });
    },
  });

  const handleRestore = () => {
    restoreMutation.mutate();
  };

  const formattedDate = auditDetails
    ? format(new Date(auditDetails.schedule_date), 'EEEE, MMMM d, yyyy')
    : '';

  const clearedTime = auditDetails
    ? format(new Date(auditDetails.cleared_at), 'h:mm a')
    : '';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-lg"
        data-testid="restore-schedule-dialog"
        aria-describedby="restore-schedule-description"
      >
        <DialogHeader className="pb-2">
          <DialogTitle className="flex items-center gap-2">
            <RotateCcw className="h-5 w-5 text-teal-600" />
            Restore Cleared Schedule
          </DialogTitle>
          <DialogDescription id="restore-schedule-description">
            Review the cleared schedule details and restore appointments to the calendar.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="space-y-4 py-6 px-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : error ? (
          <div className="py-6 px-2">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load audit details. Please try again.
              </AlertDescription>
            </Alert>
          </div>
        ) : auditDetails ? (
          <div className="space-y-5 py-4 px-1">
            {/* Schedule Info */}
            <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-lg">
              <Calendar className="h-5 w-5 text-slate-500 flex-shrink-0" />
              <div>
                <p className="font-medium text-slate-900" data-testid="restore-date">
                  {formattedDate}
                </p>
                <p className="text-sm text-slate-500">
                  Cleared at {clearedTime}
                </p>
              </div>
            </div>

            {/* Summary */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-blue-50 rounded-lg">
                <p className="text-2xl font-bold text-blue-700" data-testid="restore-appointment-count">
                  {auditDetails.appointment_count}
                </p>
                <p className="text-sm text-blue-600">Appointments to restore</p>
              </div>
              <div className="p-4 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-700" data-testid="restore-jobs-count">
                  {auditDetails.jobs_reset.length}
                </p>
                <p className="text-sm text-green-600">Jobs to reschedule</p>
              </div>
            </div>

            {/* Appointments List */}
            {auditDetails.appointments_data.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-slate-700 mb-3">
                  Appointments to be restored:
                </h4>
                <ScrollArea className="h-52 rounded-lg border">
                  <div className="p-4 space-y-3">
                    {auditDetails.appointments_data.map((apt, index) => (
                      <AppointmentPreviewItem
                        key={apt.id as string || index}
                        appointment={apt}
                        jobsMap={jobsMap}
                        staffMap={staffMap}
                      />
                    ))}
                  </div>
                </ScrollArea>
              </div>
            )}

            {/* Notes */}
            {auditDetails.notes && (
              <div className="p-4 bg-amber-50 rounded-lg">
                <p className="text-sm text-amber-800">
                  <span className="font-medium">Note:</span> {auditDetails.notes}
                </p>
              </div>
            )}
          </div>
        ) : null}

        <DialogFooter className="pt-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={restoreMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={handleRestore}
            disabled={isLoading || !!error || restoreMutation.isPending}
            className="bg-teal-500 hover:bg-teal-600"
            data-testid="confirm-restore-btn"
          >
            {restoreMutation.isPending ? (
              <>
                <RotateCcw className="mr-2 h-4 w-4 animate-spin" />
                Restoring...
              </>
            ) : (
              <>
                <RotateCcw className="mr-2 h-4 w-4" />
                Restore Schedule
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface AppointmentPreviewItemProps {
  appointment: Record<string, unknown>;
  jobsMap: Map<string, { type: string; customerName: string }>;
  staffMap: Map<string, string>;
}

function AppointmentPreviewItem({ appointment, jobsMap, staffMap }: AppointmentPreviewItemProps) {
  const timeStart = (appointment.time_window_start as string)?.substring(0, 5) || '--:--';
  const timeEnd = (appointment.time_window_end as string)?.substring(0, 5) || '--:--';
  
  const jobId = appointment.job_id as string;
  const staffId = appointment.staff_id as string;
  
  const jobInfo = jobsMap.get(jobId);
  const staffName = staffMap.get(staffId);

  // Format job type for display
  const formatJobType = (type: string) => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div
      className="flex flex-col gap-2 p-3 bg-white rounded-lg border shadow-sm"
      data-testid="restore-appointment-item"
    >
      {/* Time and Job Type Row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-slate-400" />
          <span className="text-sm font-medium text-slate-700">
            {timeStart} - {timeEnd}
          </span>
        </div>
        {jobInfo?.type && (
          <Badge variant="secondary" className="text-xs">
            {formatJobType(jobInfo.type)}
          </Badge>
        )}
      </div>
      
      {/* Customer and Staff Row */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2 text-slate-600">
          <Briefcase className="h-4 w-4 text-blue-500" />
          <span className="truncate max-w-[180px]">
            {jobInfo?.customerName || `Job #${jobId?.substring(0, 8)}`}
          </span>
        </div>
        <div className="flex items-center gap-2 text-slate-500">
          <User className="h-4 w-4 text-green-500" />
          <span className="truncate max-w-[120px]">
            {staffName || `Staff #${staffId?.substring(0, 8)}`}
          </span>
        </div>
      </div>
    </div>
  );
}

export default RestoreScheduleDialog;
