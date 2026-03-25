/**
 * Admin-side estimate detail page (Req 83).
 * Shows estimate info, line items, tiers, activity timeline, linked documents, and action buttons.
 */

import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Edit,
  Send,
  XCircle,
  Briefcase,
  FileText,
  Download,
  Clock,
  Calendar,
  Mail,
  Phone,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { LoadingSpinner, ErrorMessage } from '@/shared/components';
import {
  useEstimateDetail,
  useSendEstimate,
  useCancelEstimate,
  useCreateJobFromEstimate,
} from '../hooks';
import { ESTIMATE_STATUS_CONFIG } from '../types';
import type {
  EstimateStatus,
  EstimateLineItem,
  EstimateTier,
  ActivityEvent,
  LinkedDocument,
} from '../types';

interface EstimateDetailProps {
  estimateId?: string;
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  created: 'Estimate Created',
  sent: 'Estimate Sent',
  viewed: 'Viewed by Customer',
  approved: 'Approved',
  rejected: 'Rejected',
  follow_up_sent: 'Follow-Up Sent',
  follow_up_scheduled: 'Follow-Up Scheduled',
  cancelled: 'Cancelled',
};

function StatusBadge({ status }: { status: EstimateStatus }) {
  const config = ESTIMATE_STATUS_CONFIG[status] ?? ESTIMATE_STATUS_CONFIG.draft;
  return (
    <Badge
      className={`${config.className} border-0 font-medium`}
      data-testid={`status-${status}`}
    >
      {config.label}
    </Badge>
  );
}

