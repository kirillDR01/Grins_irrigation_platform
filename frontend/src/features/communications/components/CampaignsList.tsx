/**
 * CampaignsList — campaign list with progress bars, worker health indicator,
 * and Failed/Partial badges for error recovery.
 *
 * Validates: Requirements 15.13, 27, 32, 37
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useCampaigns, useCampaignStats, useWorkerHealth } from '../hooks';
import type { Campaign, CampaignStatus, WorkerHealth } from '../types/campaign';

// --- Status badge mapping (Requirement 27) ---

const STATUS_CONFIG: Record<
  CampaignStatus,
  { label: string; variant: 'default' | 'info' | 'scheduled' | 'success' | 'error' | 'warning' }
> = {
  draft: { label: 'Draft', variant: 'default' },
  scheduled: { label: 'Scheduled', variant: 'scheduled' },
  sending: { label: 'Sending', variant: 'info' },
  sent: { label: 'Sent', variant: 'success' },
  cancelled: { label: 'Cancelled', variant: 'warning' },
};

function CampaignStatusBadge({ status }: { status: CampaignStatus }) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft;
  return (
    <Badge variant={config.variant} data-testid={`status-${status}`}>
      {config.label}
    </Badge>
  );
}

// --- Failure badge overlay (Requirement 37) ---

function FailureBadge({ campaignId }: { campaignId: string }) {
  const { data: stats } = useCampaignStats(campaignId);
  if (!stats || stats.failed === 0) return null;
  const isPartial = stats.sent > 0 && stats.failed > 0;
  return (
    <Badge
      variant={isPartial ? 'warning' : 'error'}
      data-testid={isPartial ? 'partial-badge' : 'failed-badge'}
    >
      {isPartial ? 'Partial' : 'Failed'}
    </Badge>
  );
}

// --- Progress bar ---

function ProgressBar({ sent, failed, total }: { sent: number; failed: number; total: number }) {
  if (total === 0) return null;
  const sentPct = Math.round((sent / total) * 100);
  const failedPct = Math.round((failed / total) * 100);

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 rounded-full bg-slate-100 overflow-hidden">
        <div className="h-full flex">
          <div
            className="bg-emerald-500 transition-all"
            style={{ width: `${sentPct}%` }}
          />
          <div
            className="bg-red-400 transition-all"
            style={{ width: `${failedPct}%` }}
          />
        </div>
      </div>
      <span className="text-xs text-slate-500 whitespace-nowrap">
        {sent}/{total}
      </span>
    </div>
  );
}

// --- Worker health indicator (Requirement 32) ---

function WorkerHealthIndicator({ health }: { health: WorkerHealth | undefined }) {
  if (!health) {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span className="h-2 w-2 rounded-full bg-slate-300" />
        Worker: unknown
      </div>
    );
  }

  const isHealthy = health.status === 'healthy';
  const rl = health.rate_limit;

  return (
    <div className="flex items-center gap-3 text-xs text-slate-500">
      <span className="flex items-center gap-1.5">
        <span
          className={`h-2 w-2 rounded-full ${isHealthy ? 'bg-emerald-500' : 'bg-red-500'}`}
          data-testid="worker-health-dot"
        />
        Worker: {isHealthy ? 'healthy' : 'stale'}
      </span>
      {rl && (
        <span data-testid="rate-limit-status">
          {rl.hourly_used}/{rl.hourly_allowed} this hour
        </span>
      )}
    </div>
  );
}

// --- Campaigns list ---

export interface CampaignsListProps {
  onSelectCampaign?: (campaign: Campaign) => void;
}

export function CampaignsList({ onSelectCampaign }: CampaignsListProps) {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);

  const params = {
    page,
    page_size: 20,
    ...(statusFilter !== 'all' ? { status: statusFilter } : {}),
  };

  const { data, isLoading, error } = useCampaigns(params);
  const { data: workerHealth } = useWorkerHealth();

  const campaigns = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  return (
    <Card data-testid="campaigns-list">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base font-semibold">Text Campaigns</CardTitle>
        <div className="flex items-center gap-4">
          <WorkerHealthIndicator health={workerHealth} />
          <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
            <SelectTrigger className="w-[140px] h-8 text-xs">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="scheduled">Scheduled</SelectItem>
              <SelectItem value="sending">Sending</SelectItem>
              <SelectItem value="sent">Sent</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="py-8 text-center text-sm text-slate-400" data-testid="loading-spinner">
            Loading campaigns…
          </div>
        )}

        {error && (
          <div className="py-8 text-center text-sm text-red-500">
            Failed to load campaigns.
          </div>
        )}

        {!isLoading && !error && campaigns.length === 0 && (
          <div className="py-8 text-center text-sm text-slate-400">
            No campaigns yet.
          </div>
        )}

        {!isLoading && !error && campaigns.length > 0 && (
          <>
            <Table data-testid="campaigns-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-[200px]">Progress</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Scheduled</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {campaigns.map((c) => (
                  <CampaignRow
                    key={c.id}
                    campaign={c}
                    onClick={() => onSelectCampaign?.(c)}
                  />
                ))}
              </TableBody>
            </Table>

            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4 text-xs text-slate-500">
                <span>
                  Page {page} of {totalPages} ({total} campaigns)
                </span>
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

// --- Campaign row (Requirement 37: Failed/Partial badges) ---

function CampaignRow({
  campaign,
  onClick,
}: {
  campaign: Campaign;
  onClick?: () => void;
}) {
  const showProgress = campaign.status === 'sending' || campaign.status === 'sent';

  return (
    <TableRow
      data-testid="campaign-row"
      className="cursor-pointer hover:bg-slate-50"
      onClick={onClick}
    >
      <TableCell className="font-medium">{campaign.name}</TableCell>
      <TableCell>
        <div className="flex items-center gap-1.5">
          <CampaignStatusBadge status={campaign.status} />
          {showProgress && <FailureBadge campaignId={campaign.id} />}
        </div>
      </TableCell>
      <TableCell>
        {showProgress ? (
          <CampaignProgressBar campaignId={campaign.id} />
        ) : (
          <span className="text-xs text-slate-400">—</span>
        )}
      </TableCell>
      <TableCell className="text-xs text-slate-500">
        {formatDate(campaign.created_at)}
      </TableCell>
      <TableCell className="text-xs text-slate-500">
        {campaign.scheduled_at ? formatDate(campaign.scheduled_at) : '—'}
      </TableCell>
    </TableRow>
  );
}

function CampaignProgressBar({ campaignId }: { campaignId: string }) {
  const { data: stats } = useCampaignStats(campaignId);
  if (!stats) return <span className="text-xs text-slate-400">—</span>;
  return <ProgressBar sent={stats.sent} failed={stats.failed} total={stats.total} />;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}
