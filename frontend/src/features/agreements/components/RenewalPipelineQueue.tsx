import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { useRenewalPipeline, useApproveRenewal, useRejectRenewal } from '../hooks';
import { AGREEMENT_STATUS_CONFIG } from '../types';
import { cn } from '@/lib/utils';
import { CheckCircle, XCircle, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

function daysUntilRenewal(renewalDate: string | null): number | null {
  if (!renewalDate) return null;
  const diff = new Date(renewalDate).getTime() - Date.now();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function UrgencyBadge({ days }: { days: number | null }) {
  if (days === null) return null;
  if (days <= 1) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700" data-testid="urgency-critical">
        <AlertTriangle className="h-3 w-3" /> {days <= 0 ? 'Overdue' : '1 day'}
      </span>
    );
  }
  if (days <= 7) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700" data-testid="urgency-warning">
        <AlertTriangle className="h-3 w-3" /> {days} days
      </span>
    );
  }
  return <span className="text-xs text-slate-500">{days} days</span>;
}

export function RenewalPipelineQueue() {
  const [collapsed, setCollapsed] = useState(false);
  const { data: agreements, isLoading, error } = useRenewalPipeline();
  const approveRenewal = useApproveRenewal();
  const rejectRenewal = useRejectRenewal();

  const handleApprove = async (id: string) => {
    try {
      await approveRenewal.mutateAsync(id);
      toast.success('Renewal approved');
    } catch {
      toast.error('Failed to approve renewal');
    }
  };

  const handleReject = async (id: string) => {
    try {
      await rejectRenewal.mutateAsync({ id });
      toast.success('Renewal rejected');
    } catch {
      toast.error('Failed to reject renewal');
    }
  };

  const count = agreements?.length ?? 0;

  return (
    <div className="bg-white rounded-xl border border-slate-100 overflow-hidden" data-testid="renewal-pipeline-queue">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="font-medium text-slate-700">Renewal Pipeline</span>
          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">{count}</span>
        </div>
        {collapsed ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronUp className="h-4 w-4 text-slate-400" />}
      </button>

      {!collapsed && (
        <div className="border-t border-slate-100">
          {isLoading && <div className="p-4"><LoadingSpinner /></div>}
          {error && <Alert variant="destructive" className="m-4"><AlertDescription>Failed to load renewal pipeline.</AlertDescription></Alert>}
          {!isLoading && !error && count === 0 && (
            <p className="p-4 text-sm text-slate-500">No pending renewals.</p>
          )}
          {agreements && agreements.length > 0 && (
            <div className="divide-y divide-slate-50">
              {agreements.map((agr) => {
                const days = daysUntilRenewal(agr.renewal_date);
                return (
                  <div key={agr.id} className="flex items-center justify-between px-4 py-3" data-testid={`renewal-row-${agr.id}`}>
                    <div className="flex items-center gap-3 min-w-0">
                      <Link to={`/agreements/${agr.id}`} className="font-medium text-sm text-slate-700 hover:text-teal-600 truncate">
                        {agr.agreement_number}
                      </Link>
                      <span className="text-sm text-slate-500 truncate">{agr.customer_name}</span>
                      <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', AGREEMENT_STATUS_CONFIG.pending_renewal.bgColor, AGREEMENT_STATUS_CONFIG.pending_renewal.color)}>
                        {AGREEMENT_STATUS_CONFIG.pending_renewal.label}
                      </span>
                      <UrgencyBadge days={days} />
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-emerald-600 border-emerald-200 hover:bg-emerald-50"
                        onClick={() => handleApprove(agr.id)}
                        disabled={approveRenewal.isPending}
                        data-testid={`approve-renewal-${agr.id}`}
                      >
                        <CheckCircle className="h-3.5 w-3.5 mr-1" /> Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-red-600 border-red-200 hover:bg-red-50"
                        onClick={() => handleReject(agr.id)}
                        disabled={rejectRenewal.isPending}
                        data-testid={`reject-renewal-${agr.id}`}
                      >
                        <XCircle className="h-3.5 w-3.5 mr-1" /> Reject
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
