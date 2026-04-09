/**
 * FailedRecipientsDetail — per-recipient failure view with retry/cancel actions.
 *
 * Validates: Requirement 37
 */

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import { useCampaignRecipients, useCampaignStats, useRetryFailed, useCancelCampaign } from '../hooks';
import type { Campaign, CampaignRecipient } from '../types/campaign';

export interface FailedRecipientsDetailProps {
  campaign: Campaign;
  onBack: () => void;
}

/**
 * Render a short, human-identifiable stub from a recipient UUID.
 *
 * The backend ``CampaignRecipientResponse`` intentionally does NOT include
 * a phone number (phones live on the related Customer/Lead row), so the
 * detail table cannot surface the actual phone here without a join the
 * list endpoint does not perform. We show the first 8 chars of the
 * recipient row's UUID instead — enough for an operator to cross-reference
 * a specific failed row in the logs without claiming to be a phone.
 */
function shortId(id: string | null | undefined): string {
  if (!id) return '—';
  return id.slice(0, 8);
}

function sourceLabel(r: CampaignRecipient): string {
  if (r.customer_id) return 'customer';
  if (r.lead_id) return 'lead';
  return 'ghost';
}

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, 'error' | 'success' | 'warning' | 'default' | 'info'> = {
    failed: 'error',
    sent: 'success',
    cancelled: 'warning',
    pending: 'default',
    sending: 'info',
  };
  return (
    <Badge variant={variants[status] ?? 'default'} data-testid={`status-${status}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

export function FailedRecipientsDetail({ campaign, onBack }: FailedRecipientsDetailProps) {
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const { data: statsData } = useCampaignStats(campaign.id);
  const { data, isLoading } = useCampaignRecipients(campaign.id, {
    page,
    page_size: 50,
    status: 'failed',
  });

  const retryMutation = useRetryFailed();
  const cancelMutation = useCancelCampaign();

  const recipients = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / 50);

  const allSelected = recipients.length > 0 && recipients.every((r) => selectedIds.has(r.id));

  const toggleAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(recipients.map((r) => r.id)));
    }
  };

  const toggleOne = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleRetry = async () => {
    try {
      const result = await retryMutation.mutateAsync(campaign.id);
      toast.success(`${result.retried_recipients} recipients re-queued for sending.`);
      setSelectedIds(new Set());
    } catch {
      toast.error('Could not retry recipients.');
    }
  };

  const handleCancel = async () => {
    try {
      const result = await cancelMutation.mutateAsync(campaign.id);
      toast.success(`${result.cancelled_recipients} pending recipients cancelled.`);
    } catch {
      toast.error('Could not cancel campaign.');
    }
  };

  const hasFailed = (statsData?.failed ?? 0) > 0;
  const isPartial = hasFailed && (statsData?.sent ?? 0) > 0;

  return (
    <Card data-testid="failed-recipients-detail">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack} data-testid="back-btn">
            ← Back
          </Button>
          <CardTitle className="text-base font-semibold">{campaign.name}</CardTitle>
          {isPartial ? (
            <Badge variant="warning" data-testid="partial-badge">Partial</Badge>
          ) : hasFailed ? (
            <Badge variant="error" data-testid="failed-badge">Failed</Badge>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {hasFailed && (
            <Button
              size="sm"
              onClick={handleRetry}
              disabled={retryMutation.isPending}
              data-testid="retry-selected-btn"
            >
              {retryMutation.isPending ? 'Retrying…' : 'Retry All Failed'}
            </Button>
          )}
          {(campaign.status === 'sending' || campaign.status === 'scheduled') && (
            <Button
              size="sm"
              variant="destructive"
              onClick={handleCancel}
              disabled={cancelMutation.isPending}
              data-testid="cancel-campaign-btn"
            >
              Cancel Campaign
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent>
        {/* Stats summary */}
        {statsData && (
          <div className="mb-4 flex gap-4 text-sm text-slate-600" data-testid="campaign-stats-summary">
            <span>Total: {statsData.total}</span>
            <span className="text-emerald-600">Sent: {statsData.sent}</span>
            <span className="text-red-600">Failed: {statsData.failed}</span>
            {(statsData.opted_out ?? 0) > 0 && (
              <span className="text-amber-600">Opted out: {statsData.opted_out}</span>
            )}
          </div>
        )}

        {isLoading && (
          <div className="py-8 text-center text-sm text-slate-400" data-testid="loading-spinner">
            Loading failed recipients…
          </div>
        )}

        {!isLoading && recipients.length === 0 && (
          <div className="py-8 text-center text-sm text-slate-400">
            No failed recipients.
          </div>
        )}

        {!isLoading && recipients.length > 0 && (
          <>
            <Table data-testid="failed-recipients-table">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <Checkbox
                      checked={allSelected}
                      onCheckedChange={toggleAll}
                      aria-label="Select all"
                    />
                  </TableHead>
                  <TableHead>Recipient ID</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Error</TableHead>
                  <TableHead>Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recipients.map((r) => (
                  <TableRow key={r.id} data-testid="failed-recipient-row">
                    <TableCell>
                      <Checkbox
                        checked={selectedIds.has(r.id)}
                        onCheckedChange={() => toggleOne(r.id)}
                        aria-label={`Select recipient ${shortId(r.id)}`}
                      />
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {shortId(r.id)}
                    </TableCell>
                    <TableCell className="text-xs">{sourceLabel(r)}</TableCell>
                    <TableCell>
                      <StatusBadge status={r.delivery_status} />
                    </TableCell>
                    <TableCell className="text-xs text-slate-500 max-w-[200px] truncate">
                      {r.error_message ?? '—'}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">
                      {r.created_at
                        ? new Date(r.created_at).toLocaleString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            hour: 'numeric',
                            minute: '2-digit',
                          })
                        : '—'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4 text-xs text-slate-500">
                <span>Page {page} of {totalPages} ({total} failed)</span>
                <div className="flex gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
