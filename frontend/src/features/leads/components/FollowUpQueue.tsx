import { useState } from 'react';
import { ChevronDown, ChevronRight, Clock, ArrowRight, XCircle, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { useFollowUpQueue } from '../hooks/useLeads';
import { useUpdateLead } from '../hooks/useLeadMutations';
import type { FollowUpLead } from '../types';

function urgencyColor(hours: number): string {
  if (hours >= 12) return 'text-red-600 bg-red-50';
  if (hours >= 2) return 'text-yellow-600 bg-yellow-50';
  return 'text-green-600 bg-green-50';
}

function formatHoursAgo(hours: number): string {
  if (hours < 1) return 'just now';
  if (hours < 24) return `${Math.round(hours)}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function UrgencyIndicator({ hours }: { hours: number }) {
  const color = urgencyColor(hours);
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${color}`}>
      <Clock className="h-3 w-3" />
      {formatHoursAgo(hours)}
    </span>
  );
}

function FollowUpLeadRow({ lead }: { lead: FollowUpLead }) {
  const updateLead = useUpdateLead();

  const handleMoveToSchedule = async () => {
    try {
      await updateLead.mutateAsync({ id: lead.id, data: { intake_tag: 'schedule' } });
      toast.success('Moved to Schedule', { description: `${lead.name} moved to schedule queue.` });
    } catch {
      toast.error('Failed', { description: 'Could not update lead.' });
    }
  };

  const handleMarkLost = async () => {
    try {
      await updateLead.mutateAsync({ id: lead.id, data: { status: 'lost' } });
      toast.success('Marked as Lost', { description: `${lead.name} marked as lost.` });
    } catch {
      toast.error('Failed', { description: 'Could not update lead.' });
    }
  };

  return (
    <div
      className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-50 transition-colors"
      data-testid={`follow-up-lead-${lead.id}`}
    >
      <div className="flex items-center gap-4 min-w-0">
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-700 truncate">{lead.name}</p>
          <p className="text-xs text-slate-500">{lead.phone}</p>
        </div>
        {lead.notes && (
          <p className="text-xs text-slate-400 truncate max-w-[200px]" title={lead.notes}>
            {lead.notes}
          </p>
        )}
        <UrgencyIndicator hours={lead.time_since_created} />
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleMoveToSchedule}
          disabled={updateLead.isPending}
          title="Move to Schedule"
          data-testid={`move-schedule-${lead.id}`}
        >
          <ArrowRight className="h-4 w-4 text-green-600" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleMarkLost}
          disabled={updateLead.isPending}
          title="Mark Lost"
          data-testid={`mark-lost-${lead.id}`}
        >
          <XCircle className="h-4 w-4 text-gray-500" />
        </Button>
      </div>
    </div>
  );
}

export function FollowUpQueue() {
  const [expanded, setExpanded] = useState(true);
  const { data, isLoading } = useFollowUpQueue();

  const count = data?.total ?? 0;

  if (isLoading || count === 0) return null;

  return (
    <div
      className="bg-orange-50/50 border border-orange-200 rounded-2xl overflow-hidden"
      data-testid="follow-up-queue"
    >
      <button
        className="w-full flex items-center justify-between p-4 text-left hover:bg-orange-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-orange-600" />
          ) : (
            <ChevronRight className="h-4 w-4 text-orange-600" />
          )}
          <FileText className="h-4 w-4 text-orange-600" />
          <span className="text-sm font-semibold text-orange-800">
            Follow-Up Queue
          </span>
          <span className="text-xs bg-orange-200 text-orange-800 rounded-full px-2 py-0.5 font-medium">
            {count}
          </span>
        </div>
      </button>
      {expanded && (
        <div className="px-4 pb-4 space-y-1">
          {data?.items.map((lead) => (
            <FollowUpLeadRow key={lead.id} lead={lead} />
          ))}
        </div>
      )}
    </div>
  );
}