function formatCurrency(amount: number): string {
  return `$${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function LineItemsTable({ items }: { items: EstimateLineItem[] }) {
  return (
    <Table data-testid="line-items-table">
      <TableHeader>
        <TableRow>
          <TableHead>Item</TableHead>
          <TableHead>Description</TableHead>
          <TableHead className="text-right">Qty</TableHead>
          <TableHead className="text-right">Unit Price</TableHead>
          <TableHead className="text-right">Total</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item, idx) => (
          <TableRow key={idx} data-testid={`line-item-row-${idx}`}>
            <TableCell className="font-medium">{item.item}</TableCell>
            <TableCell className="text-slate-500">{item.description}</TableCell>
            <TableCell className="text-right">{item.quantity}</TableCell>
            <TableCell className="text-right">{formatCurrency(item.unit_price)}</TableCell>
            <TableCell className="text-right font-medium">
              {formatCurrency(item.unit_price * item.quantity)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function TierSection({ tiers }: { tiers: EstimateTier[] }) {
  return (
    <div className="space-y-4" data-testid="tier-options">
      <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">
        Tier Options
      </h3>
      {tiers.map((tier) => (
        <Card key={tier.name} data-testid={`tier-${tier.name}`}>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm capitalize">
              {tier.name} — {formatCurrency(tier.total)}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3">
            <LineItemsTable items={tier.line_items} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ActivityTimeline({ events }: { events: ActivityEvent[] }) {
  return (
    <div data-testid="activity-timeline" className="space-y-3">
      {events.length === 0 ? (
        <p className="text-sm text-slate-400 py-4 text-center">No activity recorded yet.</p>
      ) : (
        events.map((event, idx) => (
          <div
            key={idx}
            className="flex items-start gap-3 relative"
            data-testid={`timeline-event-${idx}`}
          >
            <div className="flex flex-col items-center">
              <div className="w-2.5 h-2.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />
              {idx < events.length - 1 && (
                <div className="w-px h-full bg-slate-200 min-h-[24px]" />
              )}
            </div>
            <div className="pb-4">
              <p className="text-sm font-medium text-slate-700">
                {EVENT_TYPE_LABELS[event.event_type] ?? event.event_type}
              </p>
              <p className="text-xs text-slate-400">
                {formatDateTime(event.timestamp)}
                {event.actor && ` · ${event.actor}`}
              </p>
              {event.details && (
                <p className="text-xs text-slate-500 mt-0.5">{event.details}</p>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function LinkedDocumentsSection({ documents }: { documents: LinkedDocument[] }) {
  if (documents.length === 0) return null;

  const typeIcons: Record<string, typeof FileText> = {
    pdf: FileText,
    contract: FileText,
    media: FileText,
  };

  return (
    <div data-testid="linked-documents" className="space-y-2">
      {documents.map((doc, idx) => {
        const Icon = typeIcons[doc.type] ?? FileText;
        return (
          <a
            key={idx}
            href={doc.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
            data-testid={`linked-doc-${idx}`}
          >
            <Icon className="h-4 w-4 text-slate-500 shrink-0" />
            <span className="text-sm font-medium text-slate-700 truncate">{doc.name}</span>
            <Download className="h-4 w-4 text-slate-400 ml-auto shrink-0" />
          </a>
        );
      })}
    </div>
  );
}

export function EstimateDetail({ estimateId: propId }: EstimateDetailProps) {
  const { id: paramId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const id = propId || paramId || '';

  const { data: estimate, isLoading, error } = useEstimateDetail(id);
  const sendEstimate = useSendEstimate();
  const cancelEstimate = useCancelEstimate();
  const createJob = useCreateJobFromEstimate();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  if (!estimate) return <ErrorMessage error={new Error('Estimate not found')} />;

  const status = estimate.status as EstimateStatus;
  const canEdit = status === 'draft';
  const canSend = status === 'draft' || status === 'sent';
  const canCancel = !['approved', 'rejected', 'cancelled', 'expired'].includes(status);
  const canCreateJob = status === 'approved';

  const handleSend = async () => {
    try {
      await sendEstimate.mutateAsync(id);
      toast.success('Estimate sent to customer');
    } catch {
      toast.error('Failed to send estimate');
    }
  };

  const handleCancel = async () => {
    try {
      await cancelEstimate.mutateAsync(id);
      toast.success('Estimate cancelled');
    } catch {
      toast.error('Failed to cancel estimate');
    }
  };

  const handleCreateJob = async () => {
    try {
      const result = await createJob.mutateAsync(id);
      toast.success('Job created from estimate');
      navigate(`/jobs/${result.job_id}`);
    } catch {
      toast.error('Failed to create job');
    }
  };

  return (
    <div data-testid="estimate-detail" className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(-1)}
            data-testid="back-btn"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <div>
            <h1 className="text-xl font-bold text-slate-800" data-testid="estimate-number">
              {estimate.estimate_number}
            </h1>
            <p className="text-sm text-slate-500">
              Created {formatDate(estimate.created_at)}
            </p>
          </div>
          <StatusBadge status={status} />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2" data-testid="action-buttons">
          {canEdit && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/sales?edit_estimate=${id}`)}
              data-testid="edit-estimate-btn"
            >
              <Edit className="h-4 w-4 mr-1" />
              Edit
            </Button>
          )}
          {canSend && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleSend}
              disabled={sendEstimate.isPending}
              data-testid="send-estimate-btn"
            >
              <Send className="h-4 w-4 mr-1" />
              {status === 'sent' ? 'Resend' : 'Send'}
            </Button>
          )}
          {canCancel && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={cancelEstimate.isPending}
              className="text-red-600 hover:text-red-700"
              data-testid="cancel-estimate-btn"
            >
              <XCircle className="h-4 w-4 mr-1" />
              Cancel
            </Button>
          )}
          {canCreateJob && (
            <Button
              size="sm"
              onClick={handleCreateJob}
              disabled={createJob.isPending}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
              data-testid="create-job-btn"
            >
              <Briefcase className="h-4 w-4 mr-1" />
              Create Job
            </Button>
          )}
        </div>
      </div>

      <Separator />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content — Left 2 cols */}
        <div className="lg:col-span-2 space-y-6">
          {/* Customer Info */}
          <Card data-testid="customer-info">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
                Customer
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-lg font-semibold text-slate-800" data-testid="customer-name">
                {estimate.customer_name}
              </p>
              {estimate.customer_email && (
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <Mail className="h-3.5 w-3.5" />
                  <span data-testid="customer-email">{estimate.customer_email}</span>
                </div>
              )}
              {estimate.customer_phone && (
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <Phone className="h-3.5 w-3.5" />
                  <span data-testid="customer-phone">{estimate.customer_phone}</span>
                </div>
              )}
              {estimate.valid_until && (
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <Calendar className="h-3.5 w-3.5" />
                  <span data-testid="valid-until">
                    Valid until {formatDate(estimate.valid_until)}
                  </span>
                </div>
              )}
              {estimate.promotion_code && (
                <Badge variant="outline" className="text-xs mt-1" data-testid="promotion-code">
                  Promo: {estimate.promotion_code}
                </Badge>
              )}
            </CardContent>
          </Card>

          {/* Line Items */}
          <Card data-testid="line-items-section">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
                Line Items
              </CardTitle>
            </CardHeader>
            <CardContent>
              <LineItemsTable items={estimate.line_items} />

              {/* Totals */}
              <div className="mt-4 border-t pt-4 space-y-1.5">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Subtotal</span>
                  <span data-testid="subtotal">{formatCurrency(estimate.subtotal)}</span>
                </div>
                {estimate.discount_amount > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Discount</span>
                    <span className="text-red-600" data-testid="discount">
                      -{formatCurrency(estimate.discount_amount)}
                    </span>
                  </div>
                )}
                {estimate.tax_amount > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Tax</span>
                    <span data-testid="tax">{formatCurrency(estimate.tax_amount)}</span>
                  </div>
                )}
                <Separator />
                <div className="flex justify-between text-base font-bold">
                  <span>Total</span>
                  <span data-testid="total">{formatCurrency(estimate.total)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tier Options */}
          {estimate.tiers && estimate.tiers.length > 0 && (
            <TierSection tiers={estimate.tiers} />
          )}

          {/* Notes */}
          {estimate.notes && (
            <Card data-testid="estimate-notes">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
                  Notes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-600 whitespace-pre-wrap">{estimate.notes}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar — Right col */}
        <div className="space-y-6">
          {/* Activity Timeline */}
          <Card data-testid="activity-timeline-card">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-blue-500" />
                <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
                  Activity Timeline
                </CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <ActivityTimeline events={estimate.activity_timeline} />
            </CardContent>
          </Card>

          {/* Linked Documents */}
          {estimate.linked_documents.length > 0 && (
            <Card data-testid="linked-documents-card">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-slate-500" />
                  <CardTitle className="text-sm font-semibold text-slate-500 uppercase tracking-wider">
                    Documents
                  </CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <LinkedDocumentsSection documents={estimate.linked_documents} />
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
