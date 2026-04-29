// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
/**
 * CampaignResponsesView — summary buckets + drill-down table for poll campaign responses.
 *
 * Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5, 13.6
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
import { ArrowLeft, Download } from 'lucide-react';
import { apiClient } from '@/core/api';
import {
  useCampaignResponseSummary,
  useCampaignResponses,
} from '../hooks/useCampaignResponses';
import type { Campaign, CampaignResponseBucket } from '../types/campaign';

export interface CampaignResponsesViewProps {
  campaign: Campaign;
  onBack: () => void;
}

function downloadCsv(campaignId: string, optionKey?: string) {
  const path = optionKey
    ? `/campaigns/${campaignId}/responses/export.csv?option_key=${optionKey}`
    : `/campaigns/${campaignId}/responses/export.csv`;
  apiClient.get(path, { responseType: 'blob' }).then((resp) => {
    const disposition = resp.headers['content-disposition'] ?? '';
    const match = disposition.match(/filename="(.+?)"/);
    const filename = match?.[1] ?? `campaign_${campaignId}_responses.csv`;
    const url = URL.createObjectURL(resp.data as Blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  });
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

function maskPhone(phone: string): string {
  if (phone.length >= 4) return '***' + phone.slice(-4);
  return '****';
}

export function CampaignResponsesView({
  campaign,
  onBack,
}: CampaignResponsesViewProps) {
  const { data: summary, isLoading: summaryLoading } =
    useCampaignResponseSummary(campaign.id);

  // Drill-down state: which bucket is expanded
  const [drillDown, setDrillDown] = useState<{
    option_key?: string;
    status?: string;
    label: string;
  } | null>(null);

  // Derive counts from buckets
  const parsedCount =
    summary?.buckets
      .filter((b) => b.status === 'parsed')
      .reduce((s, b) => s + b.count, 0) ?? 0;
  const needsReviewCount =
    summary?.buckets
      .filter((b) => b.status === 'needs_review')
      .reduce((s, b) => s + b.count, 0) ?? 0;
  const optedOutCount =
    summary?.buckets
      .filter((b) => b.status === 'opted_out')
      .reduce((s, b) => s + b.count, 0) ?? 0;

  const parsedBuckets =
    summary?.buckets.filter((b) => b.status === 'parsed') ?? [];

  return (
    <div data-testid="campaign-responses-view" className="space-y-4">
      {/* Back + title */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-1" /> Back
        </Button>
        <h2 className="text-lg font-semibold">{campaign.name} — Responses</h2>
      </div>

      {summaryLoading && (
        <div
          className="py-8 text-center text-sm text-slate-400"
          data-testid="loading-spinner"
        >
          Loading responses…
        </div>
      )}

      {summary && (
        <>
          {/* Summary header */}
          <Card>
            <CardContent className="pt-4">
              <div
                className="flex flex-wrap gap-6 text-sm"
                data-testid="response-summary-header"
              >
                <Stat label="Total Sent" value={summary.total_sent} />
                <Stat label="Total Replied" value={summary.total_replied} />
                <Stat label="Parsed" value={parsedCount} />
                <Stat label="Needs Review" value={needsReviewCount} />
                <Stat label="Opted Out" value={optedOutCount} />
              </div>
            </CardContent>
          </Card>

          {/* Per-option buckets */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-base font-semibold">
                Response Buckets
              </CardTitle>
              <a
                href={`/api/v1/campaigns/${campaign.id}/responses/export.csv`}
                download
                data-testid="export-all-csv-btn"
                className="inline-flex items-center gap-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
              >
                <Download className="h-4 w-4 mr-1" /> Export all CSV
              </a>
            </CardHeader>
            <CardContent className="space-y-2">
              {parsedBuckets.map((b) => (
                <BucketRow
                  key={b.option_key}
                  bucket={b}
                  campaignId={campaign.id}
                  onView={() =>
                    setDrillDown({
                      option_key: b.option_key ?? undefined,
                      status: 'parsed',
                      label: b.option_label ?? `Option ${b.option_key}`,
                    })
                  }
                />
              ))}

              {/* Needs review bucket */}
              <div
                className="flex items-center justify-between rounded-md border px-4 py-2"
                data-testid="bucket-needs-review"
              >
                <div className="flex items-center gap-2">
                  <Badge variant="warning">Needs Review</Badge>
                  <span className="text-sm font-medium">
                    {needsReviewCount} responses
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  data-testid="view-needs-review-btn"
                  onClick={() =>
                    setDrillDown({
                      status: 'needs_review',
                      label: 'Needs Review',
                    })
                  }
                >
                  View
                </Button>
              </div>

              {/* Opted out bucket */}
              <div
                className="flex items-center justify-between rounded-md border px-4 py-2"
                data-testid="bucket-opted-out"
              >
                <div className="flex items-center gap-2">
                  <Badge variant="error">Opted Out</Badge>
                  <span className="text-sm font-medium">
                    {optedOutCount} responses
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  data-testid="view-opted-out-btn"
                  onClick={() =>
                    setDrillDown({
                      status: 'opted_out',
                      label: 'Opted Out',
                    })
                  }
                >
                  View
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Drill-down table */}
          {drillDown && (
            <DrillDownTable
              campaignId={campaign.id}
              optionKey={drillDown.option_key}
              status={drillDown.status}
              label={drillDown.label}
              onClose={() => setDrillDown(null)}
            />
          )}
        </>
      )}
    </div>
  );
}

