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
      <DialogContent data-testid="clear-day-dialog" className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 p-3">
              <AlertTriangle
                className="h-5 w-5 text-amber-600"
                data-testid="clear-day-warning"
              />
            </div>
            <div>
              <DialogTitle className="text-lg font-bold text-slate-800">
                Clear Day
              </DialogTitle>
              <DialogDescription className="text-sm text-slate-500">
                {formattedDate}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Confirmation message */}
          <p className="text-sm text-slate-600">
            This action will remove all appointments for this day.
          </p>

          {/* Appointment count */}
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-sm font-medium text-slate-700">
              {appointmentCount} appointment{appointmentCount !== 1 ? 's' : ''} will be
              cleared
            </p>
          </div>

          {/* Affected jobs preview */}
          {affectedJobs.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-700">
                Affected appointments:
              </p>
              <ul className="space-y-2" data-testid="affected-jobs-list">
                {jobsToShow.map((job) => (
                  <li
                    key={job.job_id}
                    className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm"
                  >
                    <span className="h-2 w-2 rounded-full bg-amber-500" />
                    <span className="text-slate-700">
                      {job.customer_name} - {job.service_type}
                    </span>
                  </li>
                ))}
              </ul>
              {remainingCount > 0 && (
                <p className="text-sm text-slate-400">
                  and {remainingCount} more...
                </p>
              )}
            </div>
          )}

          {/* Status reset notice */}
          <div
            className="rounded-xl border border-amber-100 bg-amber-50 p-4"
            data-testid="status-reset-notice"
          >
            <p className="text-sm text-amber-700">
              <span className="font-medium">Note:</span> Jobs with &quot;scheduled&quot;
              status will be reset to &quot;approved&quot; so they can be rescheduled.
            </p>
          </div>

          {/* Audit notice */}
          <div
            className="rounded-xl border border-blue-100 bg-blue-50 p-4"
            data-testid="audit-notice"
          >
            <p className="text-sm text-blue-700">
              This action will be logged for audit purposes. You can view cleared
              schedules in the &quot;Recently Cleared&quot; section.
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
            data-testid="clear-day-cancel"
            className="border-slate-200 text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isLoading}
            data-testid="clear-day-confirm"
            className="bg-red-500 hover:bg-red-600"
          >
            {isLoading ? 'Clearing...' : 'Clear Day'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
