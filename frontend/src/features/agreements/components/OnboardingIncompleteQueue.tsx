import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
import { useOnboardingIncomplete } from '../hooks';
import { ChevronDown, ChevronUp, UserX } from 'lucide-react';

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function OnboardingIncompleteQueue() {
  const [collapsed, setCollapsed] = useState(false);
  const { data: agreements, isLoading, error } = useOnboardingIncomplete();

  const count = agreements?.length ?? 0;

  return (
    <div className="bg-white rounded-xl border border-slate-100 overflow-hidden" data-testid="onboarding-incomplete-queue">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="font-medium text-slate-700">Onboarding Incomplete</span>
          <span className="rounded-full bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700">{count}</span>
        </div>
        {collapsed ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronUp className="h-4 w-4 text-slate-400" />}
      </button>

      {!collapsed && (
        <div className="border-t border-slate-100">
          {isLoading && <div className="p-4"><LoadingSpinner /></div>}
          {error && <Alert variant="destructive" className="m-4"><AlertDescription>Failed to load onboarding queue.</AlertDescription></Alert>}
          {!isLoading && !error && count === 0 && (
            <p className="p-4 text-sm text-slate-500">No incomplete onboarding.</p>
          )}
          {agreements && agreements.length > 0 && (
            <div className="divide-y divide-slate-50">
              {agreements.map((agr) => (
                <div key={agr.id} className="flex items-center justify-between px-4 py-3" data-testid={`onboarding-row-${agr.id}`}>
                  <div className="flex items-center gap-3 min-w-0">
                    <UserX className="h-4 w-4 text-violet-400 shrink-0" />
                    <Link to={`/agreements/${agr.id}`} className="font-medium text-sm text-slate-700 hover:text-teal-600 truncate">
                      {agr.agreement_number}
                    </Link>
                    <span className="text-sm text-slate-500 truncate">{agr.customer_name}</span>
                    <span className="text-xs text-slate-400">Created {formatDate(agr.created_at)}</span>
                  </div>
                  <span className="text-xs text-violet-600 font-medium shrink-0">No property</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
