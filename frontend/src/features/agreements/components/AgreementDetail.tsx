import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Circle,
  Clock,
  ExternalLink,
  FileText,
  Pause,
  Play,
  Save,
  Shield,
  ThumbsDown,
  ThumbsUp,
  User,
  XCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { LoadingPage, ErrorMessage } from '@/shared/components';
import { config } from '@/core/config';
import { useAgreement, useAgreementCompliance, useUpdateNotes } from '../hooks';
import { useUpdateAgreementStatus, useApproveRenewal, useRejectRenewal } from '../hooks';
import { getAgreementStatusConfig } from '../types';
import type { AgreementDetail as AgreementDetailType, AgreementJobSummary, AgreementStatusLog, AgreementStatus, DisclosureRecord, DisclosureType } from '../types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(d: string | null | undefined): string {
  if (!d) return '—';
  return new Date(d).toLocaleDateString();
}

function formatCurrency(amount: number | string | null | undefined): string {
  if (amount == null) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(amount));
}

function jobStatusIcon(status: string) {
  switch (status) {
    case 'completed':
    case 'closed':
      return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
    case 'scheduled':
    case 'in_progress':
      return <Calendar className="h-4 w-4 text-blue-500" />;
    default:
      return <Circle className="h-4 w-4 text-slate-300" />;
  }
}

const DISCLOSURE_LABELS: Record<DisclosureType, string> = {
  PRE_SALE: 'Pre-Sale',
  CONFIRMATION: 'Confirmation',
  RENEWAL_NOTICE: 'Renewal Notice',
  ANNUAL_NOTICE: 'Annual Notice',
  CANCELLATION_CONF: 'Cancellation Confirmation',
};

