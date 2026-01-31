/**
 * ClearDayDialog component.
 * Confirmation dialog for clearing all appointments on a specific day.
 */

import { AlertTriangle, Clock, User } from 'lucide-react';
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
import { ScrollArea } from '@/components/ui/scroll-area';

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

const MAX_JOBS_PREVIEW = 8;

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
      <DialogContent data-testid="clear-day-dialog" className="sm:max-w-lg p-0 gap-0 overflow-hidden">
        {/* Header with warning icon */}
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-100 shrink-0">
              <AlertTriangle
                className="h-6 w-6 text-amber-600"
                data-testid="clear-day-warning"
              />
            </div>
            <div>
              <DialogTitle className="text-xl font-bold text-slate-800">
                Clear Day
              </DialogTitle>
              <DialogDescription className="text-sm text-slate-500 mt-1">
                {formattedDate}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Content area with proper padding */}
        <div className="px-6 py-5 space-y-5">
          {/* Confirmation message */}
          <p className="text-sm text-slate-600 leading-relaxed">
            This action will remove all appointments scheduled for this day. 
            The associated jobs will be reset so they can be rescheduled.
          </p>

          {/* Appointment count card */}
          <div className="rounded-xl bg-red-50 border border-red-100 p-4">
            <p className="text-base font-semibold text-red-700">
              {appointmentCount} appointment{appointmentCount !== 1 ? 's' : ''} will be cleared
            </p>
          </div>

          {/* Affected appointments preview */}
          {affectedJobs.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm font-semibold text-slate-700">
                Affected Appointments:
              </p>
              <ScrollArea className={affectedJobs.length > 5 ? 'h-48' : ''}>
                <ul className="space-y-2 pr-2" data-testid="affected-jobs-list">
                  {jobsToShow.map((job, index) => (
                    <li
                      key={`${job.job_id}-${index}`}
                      className="flex items-center gap-3 rounded-lg bg-slate-50 border border-slate-100 px-4 py-3"
                    >
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-100 shrink-0">
                        <User className="h-4 w-4 text-amber-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800 truncate">
                          {job.customer_name}
                        </p>
                        <div className="flex items-center gap-1 text-xs text-slate-500 mt-0.5">
                          <Clock className="h-3 w-3" />
                          <span>{job.service_type}</span>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </ScrollArea>
              {remainingCount > 0 && (
                <p className="text-sm text-slate-400 pl-1">
                  and {remainingCount} more appointment{remainingCount !== 1 ? 's' : ''}...
                </p>
              )}
            </div>
          )}

          {/* Info notices */}
          <div className="space-y-3">
            {/* Status reset notice */}
            <div
              className="rounded-xl border border-amber-200 bg-amber-50 p-4"
              data-testid="status-reset-notice"
            >
              <p className="text-sm text-amber-800">
                <span className="font-semibold">Note:</span> Jobs with &quot;scheduled&quot;
                status will be reset to &quot;approved&quot; so they can be rescheduled.
              </p>
            </div>

            {/* Audit notice */}
            <div
              className="rounded-xl border border-blue-200 bg-blue-50 p-4"
              data-testid="audit-notice"
            >
              <p className="text-sm text-blue-800">
                This action will be logged for audit purposes. You can view cleared
                schedules in the &quot;Recently Cleared&quot; section.
              </p>
            </div>
          </div>
        </div>

        {/* Footer with buttons */}
        <DialogFooter className="px-6 py-4 border-t border-slate-100 bg-slate-50 gap-3 sm:gap-3">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
            data-testid="clear-day-cancel"
            className="border-slate-300 text-slate-700 hover:bg-slate-100 px-6"
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={onConfirm}
            disabled={isLoading}
            data-testid="clear-day-confirm"
            className="bg-red-500 hover:bg-red-600 px-6"
          >
            {isLoading ? 'Clearing...' : 'Clear Day'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