// --- Helpers ---

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-lg font-semibold">{value}</span>
    </div>
  );
}

function BucketRow({
  bucket,
  campaignId,
  onView,
}: {
  bucket: CampaignResponseBucket;
  campaignId: string;
  onView: () => void;
}) {
  return (
    <div
      className="flex items-center justify-between rounded-md border px-4 py-2"
      data-testid={`bucket-option-${bucket.option_key}`}
    >
      <div className="flex items-center gap-3">
        <Badge variant="default">{bucket.option_key}</Badge>
        <span className="text-sm">{bucket.option_label}</span>
        <span className="text-sm font-medium text-slate-600">
          {bucket.count} responses
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          data-testid={`view-option-${bucket.option_key}-btn`}
          onClick={onView}
        >
          View
        </Button>
        <a
          href={`/api/v1/campaigns/${campaignId}/responses/export.csv?option_key=${bucket.option_key}`}
          download
          data-testid={`csv-option-${bucket.option_key}-btn`}
          className="inline-flex items-center gap-1 rounded-md border border-input bg-background px-3 py-1.5 text-sm font-medium hover:bg-accent hover:text-accent-foreground"
        >
          CSV
        </a>
      </div>
    </div>
  );
}

function DrillDownTable({
  campaignId,
  optionKey,
  status,
  label,
  onClose,
}: {
  campaignId: string;
  optionKey?: string;
  status?: string;
  label: string;
  onClose: () => void;
}) {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useCampaignResponses(campaignId, {
    option_key: optionKey,
    status,
    page,
    page_size: 20,
  });

  const rows = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  return (
    <Card data-testid="drilldown-table">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base font-semibold">{label}</CardTitle>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Close
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="py-4 text-center text-sm text-slate-400">
            Loading…
          </div>
        )}

        {!isLoading && rows.length === 0 && (
          <div className="py-4 text-center text-sm text-slate-400">
            No responses.
          </div>
        )}

        {!isLoading && rows.length > 0 && (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Raw Reply</TableHead>
                  <TableHead>Received At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.id} data-testid="response-row">
                    <TableCell>{r.recipient_name ?? '—'}</TableCell>
                    <TableCell>{maskPhone(r.phone)}</TableCell>
                    <TableCell className="max-w-[200px] truncate">
                      {r.raw_reply_body}
                    </TableCell>
                    <TableCell className="text-xs text-slate-500">
                      {formatDate(r.received_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4 text-xs text-slate-500">
                <span>
                  Page {page} of {totalPages} ({total} responses)
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
