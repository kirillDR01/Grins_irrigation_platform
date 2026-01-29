/**
 * ClearDayDialog component.
 * Confirmation dialog for clearing all appointments on a specific day.
 */

import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { format } from 'date-fns';

interface AffectedJob {
  job_id: string;
  customer_name: string;
  service_type: string;
}

interface ClearDayDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  date: Date;
  appointmentCount: number;
  affectedJobs: AffectedJob[];
  onConfirm: () => void;
  isLoading?: boolean;
}

const MAX_JOBS_PREVIEW = 5;

export function ClearDayDialog({
  open,
  onOpenChange,
  date,
  appointmentCount,
  affectedJobs,
  onConfirm,
  isLoading = false,
}: ClearDayDialogProps) {
  const formattedDate = format(date, 'EEEE, MMMM d, yyyy');
  const jobsToShow = affectedJobs.slice(0, MAX_JOBS_PREVIEW);
  const remainingCount = affectedJobs.length - MAX_JOBS_PREVIEW;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="clear-day-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle
              className="h-5 w-5 text-destructive"
              data-testid="clear-day-warning"
            />
            Clear Schedule for {formattedDate}
          </DialogTitle>
          <DialogDescription>
            This action will remove all appointments for this day.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Appointment count */}
          <div className="rounded-md bg-muted p-3">
            <p className="text-sm font-medium">
              {appointmentCount} appointment{appointmentCount !== 1 ? 's' : ''} will be
              deleted
            </p>
          </div>

          {/* Affected jobs preview */}
          {affectedJobs.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-muted-foreground">
                Affected jobs:
              </p>
              <ul className="space-y-1 text-sm" data-testid="affected-jobs-list">
                {jobsToShow.map((job) => (
                  <li key={job.job_id} className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground" />
                    <span>
                      {job.customer_name} - {job.service_type}
                    </span>
                  </li>
                ))}
              </ul>
              {remainingCount > 0 && (
                <p className="text-sm text-muted-foreground">
                  and {remainingCount} more...
                </p>
              )}
            </div>
          )}

          {/* Status reset notice */}
          <div
            className="rounded-md border border-yellow-200 bg-yellow-50 p-3"
            data-testid="status-reset-notice"
          >
            <p className="text-sm text-yellow-800">
              <strong>Note:</strong> Jobs with &quot;scheduled&quot; status will be reset
              to &quot;approved&quot; so they can be rescheduled.
            </p>
          </div>

          {/* Audit notice */}
          <div
            className="rounded-md border border-blue-200 bg-blue-50 p-3"
            data-testid="audit-notice"
          >
            <p className="text-sm text-blue-800">
              This action will be logged for audit purposes. You can view cleared
              schedules in the &quot;Recently Cleared&quot; section.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
            data-testid="clear-day-cancel"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isLoading}
            data-testid="clear-day-confirm"
          >
            {isLoading ? 'Clearing...' : 'Clear Schedule'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
