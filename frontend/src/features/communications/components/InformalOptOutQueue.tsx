/**
 * InformalOptOutQueue (Gap 06).
 *
 * Admin review queue for unacknowledged `INFORMAL_OPT_OUT` alerts.
 * Layout mirrors `NoReplyReviewQueue`: section header with count,
 * per-row actions (Confirm Opt-Out / Dismiss), and a confirm dialog
 * for the destructive Confirm-Opt-Out action surfacing the recipient
 * phone (dev safety pattern).
 */
import { useMemo, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { AlertCircle, Check, X } from 'lucide-react';
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
import { Skeleton } from '@/components/ui/skeleton';
import { getErrorMessage } from '@/core/api/client';

import type { AdminAlert } from '../api/alertsApi';
import {
  useConfirmInformalOptOut,
  useDismissInformalOptOut,
  useInformalOptOutQueue,
} from '../hooks/useInformalOptOutQueue';

export function InformalOptOutQueue() {
  const { data, isLoading, error } = useInformalOptOutQueue();
  const confirmMutation = useConfirmInformalOptOut();
  const dismissMutation = useDismissInformalOptOut();

  const [confirmTarget, setConfirmTarget] = useState<AdminAlert | null>(null);

  const alerts = useMemo(() => data?.items ?? [], [data]);

  const handleConfirm = async () => {
    if (!confirmTarget) return;
    try {
      await confirmMutation.mutateAsync(confirmTarget.id);
      toast.success('Opt-out confirmed. Customer will receive one STOP confirmation.');
      setConfirmTarget(null);
    } catch (err) {
      toast.error(`Confirm failed: ${getErrorMessage(err)}`);
    }
  };

  const handleDismiss = async (alertId: string) => {
    try {
      await dismissMutation.mutateAsync(alertId);
      toast.success('Alert dismissed.');
    } catch (err) {
      toast.error(`Dismiss failed: ${getErrorMessage(err)}`);
    }
  };

  return (
    <div className="space-y-4" data-testid="informal-opt-out-queue">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-amber-100 flex items-center justify-center">
          <AlertCircle className="h-5 w-5 text-amber-600" />
        </div>
        <div className="flex-1">
          <h2 className="text-lg font-semibold text-slate-800">
            Informal opt-out review
          </h2>
          <p className="text-sm text-slate-500">
            Customers who wrote variants of "stop texting me" — confirm or dismiss
            to clear the suppression.
          </p>
        </div>
        <Badge
          variant="secondary"
          className="bg-amber-100 text-amber-700"
          data-testid="informal-opt-out-queue-count"
        >
          {alerts.length} open
        </Badge>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      )}

      {error && (
        <div
          className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          data-testid="informal-opt-out-queue-error"
        >
          Failed to load informal opt-out alerts.
        </div>
      )}

      {!isLoading && !error && alerts.length === 0 && (
        <div
          className="rounded-md border border-slate-100 bg-white p-6 text-center text-sm text-slate-500"
          data-testid="informal-opt-out-queue-empty"
        >
          No informal opt-out alerts are pending. Nicely done.
        </div>
      )}

      {alerts.map((alert) => (
        <InformalOptOutRow
          key={alert.id}
          alert={alert}
          onConfirm={() => setConfirmTarget(alert)}
          onDismiss={() => handleDismiss(alert.id)}
          isDismissing={dismissMutation.isPending}
        />
      ))}

      <Dialog
        open={confirmTarget !== null}
        onOpenChange={(open) => !open && setConfirmTarget(null)}
      >
        <DialogContent data-testid="confirm-opt-out-dialog">
          <DialogHeader>
            <DialogTitle>Confirm SMS opt-out</DialogTitle>
            <DialogDescription>
              This writes a permanent opt-out record, sends one confirmation
              SMS, and blocks all further marketing and reminder sends to the
              customer. Use "Dismiss" instead if this was a false positive.
            </DialogDescription>
          </DialogHeader>
          <div className="text-sm text-slate-700 space-y-1">
            <div className="font-medium">Flagged message:</div>
            <div className="rounded bg-slate-50 p-2 italic text-slate-600">
              {confirmTarget?.message}
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmTarget(null)}
              disabled={confirmMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={confirmMutation.isPending}
              className="bg-red-600 hover:bg-red-700 text-white"
              data-testid="confirm-opt-out-btn"
            >
              {confirmMutation.isPending ? 'Confirming…' : 'Confirm opt-out'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface InformalOptOutRowProps {
  alert: AdminAlert;
  onConfirm: () => void;
  onDismiss: () => void;
  isDismissing: boolean;
}

function InformalOptOutRow({
  alert,
  onConfirm,
  onDismiss,
  isDismissing,
}: InformalOptOutRowProps) {
  const age = formatDistanceToNow(new Date(alert.created_at), { addSuffix: true });
  return (
    <div
      className="flex items-start justify-between gap-3 rounded-lg border border-slate-100 bg-white p-3"
      data-testid={`informal-opt-out-row-${alert.id}`}
    >
      <div className="flex-1 min-w-0">
        <div className="text-xs text-slate-500">
          Flagged {age} · entity: {alert.entity_type}
        </div>
        <div className="mt-1 text-sm text-slate-800 break-words">
          {alert.message}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Button
          size="sm"
          className="bg-red-600 hover:bg-red-700 text-white"
          onClick={onConfirm}
          data-testid={`confirm-opt-out-trigger-${alert.id}`}
        >
          <Check className="h-3 w-3 mr-1" />
          Confirm
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={onDismiss}
          disabled={isDismissing}
          data-testid={`dismiss-opt-out-btn-${alert.id}`}
        >
          <X className="h-3 w-3 mr-1" />
          Dismiss
        </Button>
      </div>
    </div>
  );
}
