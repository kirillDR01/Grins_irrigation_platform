import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { useFailedPayments, useUpdateAgreementStatus } from '../hooks';
import { AGREEMENT_STATUS_CONFIG } from '../types';
import type { AgreementStatus } from '../types';
import { cn } from '@/lib/utils';
import { Play, XCircle, ChevronDown, ChevronUp } from 'lucide-react';

function formatCurrency(amount: number | string): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(amount));
}

export function FailedPaymentsQueue() {
  const [collapsed, setCollapsed] = useState(false);
  const { data: agreements, isLoading, error } = useFailedPayments();
  const updateStatus = useUpdateAgreementStatus();

  const handleResume = async (id: string) => {
    try {
      await updateStatus.mutateAsync({ id, data: { status: 'active', reason: 'Payment recovered' } });
      toast.success('Agreement resumed');
    } catch {
      toast.error('Failed to resume agreement');
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await updateStatus.mutateAsync({ id, data: { status: 'cancelled', reason: 'Payment failure' } });
      toast.success('Agreement cancelled');
    } catch {
      toast.error('Failed to cancel agreement');
    }
  };

  const count = agreements?.length ?? 0;

  return (
    <div className="bg-white rounded-xl border border-slate-100 overflow-hidden" data-testid="failed-payments-queue">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="font-medium text-slate-700">Failed Payments</span>
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">{count}</span>
        </div>
        {collapsed ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronUp className="h-4 w-4 text-slate-400" />}
      </button>

      {!collapsed && (
        <div className="border-t border-slate-100">
          {isLoading && <div className="p-4"><LoadingSpinner /></div>}
          {error && <Alert variant="destructive" className="m-4"><AlertDescription>Failed to load failed payments.</AlertDescription></Alert>}
          {!isLoading && !error && count === 0 && (
            <p className="p-4 text-sm text-slate-500">No failed payments.</p>
          )}
          {agreements && agreements.length > 0 && (
            <div className="divide-y divide-slate-50">
              {agreements.map((agr) => {
                const statusCfg = AGREEMENT_STATUS_CONFIG[agr.status as AgreementStatus];
                return (
                  <div key={agr.id} className="flex items-center justify-between px-4 py-3" data-testid={`failed-payment-row-${agr.id}`}>
                    <div className="flex items-center gap-3 min-w-0">
                      <Link to={`/agreements/${agr.id}`} className="font-medium text-sm text-slate-700 hover:text-teal-600 truncate">
                        {agr.agreement_number}
                      </Link>
                      <span className="text-sm text-slate-500 truncate">{agr.customer_name}</span>
                      <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', statusCfg.bgColor, statusCfg.color)}>
                        {statusCfg.label}
                      </span>
                      <span className="text-sm font-medium text-red-600">{formatCurrency(agr.annual_price)}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-emerald-600 border-emerald-200 hover:bg-emerald-50"
                        onClick={() => handleResume(agr.id)}
                        disabled={updateStatus.isPending}
                        data-testid={`resume-payment-${agr.id}`}
                      >
                        <Play className="h-3.5 w-3.5 mr-1" /> Resume
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-red-600 border-red-200 hover:bg-red-50"
                        onClick={() => handleCancel(agr.id)}
                        disabled={updateStatus.isPending}
                        data-testid={`cancel-payment-${agr.id}`}
                      >
                        <XCircle className="h-3.5 w-3.5 mr-1" /> Cancel
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