const DISCLOSURE_COLORS: Record<DisclosureType, string> = {
  PRE_SALE: 'bg-violet-100 text-violet-700',
  CONFIRMATION: 'bg-emerald-100 text-emerald-700',
  RENEWAL_NOTICE: 'bg-blue-100 text-blue-700',
  ANNUAL_NOTICE: 'bg-amber-100 text-amber-700',
  CANCELLATION_CONF: 'bg-red-100 text-red-700',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  const cfg = getAgreementStatusConfig(status as AgreementDetailType['status']);
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${cfg.bgColor} ${cfg.color}`}
      data-testid="agreement-status-badge"
    >
      {cfg.label}
    </span>
  );
}

function InfoSection({ agreement }: { agreement: AgreementDetailType }) {
  return (
    <Card data-testid="agreement-info">
      <CardContent className="pt-6 space-y-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-slate-400">Tier</p>
            <p className="font-medium text-slate-700">{agreement.tier_name ?? '—'}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Package Type</p>
            <p className="font-medium text-slate-700 capitalize">{agreement.package_type ?? '—'}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Annual Price</p>
            <p className="font-medium text-slate-700">{formatCurrency(agreement.annual_price)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Auto-Renew</p>
            <p className="font-medium text-slate-700">{agreement.auto_renew ? 'Yes' : 'No'}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Start Date</p>
            <p className="font-medium text-slate-700">{formatDate(agreement.start_date)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">End Date</p>
            <p className="font-medium text-slate-700">{formatDate(agreement.end_date)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Renewal Date</p>
            <p className="font-medium text-slate-700">{formatDate(agreement.renewal_date)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400">Payment Status</p>
            <p className="font-medium text-slate-700 capitalize">{agreement.payment_status.replace('_', ' ')}</p>
          </div>
        </div>

        {/* Customer link */}
        {agreement.customer_id && (
          <Link
            to={`/customers/${agreement.customer_id}`}
            className="flex items-center gap-2 p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
            data-testid="agreement-customer-link"
          >
            <User className="h-4 w-4 text-blue-600" />
            <span className="text-sm font-medium text-blue-700">
              {agreement.customer_name ?? 'View Customer'}
            </span>
          </Link>
        )}
      </CardContent>
    </Card>
  );
}

function JobsTimeline({ jobs }: { jobs: AgreementJobSummary[] }) {
  const sorted = [...jobs].sort((a, b) => {
    const da = a.target_start_date ?? '';
    const db = b.target_start_date ?? '';
    return da.localeCompare(db);
  });
  const completed = jobs.filter((j) => j.status === 'completed' || j.status === 'closed').length;

  return (
    <Card data-testid="agreement-jobs-timeline">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
          <Calendar className="h-4 w-4 text-slate-400" />
          Visits
          <span className="ml-auto text-xs font-normal text-slate-500" data-testid="jobs-progress">
            {completed} of {jobs.length} completed
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {sorted.length === 0 ? (
          <p className="text-sm text-slate-400">No visits scheduled</p>
        ) : (
          <div className="space-y-2">
            {sorted.map((job) => (
              <Link
                key={job.id}
                to={`/jobs/${job.id}`}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 transition-colors"
                data-testid={`job-row-${job.id}`}
              >
                {jobStatusIcon(job.status)}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-700 truncate">
                    {job.job_type ?? 'Service Visit'}
                  </p>
                  <p className="text-xs text-slate-400">
                    {formatDate(job.target_start_date)}
                    {job.target_end_date && job.target_end_date !== job.target_start_date
                      ? ` – ${formatDate(job.target_end_date)}`
                      : ''}
                  </p>
                </div>
                <span className="text-xs text-slate-400 capitalize">{job.status.replace('_', ' ')}</span>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StatusLog({ logs }: { logs: AgreementStatusLog[] }) {
  const sorted = [...logs].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <Card data-testid="agreement-status-log">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
          <Clock className="h-4 w-4 text-slate-400" />
          Status History
        </CardTitle>
      </CardHeader>
      <CardContent>
        {sorted.length === 0 ? (
          <p className="text-sm text-slate-400">No status changes recorded</p>
        ) : (
          <div className="space-y-3">
            {sorted.map((log) => (
              <div key={log.id} className="flex gap-3 text-sm" data-testid={`status-log-${log.id}`}>
                <div className="w-1 rounded-full bg-slate-200 shrink-0" />
                <div className="min-w-0">
                  <p className="font-medium text-slate-700">
                    {log.old_status ? (
                      <>
                        <span className="capitalize">{log.old_status.replace('_', ' ')}</span>
                        {' → '}
                      </>
                    ) : null}
                    <span className="capitalize">{log.new_status.replace('_', ' ')}</span>
                  </p>
                  {log.reason && <p className="text-slate-500">{log.reason}</p>}
                  <p className="text-xs text-slate-400">
                    {formatDate(log.created_at)}
                    {log.changed_by_name ? ` by ${log.changed_by_name}` : ''}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ComplianceLog({ records, agreementStatus, lastAnnualNoticeSent }: { records: DisclosureRecord[]; agreementStatus: AgreementStatus; lastAnnualNoticeSent: string | null }) {
  const sorted = [...records].sort(
    (a, b) => new Date(b.sent_at).getTime() - new Date(a.sent_at).getTime(),
  );

  // Check which disclosure types are present (normalize to uppercase for comparison)
  const presentTypes = new Set(records.map((r) => r.disclosure_type.toUpperCase()));
  const requiredTypes: DisclosureType[] = ['PRE_SALE', 'CONFIRMATION'];
  const allTypes: DisclosureType[] = ['PRE_SALE', 'CONFIRMATION', 'RENEWAL_NOTICE', 'ANNUAL_NOTICE', 'CANCELLATION_CONF'];

  // Determine overdue status for ANNUAL_NOTICE: overdue if ACTIVE and no notice in current year
  const currentYear = new Date().getFullYear();
  const annualNoticeOverdue =
    agreementStatus === 'active' &&
    (!lastAnnualNoticeSent || new Date(lastAnnualNoticeSent).getFullYear() < currentYear);

  const getIndicator = (type: DisclosureType) => {
    const isPresent = presentTypes.has(type);
    if (isPresent) return { icon: '✓', className: 'bg-emerald-100 text-emerald-700' };
    if (type === 'ANNUAL_NOTICE' && annualNoticeOverdue)
      return { icon: '⚠', className: 'bg-orange-100 text-orange-700' };
    if (requiredTypes.includes(type))
      return { icon: '✗', className: 'bg-red-100 text-red-700' };
    return { icon: '—', className: 'bg-slate-100 text-slate-500' };
  };

  return (
    <Card data-testid="agreement-compliance-log">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
          <Shield className="h-4 w-4 text-slate-400" />
          Compliance
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status summary */}
        <div className="flex flex-wrap gap-2" data-testid="compliance-status-summary">
          {allTypes.map((type) => {
            const { icon, className } = getIndicator(type);
            return (
              <span
                key={type}
                className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${className}`}
                data-testid={`compliance-${type}`}
              >
                {icon} {DISCLOSURE_LABELS[type]}
              </span>
            );
          })}
        </div>

        {/* Overdue warning */}
        {annualNoticeOverdue && (
          <div
            className="flex items-center gap-2 rounded-md bg-orange-50 border border-orange-200 px-3 py-2 text-xs text-orange-700"
            data-testid="compliance-overdue-warning"
          >
            <Shield className="h-3.5 w-3.5 shrink-0" />
            Annual notice has not been sent this year. Required for active agreements.
          </div>
        )}

        {/* Records list */}
        {sorted.length === 0 ? (
          <p className="text-sm text-slate-400">No disclosure records</p>
        ) : (
          <div className="space-y-2">
            {sorted.map((rec) => (
              <div key={rec.id} className="flex items-center gap-2 text-sm" data-testid={`disclosure-${rec.id}`}>
                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${DISCLOSURE_COLORS[rec.disclosure_type.toUpperCase() as DisclosureType] ?? 'bg-slate-100 text-slate-500'}`}>
                  {DISCLOSURE_LABELS[rec.disclosure_type.toUpperCase() as DisclosureType] ?? rec.disclosure_type}
                </span>
                <span className="text-slate-500">{formatDate(rec.sent_at)}</span>
                <span className="text-xs text-slate-400">via {rec.sent_via}</span>
                {rec.delivery_confirmed && (
                  <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AdminNotes({ agreementId, initialNotes }: { agreementId: string; initialNotes: string | null }) {
  const [notes, setNotes] = useState(initialNotes ?? '');
  const [dirty, setDirty] = useState(false);
  const updateNotes = useUpdateNotes();

  const handleSave = async () => {
    await updateNotes.mutateAsync({ id: agreementId, notes: notes || null });
    setDirty(false);
  };

  return (
    <Card data-testid="agreement-admin-notes">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
          <FileText className="h-4 w-4 text-slate-400" />
          Admin Notes
        </CardTitle>
      </CardHeader>
      <CardContent>
        <textarea
          className="w-full min-h-[80px] rounded-md border border-slate-200 p-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
          value={notes}
          onChange={(e) => {
            setNotes(e.target.value);
            setDirty(true);
          }}
          placeholder="Add internal notes about this agreement..."
          data-testid="admin-notes-input"
        />
        {dirty && (
          <Button
            size="sm"
            className="mt-2"
            onClick={handleSave}
            disabled={updateNotes.isPending}
            data-testid="save-notes-btn"
          >
            <Save className="h-3.5 w-3.5 mr-1" />
            {updateNotes.isPending ? 'Saving...' : 'Save Notes'}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Cancel dialog
// ---------------------------------------------------------------------------

function CancelDialog({
  open,
  onOpenChange,
  onConfirm,
  isPending,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (reason: string) => void;
  isPending: boolean;
}) {
  const [reason, setReason] = useState('');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="cancel-dialog">
        <DialogHeader>
          <DialogTitle>Cancel Agreement</DialogTitle>
          <DialogDescription>
            This will cancel the agreement and any approved jobs. Please provide a reason.
          </DialogDescription>
        </DialogHeader>
        <textarea
          className="w-full min-h-[80px] rounded-md border border-slate-200 p-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Cancellation reason (required)..."
          data-testid="cancel-reason-input"
        />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="cancel-dialog-dismiss">
            Back
          </Button>
          <Button
            variant="destructive"
            disabled={!reason.trim() || isPending}
            onClick={() => onConfirm(reason.trim())}
            data-testid="cancel-dialog-confirm"
          >
            {isPending ? 'Cancelling...' : 'Confirm Cancel'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Context-sensitive action buttons
// ---------------------------------------------------------------------------

function ActionButtons({
  agreement,
}: {
  agreement: AgreementDetailType;
}) {
  const [cancelOpen, setCancelOpen] = useState(false);
  const updateStatus = useUpdateAgreementStatus();
  const approveRenewal = useApproveRenewal();
  const rejectRenewal = useRejectRenewal();

  const handleStatusChange = async (status: string, reason?: string) => {
    try {
      await updateStatus.mutateAsync({ id: agreement.id, data: { status, reason } });
      toast.success(`Agreement ${status.replace('_', ' ')}`);
    } catch (e) {
      toast.error((e as Error).message || 'Failed to update status');
    }
  };

  const handleApprove = async () => {
    try {
      await approveRenewal.mutateAsync(agreement.id);
      toast.success('Renewal approved');
    } catch (e) {
      toast.error((e as Error).message || 'Failed to approve renewal');
    }
  };

  const handleReject = async () => {
    try {
      await rejectRenewal.mutateAsync({ id: agreement.id });
      toast.success('Renewal rejected');
    } catch (e) {
      toast.error((e as Error).message || 'Failed to reject renewal');
    }
  };

  const handleCancel = async (reason: string) => {
    await handleStatusChange('cancelled', reason);
    setCancelOpen(false);
  };

  const isPending = updateStatus.isPending || approveRenewal.isPending || rejectRenewal.isPending;

  const buttons: Record<AgreementStatus, React.ReactNode> = {
    active: (
      <>
        <Button
          variant="outline"
          size="sm"
          disabled={isPending}
          onClick={() => handleStatusChange('paused', 'Admin paused')}
          data-testid="pause-agreement-btn"
        >
          <Pause className="h-3.5 w-3.5 mr-1" /> Pause
        </Button>
        <Button
          variant="destructive"
          size="sm"
          disabled={isPending}
          onClick={() => setCancelOpen(true)}
          data-testid="cancel-agreement-btn"
        >
          <XCircle className="h-3.5 w-3.5 mr-1" /> Cancel
        </Button>
      </>
    ),
    paused: (
      <>
        <Button
          variant="outline"
          size="sm"
          disabled={isPending}
          onClick={() => handleStatusChange('active', 'Admin resumed')}
          data-testid="resume-agreement-btn"
        >
          <Play className="h-3.5 w-3.5 mr-1" /> Resume
        </Button>
        <Button
          variant="destructive"
          size="sm"
          disabled={isPending}
          onClick={() => setCancelOpen(true)}
          data-testid="cancel-agreement-btn"
        >
          <XCircle className="h-3.5 w-3.5 mr-1" /> Cancel
        </Button>
      </>
    ),
    pending_renewal: (
      <>
        <Button
          size="sm"
          disabled={isPending}
          onClick={handleApprove}
          data-testid="approve-renewal-btn"
        >
          <ThumbsUp className="h-3.5 w-3.5 mr-1" /> Approve Renewal
        </Button>
        <Button
          variant="destructive"
          size="sm"
          disabled={isPending}
          onClick={handleReject}
          data-testid="reject-renewal-btn"
        >
          <ThumbsDown className="h-3.5 w-3.5 mr-1" /> Reject Renewal
        </Button>
      </>
    ),
    pending: null,
    past_due: null,
    cancelled: null,
    expired: null,
  };

  const actions = buttons[agreement.status];
  if (!actions) return null;

  return (
    <>
      <div className="flex flex-wrap gap-2" data-testid="agreement-actions">
        {actions}
      </div>
      <CancelDialog
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        onConfirm={handleCancel}
        isPending={updateStatus.isPending}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface AgreementDetailProps {
  agreementId: string;
  onClose?: () => void;
}

export function AgreementDetail({ agreementId, onClose }: AgreementDetailProps) {
  const navigate = useNavigate();
  const { data: agreement, isLoading, error, refetch } = useAgreement(agreementId);
  const { data: compliance } = useAgreementCompliance(agreementId);

  const handleGoBack = () => {
    if (onClose) {
      onClose();
    } else {
      navigate('/agreements');
    }
  };

  if (isLoading) return <LoadingPage message="Loading agreement..." />;
  if (error) return <ErrorMessage error={error} onRetry={() => refetch()} />;
  if (!agreement) return <ErrorMessage error={new Error('Agreement not found')} />;

  const stripeSubUrl = agreement.stripe_subscription_id
    ? `https://dashboard.stripe.com/subscriptions/${agreement.stripe_subscription_id}`
    : null;

  const customerPortalUrl = config.stripeCustomerPortalUrl || null;

  return (
    <div data-testid="agreement-detail" className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleGoBack}
            aria-label="Go back"
            className="h-8 w-8 hover:bg-slate-100 shrink-0"
          >
            <ArrowLeft className="h-4 w-4 text-slate-600" />
          </Button>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-slate-800 truncate" data-testid="agreement-title">
              {agreement.agreement_number}
            </h1>
            <p className="text-slate-500 text-sm">
              {agreement.tier_name} · {agreement.customer_name ?? 'Unknown Customer'}
            </p>
          </div>
        </div>
        <StatusBadge status={agreement.status} />
      </div>

      {/* Action buttons */}
      <ActionButtons agreement={agreement} />

      {/* External links */}
      <div className="flex flex-wrap gap-2">
        {stripeSubUrl && (
          <a
            href={stripeSubUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
            data-testid="stripe-dashboard-link"
          >
            <ExternalLink className="h-3 w-3" /> View in Stripe
          </a>
        )}
        {customerPortalUrl && (
          <a
            href={customerPortalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
            data-testid="customer-portal-link"
          >
            <ExternalLink className="h-3 w-3" /> Customer Portal
          </a>
        )}
      </div>

      <InfoSection agreement={agreement} />

      <Separator />

      <JobsTimeline jobs={agreement.jobs} />

      <StatusLog logs={agreement.status_logs} />

      <ComplianceLog
        records={compliance ?? []}
        agreementStatus={agreement.status}
        lastAnnualNoticeSent={agreement.last_annual_notice_sent}
      />

      <AdminNotes agreementId={agreementId} initialNotes={agreement.notes} />
    </div>
  );
}
