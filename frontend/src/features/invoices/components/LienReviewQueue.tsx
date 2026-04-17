/**
 * LienReviewQueue — admin-facing queue of customers with past-due
 * invoices eligible for a notice of intent to lien. Replaces the
 * fire-and-forget ``mass_notify('lien_eligible')`` path per CR-5.
 *
 * Each row aggregates a single customer's lien-eligible invoices.
 * The admin reviews the oldest-age + total-past-due numbers and
 * clicks Send Notice (confirm dialog) to dispatch one SMS. Dismiss
 * is client-side only for MVP.
 *
 * Validates: CR-5 (bughunt 2026-04-16).
 */

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, FileText, Mail, Settings as SettingsIcon, XCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useBusinessSettings } from '@/features/settings';

import { useLienCandidates, useSendLienNotice } from '../hooks/useLienReview';
import type { LienCandidate } from '../types';

export function LienReviewQueue() {
  const { data: candidates, isLoading, error } = useLienCandidates();
  const sendMutation = useSendLienNotice();
  // H-12: display the live thresholds so admins see which knobs drive the queue.
  const { data: thresholds } = useBusinessSettings();
  const lienDays = thresholds?.lien_days_past_due ?? 60;
  const lienMin = Number(thresholds?.lien_min_amount ?? 500);

  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [confirmTarget, setConfirmTarget] = useState<LienCandidate | null>(null);

  const visibleCandidates = useMemo(() => {
    if (!candidates) return [];
    return candidates.filter((c) => !dismissed.has(c.customer_id));
  }, [candidates, dismissed]);

  const handleDismiss = (customerId: string) => {
    setDismissed((prev) => {
      const next = new Set(prev);
      next.add(customerId);
      return next;
    });
  };

  const handleSendConfirm = async () => {
    if (!confirmTarget) return;
    try {
      await sendMutation.mutateAsync(confirmTarget.customer_id);
    } finally {
      setConfirmTarget(null);
    }
  };

  if (isLoading) {
    return (
      <div
        className="rounded-xl bg-white p-4 shadow-sm"
        data-testid="lien-queue"
      >
        <div className="mb-3 flex items-center gap-2">
          <FileText className="h-4 w-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-slate-700">
            Lien Review Queue
          </h3>
        </div>
        <div className="space-y-2">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="rounded-xl bg-white p-4 shadow-sm"
        data-testid="lien-queue"
      >
        <div className="mb-3 flex items-center gap-2 text-red-600">
          <AlertTriangle className="h-4 w-4" />
          <span className="text-sm font-semibold">Failed to load lien candidates</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl bg-white p-4 shadow-sm"
      data-testid="lien-queue"
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-amber-600" />
          <h3 className="text-base font-semibold text-slate-800">
            Lien Review Queue
          </h3>
          <Badge variant="secondary">{visibleCandidates.length}</Badge>
        </div>
        <p className="text-xs text-slate-500" data-testid="lien-threshold-note">
          Customers with invoices &gt; {lienDays} days past due and ≥ ${lienMin.toFixed(0)} owed.{' '}
          <Link
            to="/settings?tab=business"
            className="inline-flex items-center gap-1 text-sky-600 hover:underline dark:text-sky-400"
            data-testid="lien-threshold-configure-link"
          >
            <SettingsIcon className="h-3 w-3" />
            configure in Business Settings
          </Link>
        </p>
      </div>

      {visibleCandidates.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-200 py-10 text-center">
          <p className="text-sm text-slate-500">
            No customers in the lien review queue.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {visibleCandidates.map((c) => (
            <div
              key={c.customer_id}
              data-testid={`lien-candidate-row-${c.customer_id}`}
              className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3"
            >
              <div className="min-w-0 flex-1">
                <div className="font-medium text-slate-800">{c.customer_name}</div>
                <div className="mt-1 text-xs text-slate-500">
                  {c.customer_phone || 'No phone on file'}
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Badge variant="destructive">
                    {c.oldest_invoice_age_days} days past due
                  </Badge>
                  <Badge variant="outline">
                    ${Number(c.total_past_due_amount).toFixed(2)} owed
                  </Badge>
                  {c.invoice_numbers.slice(0, 3).map((num) => (
                    <Badge key={num} variant="secondary" className="font-mono text-[10px]">
                      {num}
                    </Badge>
                  ))}
                  {c.invoice_numbers.length > 3 && (
                    <span className="text-xs text-slate-500">
                      +{c.invoice_numbers.length - 3} more
                    </span>
                  )}
                </div>
              </div>
              <div className="flex shrink-0 flex-col gap-2">
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => setConfirmTarget(c)}
                  data-testid={`send-lien-btn-${c.customer_id}`}
                  disabled={
                    !c.customer_phone || sendMutation.isPending
                  }
                >
                  <Mail className="mr-2 h-3.5 w-3.5" />
                  Send Notice
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleDismiss(c.customer_id)}
                  data-testid={`dismiss-lien-btn-${c.customer_id}`}
                >
                  <XCircle className="mr-2 h-3.5 w-3.5" />
                  Dismiss
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog
        open={confirmTarget !== null}
        onOpenChange={(open) => !open && setConfirmTarget(null)}
      >
        <DialogContent data-testid="lien-confirm-dialog">
          <DialogHeader>
            <DialogTitle>Send lien notice?</DialogTitle>
            <DialogDescription>
              The recipient will receive an SMS at{' '}
              <span className="font-mono">
                {confirmTarget?.customer_phone || 'unknown'}
              </span>{' '}
              for invoice
              {confirmTarget && confirmTarget.invoice_numbers.length > 1 ? 's' : ''}{' '}
              {confirmTarget?.invoice_numbers.join(', ')}. This action is logged.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmTarget(null)}
              disabled={sendMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSendConfirm}
              disabled={sendMutation.isPending}
              data-testid="confirm-send-lien-btn"
            >
              {sendMutation.isPending ? 'Sending…' : 'Confirm & send'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
