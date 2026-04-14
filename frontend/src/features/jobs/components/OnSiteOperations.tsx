import { useState, useCallback } from 'react';
import {
  Navigation,
  Play,
  CheckCircle2,
  Star,
  Camera,
  AlertTriangle,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import {
  useOnMyWay,
  useJobStarted,
  useCompleteJobWithWarning,
  useUploadJobPhoto,
  useReviewPush,
} from '../hooks';
import type { Job } from '../types';

interface OnSiteOperationsProps {
  job: Job;
}

export function OnSiteOperations({ job }: OnSiteOperationsProps) {
  const [showPaymentWarning, setShowPaymentWarning] = useState(false);

  const onMyWayMutation = useOnMyWay();
  const jobStartedMutation = useJobStarted();
  const completeMutation = useCompleteJobWithWarning();
  const uploadPhotoMutation = useUploadJobPhoto();
  const reviewPushMutation = useReviewPush();

  const isCompleted = job.status === 'completed';
  const isCancelled = job.status === 'cancelled';
  const isTerminal = isCompleted || isCancelled;

  const handleOnMyWay = async () => {
    try {
      await onMyWayMutation.mutateAsync(job.id);
      toast.success('On My Way SMS sent to customer');
    } catch {
      toast.error('Failed to send On My Way notification');
    }
  };

  const handleJobStarted = async () => {
    try {
      await jobStartedMutation.mutateAsync(job.id);
      toast.success('Job started — timestamp logged');
    } catch {
      toast.error('Failed to log job start');
    }
  };

  const handleComplete = async () => {
    try {
      const result = await completeMutation.mutateAsync({ id: job.id });
      if (!result.completed && result.warning) {
        setShowPaymentWarning(true);
      } else {
        toast.success('Job marked as complete');
      }
    } catch {
      toast.error('Failed to complete job');
    }
  };

  const handleForceComplete = async () => {
    setShowPaymentWarning(false);
    try {
      const result = await completeMutation.mutateAsync({ id: job.id, force: true });
      if (result.completed) {
        toast.success('Job completed (without payment/invoice)');
      }
    } catch {
      toast.error('Failed to force-complete job');
    }
  };

  const handlePhotoUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      try {
        await uploadPhotoMutation.mutateAsync({ id: job.id, file });
        toast.success('Photo uploaded');
      } catch {
        toast.error('Failed to upload photo');
      }
      e.target.value = '';
    },
    [uploadPhotoMutation, job.id],
  );

  const handleReviewPush = async () => {
    try {
      const result = await reviewPushMutation.mutateAsync(job.id);
      if (result.sms_sent) {
        toast.success('Google review request sent');
      } else {
        toast.error('Failed to send review request');
      }
    } catch {
      toast.error('Failed to send review request');
    }
  };

  const anyPending =
    onMyWayMutation.isPending ||
    jobStartedMutation.isPending ||
    completeMutation.isPending;

  return (
    <>
      <div data-testid="on-site-operations">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
          <Navigation className="h-3.5 w-3.5" />
          On-Site Operations
        </p>

        {/* Status progression buttons — mobile: stacked vertically at top (Req 12.1, 12.2) */}
        {!isTerminal && (
          <div
            className="flex flex-col gap-3 mb-3 order-first md:flex-row md:flex-wrap md:gap-2 md:order-none"
            data-testid="on-site-status-buttons"
          >
            <Button
              className="w-full min-h-[48px] text-base bg-blue-500 hover:bg-blue-600 text-white md:w-auto md:min-h-0 md:text-sm"
              onClick={handleOnMyWay}
              disabled={anyPending || !!job.on_my_way_at}
              data-testid="on-my-way-btn"
            >
              <Navigation className="mr-1.5 h-4 w-4 md:h-3.5 md:w-3.5" />
              {job.on_my_way_at ? 'On My Way ✓' : 'On My Way'}
            </Button>
            <Button
              className="w-full min-h-[48px] text-base bg-orange-500 hover:bg-orange-600 text-white md:w-auto md:min-h-0 md:text-sm"
              onClick={handleJobStarted}
              disabled={anyPending || !!job.started_at}
              data-testid="job-started-btn"
            >
              <Play className="mr-1.5 h-4 w-4 md:h-3.5 md:w-3.5" />
              {job.started_at ? 'Job Started ✓' : 'Job Started'}
            </Button>
            <Button
              className="w-full min-h-[48px] text-base bg-emerald-500 hover:bg-emerald-600 text-white md:w-auto md:min-h-0 md:text-sm"
              onClick={handleComplete}
              disabled={anyPending}
              data-testid="job-complete-btn"
            >
              <CheckCircle2 className="mr-1.5 h-4 w-4 md:h-3.5 md:w-3.5" />
              Job Complete
            </Button>
          </div>
        )}

        <Separator className="my-3" />

        {/* Photo upload + Review push */}
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            className="relative"
            disabled={uploadPhotoMutation.isPending}
            data-testid="upload-job-photo-btn"
            asChild
          >
            <label className="cursor-pointer">
              <Camera className="mr-1.5 h-3.5 w-3.5" />
              {uploadPhotoMutation.isPending ? 'Uploading...' : 'Add Photo'}
              <input
                type="file"
                className="hidden"
                accept="image/*"
                capture="environment"
                onChange={handlePhotoUpload}
                data-testid="job-photo-input"
              />
            </label>
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleReviewPush}
            disabled={reviewPushMutation.isPending}
            data-testid="review-push-btn"
          >
            <Star className="mr-1.5 h-3.5 w-3.5" />
            {reviewPushMutation.isPending ? 'Sending...' : 'Google Review'}
          </Button>
        </div>
      </div>

      {/* Payment Warning Modal — mobile-friendly sizing (Req 12.5) */}
      <Dialog open={showPaymentWarning} onOpenChange={setShowPaymentWarning}>
        <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-md" data-testid="payment-warning-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />
              No Payment or Invoice on File
            </DialogTitle>
            <DialogDescription>
              This job has no payment collected and no invoice sent. Are you sure
              you want to mark it as complete?
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col-reverse gap-2 mt-4 sm:flex-row sm:justify-end">
            <Button
              variant="outline"
              className="w-full sm:w-auto"
              onClick={() => setShowPaymentWarning(false)}
              data-testid="payment-warning-cancel-btn"
            >
              Cancel
            </Button>
            <Button
              className="w-full sm:w-auto bg-amber-500 hover:bg-amber-600 text-white"
              onClick={handleForceComplete}
              disabled={completeMutation.isPending}
              data-testid="complete-anyway-btn"
            >
              {completeMutation.isPending ? 'Completing...' : 'Complete Anyway'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
