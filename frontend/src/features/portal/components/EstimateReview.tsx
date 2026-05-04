import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { CheckCircle2, XCircle, FileText, Loader2, AlertTriangle } from 'lucide-react';
import { usePortalEstimate, useApproveEstimate, useRejectEstimate } from '../hooks';
import type { PortalEstimateTier, PortalEstimateLineItem } from '../types';

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
}

function LineItemsTable({ items }: { items: PortalEstimateLineItem[] }) {
  return (
    <Table data-testid="estimate-line-items-table">
      <TableHeader>
        <TableRow>
          <TableHead>Item</TableHead>
          <TableHead className="hidden md:table-cell">Description</TableHead>
          <TableHead className="text-right">Qty</TableHead>
          <TableHead className="text-right">Unit Price</TableHead>
          <TableHead className="text-right">Total</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item, idx) => (
          <TableRow key={idx}>
            <TableCell className="font-medium">
              {item.item}
              <p className="text-xs text-slate-500 md:hidden mt-1">{item.description}</p>
            </TableCell>
            <TableCell className="hidden md:table-cell text-slate-600">{item.description}</TableCell>
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

export function EstimateReview() {
  const { token = '' } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { data: estimate, isLoading, error } = usePortalEstimate(token);
  const approve = useApproveEstimate(token);
  const reject = useRejectEstimate(token);

  const [selectedTier, setSelectedTier] = useState<string | null>(null);
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const isExpired = error && (error as { response?: { status?: number } })?.response?.status === 410;

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50" data-testid="estimate-loading">
        <Loader2 className="h-8 w-8 animate-spin text-teal-500" />
      </div>
    );
  }

  if (isExpired) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4" data-testid="estimate-expired">
        <div className="max-w-md text-center space-y-4">
          <AlertTriangle className="h-12 w-12 text-amber-500 mx-auto" />
          <h1 className="text-xl font-bold text-slate-800">Link Expired</h1>
          <p className="text-slate-600">
            This estimate link has expired. Please contact the business for an updated link.
          </p>
        </div>
      </div>
    );
  }

  if (error || !estimate) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4" data-testid="estimate-error">
        <div className="max-w-md text-center space-y-4">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto" />
          <h1 className="text-xl font-bold text-slate-800">Unable to Load Estimate</h1>
          <p className="text-slate-600">
            We couldn&apos;t load this estimate. The link may be invalid or expired.
          </p>
        </div>
      </div>
    );
  }

  const handleApprove = async () => {
    try {
      await approve.mutateAsync(selectedTier ? { selected_tier: selectedTier } : undefined);
      navigate(`/portal/estimates/${token}/confirmed`, { state: { action: 'approved' } });
    } catch {
      // Error handled by mutation
    }
  };

  const handleReject = async () => {
    try {
      await reject.mutateAsync({ reason: rejectReason || undefined });
      navigate(`/portal/estimates/${token}/confirmed`, { state: { action: 'rejected' } });
    } catch {
      // Error handled by mutation
    }
  };

  const displayTotal = selectedTier
    ? estimate.tiers?.find((t) => t.name === selectedTier)?.total ?? estimate.total
    : estimate.total;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="estimate-review-page">
      {/* Header with company branding */}
      <header className="bg-white border-b border-slate-200 px-4 py-6 md:px-8">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          {estimate.company_logo_url && (
            <img
              src={estimate.company_logo_url}
              alt={estimate.company_name ?? 'Grins Irrigation'}
              className="h-12 w-auto object-contain"
              data-testid="company-logo"
            />
          )}
          <div>
            <h1 className="text-lg font-bold text-slate-800">
              {estimate.company_name ?? 'Grins Irrigation'}
            </h1>
            {estimate.company_phone && (
              <p className="text-sm text-slate-500">{estimate.company_phone}</p>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8 md:px-8 space-y-6">
        {/* Estimate info */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-teal-500" />
              <h2 className="text-lg font-semibold text-slate-800">
                Estimate {estimate.estimate_number}
              </h2>
            </div>
            <Badge
              variant={estimate.status === 'APPROVED' ? 'success' : estimate.status === 'REJECTED' ? 'error' : 'info'}
              data-testid="estimate-status-badge"
            >
              {estimate.status}
            </Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-slate-500">Prepared for:</span>
              <p className="font-medium text-slate-800">
                {[estimate.customer_first_name, estimate.customer_last_name]
                  .filter(Boolean)
                  .join(' ') || estimate.customer_name || '—'}
              </p>
            </div>
            <div>
              <span className="text-slate-500">Date:</span>
              <p className="font-medium text-slate-800">
                {new Date(estimate.created_at).toLocaleDateString()}
              </p>
            </div>
            {estimate.valid_until && (
              <div>
                <span className="text-slate-500">Valid until:</span>
                <p className="font-medium text-slate-800">
                  {new Date(estimate.valid_until).toLocaleDateString()}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Tier selection (if multi-tier) */}
        {estimate.tiers && estimate.tiers.length > 0 && (
          <div className="space-y-3" data-testid="tier-options">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
              Select an Option
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {estimate.tiers.map((tier: PortalEstimateTier) => (
                <button
                  key={tier.name}
                  type="button"
                  onClick={() => setSelectedTier(tier.name)}
                  className={cn(
                    'rounded-xl border-2 p-4 text-left transition-all',
                    selectedTier === tier.name
                      ? 'border-teal-500 bg-teal-50 shadow-sm'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  )}
                  data-testid={`tier-option-${tier.name}`}
                >
                  <p className="font-semibold text-slate-800 capitalize">{tier.name}</p>
                  <p className="text-lg font-bold text-teal-600 mt-1">{formatCurrency(tier.total)}</p>
                  <p className="text-xs text-slate-500 mt-1">{tier.line_items.length} items</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Line items table */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-x-auto">
          <div className="p-4 border-b border-slate-100">
            <h3 className="font-semibold text-slate-800">
              {selectedTier ? `${selectedTier} — Line Items` : 'Line Items'}
            </h3>
          </div>
          <LineItemsTable
            items={
              selectedTier
                ? estimate.tiers?.find((t) => t.name === selectedTier)?.line_items ?? estimate.line_items
                : estimate.line_items
            }
          />
        </div>

        {/* Totals */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-2" data-testid="estimate-totals">
          <div className="flex justify-between text-sm text-slate-600">
            <span>Subtotal</span>
            <span>{formatCurrency(estimate.subtotal)}</span>
          </div>
          {estimate.tax_amount > 0 && (
            <div className="flex justify-between text-sm text-slate-600">
              <span>Tax</span>
              <span>{formatCurrency(estimate.tax_amount)}</span>
            </div>
          )}
          {estimate.discount_amount > 0 && (
            <div className="flex justify-between text-sm text-emerald-600">
              <span>Discount {estimate.promotion_code && `(${estimate.promotion_code})`}</span>
              <span>-{formatCurrency(estimate.discount_amount)}</span>
            </div>
          )}
          <div className="flex justify-between text-lg font-bold text-slate-800 pt-2 border-t border-slate-100">
            <span>Total</span>
            <span>{formatCurrency(displayTotal)}</span>
          </div>
        </div>

        {/* Notes */}
        {estimate.notes && (
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-800 mb-2">Notes</h3>
            <p className="text-sm text-slate-600 whitespace-pre-wrap">{estimate.notes}</p>
          </div>
        )}

        {/* Actions */}
        {!estimate.is_readonly && (
          <div className="space-y-4" data-testid="estimate-actions">
            {!showRejectForm ? (
              <div className="flex flex-col md:flex-row gap-3">
                <Button
                  onClick={handleApprove}
                  disabled={approve.isPending || (!!estimate.tiers?.length && !selectedTier)}
                  className="flex-1 h-12"
                  data-testid="approve-estimate-btn"
                >
                  {approve.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4" />
                  )}
                  Approve Estimate
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setShowRejectForm(true)}
                  className="flex-1 h-12"
                  data-testid="reject-estimate-btn"
                >
                  <XCircle className="h-4 w-4" />
                  Reject
                </Button>
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4" data-testid="reject-form">
                <h3 className="font-semibold text-slate-800">Reason for Rejection (optional)</h3>
                <Textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="Let us know why you're declining this estimate..."
                  rows={3}
                  data-testid="reject-reason-textarea"
                />
                <div className="flex flex-col md:flex-row gap-3">
                  <Button
                    variant="destructive"
                    onClick={handleReject}
                    disabled={reject.isPending}
                    className="flex-1 h-12"
                    data-testid="confirm-reject-btn"
                  >
                    {reject.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Confirm Rejection'}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowRejectForm(false);
                      setRejectReason('');
                    }}
                    className="flex-1 h-12"
                    data-testid="cancel-reject-btn"
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {estimate.is_readonly && (
          <div className="text-center text-sm text-slate-500 py-4" data-testid="estimate-readonly-notice">
            This estimate has already been {estimate.status.toLowerCase()}.
          </div>
        )}
      </main>
    </div>
  );
}
