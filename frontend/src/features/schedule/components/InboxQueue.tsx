/**
 * InboxQueue — fourth queue card on ``/schedule`` (gap-16 v0).
 *
 * Surfaces inbound replies that span four heterogeneous source tables
 * (job_confirmation_responses, reschedule_requests, campaign_responses,
 * communications). Read-only in v0; triage actions (link, archive,
 * reply) deferred to v1.
 *
 * Wrapped in ``<section id="inbox-queue">`` so dashboard alert cards
 * (orphan-inbound, unrecognized-reply) can deep-link via
 * ``/schedule#inbox-queue``.
 *
 * Validates: scheduling-gaps gap-16.
 */

import { useEffect, useMemo, useState } from 'react';
import { format, formatDistanceToNow } from 'date-fns';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  ArrowRight,
  Calendar,
  ChevronDown,
  ChevronUp,
  Inbox,
  Mail,
  MessageSquare,
  PhoneCall,
  User,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { QueueFreshnessHeader } from '@/shared/components';
import { cn } from '@/lib/utils';
import { useInbox, inboxKeys } from '../hooks/useInbox';
import type {
  InboxFilterToken,
  InboxItem,
  InboxSourceTable,
} from '../api/inboxApi';

interface InboxQueueProps {
  onAppointmentClick?: (appointmentId: string) => void;
}

const FILTER_OPTIONS: { key: InboxFilterToken; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'needs_triage', label: 'Needs triage' },
  { key: 'orphans', label: 'Orphans' },
  { key: 'unrecognized', label: 'Unrecognized' },
  { key: 'opt_outs', label: 'Opt-outs' },
  { key: 'archived', label: 'Archived' },
];

const SNIPPET_LENGTH = 80;

const sourceIcons: Record<InboxSourceTable, React.ReactNode> = {
  job_confirmation_responses: (
    <MessageSquare className="h-3 w-3 text-teal-500" />
  ),
  reschedule_requests: <Calendar className="h-3 w-3 text-amber-500" />,
  campaign_responses: <Mail className="h-3 w-3 text-blue-500" />,
  communications: <PhoneCall className="h-3 w-3 text-violet-500" />,
};

const sourceLabels: Record<InboxSourceTable, string> = {
  job_confirmation_responses: 'Confirmation',
  reschedule_requests: 'Reschedule',
  campaign_responses: 'Campaign',
  communications: 'Inbox',
};

const triageColors: Record<InboxItem['triage_status'], string> = {
  pending: 'bg-amber-100 text-amber-700',
  handled: 'bg-emerald-100 text-emerald-700',
  dismissed: 'bg-slate-100 text-slate-500',
};

export function InboxQueue({ onAppointmentClick }: InboxQueueProps) {
  const [filter, setFilter] = useState<InboxFilterToken>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const {
    data,
    isLoading,
    error,
    dataUpdatedAt,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInbox(filter);

  const items = useMemo<InboxItem[]>(() => {
    if (!data?.pages) return [];
    return data.pages.flatMap((p) => p.items);
  }, [data]);

  const counts = data?.pages?.[0]?.counts;

  // Auto-scroll to anchor when navigated via /schedule#inbox-queue
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (window.location.hash !== '#inbox-queue') return;
    const el = document.getElementById('inbox-queue');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  const headerIcon = <Inbox className="h-4 w-4 text-indigo-500" />;
  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: inboxKeys.all });

  if (isLoading) {
    return (
      <section
        id="inbox-queue"
        className="bg-slate-50 rounded-xl p-4 border border-slate-100"
        data-testid="inbox-queue"
      >
        <div className="flex items-center gap-2 mb-3">
          {headerIcon}
          <h3 className="text-sm font-semibold text-slate-700">
            Inbound Triage
          </h3>
        </div>
        <div className="space-y-2">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section
        id="inbox-queue"
        className="bg-slate-50 rounded-xl p-4 border border-slate-100"
        data-testid="inbox-queue"
      >
        <div className="flex items-center gap-2 mb-3">
          {headerIcon}
          <h3 className="text-sm font-semibold text-slate-700">
            Inbound Triage
          </h3>
        </div>
        <p
          className="text-sm text-red-600"
          data-testid="inbox-queue-error"
        >
          Failed to load inbox.{' '}
          <Button
            size="sm"
            variant="ghost"
            className="h-auto p-0 text-red-600 underline"
            onClick={refresh}
          >
            Retry
          </Button>
        </p>
      </section>
    );
  }

  return (
    <section
      id="inbox-queue"
      className="bg-slate-50 rounded-xl p-4 border border-slate-100"
      data-testid="inbox-queue"
    >
      <QueueFreshnessHeader
        icon={headerIcon}
        title="Inbound Triage"
        badgeCount={counts?.needs_triage}
        badgeClassName="bg-amber-100 text-amber-700"
        dataUpdatedAt={dataUpdatedAt}
        isRefetching={isFetching}
        onRefresh={refresh}
        testId="refresh-inbox-btn"
      />

      <div
        className="flex items-center gap-1 flex-wrap mb-3"
        data-testid="inbox-filter-bar"
      >
        {FILTER_OPTIONS.map((opt) => {
          const count = counts ? (counts[opt.key] ?? 0) : 0;
          const active = filter === opt.key;
          return (
            <button
              key={opt.key}
              type="button"
              onClick={() => {
                setFilter(opt.key);
                setExpandedId(null);
              }}
              className={cn(
                'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                active
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'bg-white text-slate-600 hover:bg-slate-100'
              )}
              data-testid={`inbox-filter-${opt.key}`}
              aria-pressed={active}
            >
              {opt.label}
              {counts && (
                <span
                  className={cn(
                    'ml-1.5 text-[10px]',
                    active ? 'text-indigo-500' : 'text-slate-400'
                  )}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {items.length === 0 ? (
        <p
          className="text-sm text-slate-400"
          data-testid="inbox-queue-empty"
        >
          No inbound messages awaiting review
        </p>
      ) : (
        <div className="space-y-2" data-testid="inbox-queue-list">
          {items.map((item) => (
            <InboxRow
              key={`${item.source_table}-${item.id}`}
              item={item}
              expanded={expandedId === item.id}
              onToggle={() =>
                setExpandedId((prev) => (prev === item.id ? null : item.id))
              }
              onOpenAppointment={
                item.appointment_id
                  ? () => onAppointmentClick?.(item.appointment_id as string)
                  : undefined
              }
              onOpenCustomer={
                item.customer_id
                  ? () => navigate(`/customers/${item.customer_id}`)
                  : undefined
              }
            />
          ))}
        </div>
      )}

      {hasNextPage && (
        <div className="flex justify-center pt-3">
          <Button
            size="sm"
            variant="outline"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
            data-testid="load-more-inbox-btn"
          >
            {isFetchingNextPage ? 'Loading…' : 'Load more'}
          </Button>
        </div>
      )}
    </section>
  );
}

interface InboxRowProps {
  item: InboxItem;
  expanded: boolean;
  onToggle: () => void;
  onOpenAppointment?: () => void;
  onOpenCustomer?: () => void;
}

function InboxRow({
  item,
  expanded,
  onToggle,
  onOpenAppointment,
  onOpenCustomer,
}: InboxRowProps) {
  const snippet =
    item.body.length > SNIPPET_LENGTH
      ? `${item.body.slice(0, SNIPPET_LENGTH).trimEnd()}…`
      : item.body;
  const senderName = item.customer_name ?? 'Unknown number';
  const phone = item.from_phone ?? null;

  return (
    <div
      className="bg-white rounded-lg border border-slate-100"
      data-testid={`inbox-row-${item.id}`}
      data-source={item.source_table}
    >
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-start justify-between p-3 text-left hover:bg-slate-50"
        data-testid={`inbox-row-expand-${item.id}`}
        aria-expanded={expanded}
      >
        <div className="flex flex-col gap-1 min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-slate-700 truncate">
              {senderName}
            </span>
            {phone && (
              <span className="text-xs font-mono text-slate-500">
                {phone}
              </span>
            )}
            {item.parsed_keyword && (
              <Badge className="bg-indigo-100 text-indigo-700 text-[10px]">
                {item.parsed_keyword}
              </Badge>
            )}
          </div>
          <p className="text-sm text-slate-600 truncate">{snippet}</p>
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <span className="flex items-center gap-1">
              {sourceIcons[item.source_table]}
              {sourceLabels[item.source_table]}
            </span>
            <span>•</span>
            <Badge
              className={cn(
                'text-[10px] capitalize',
                triageColors[item.triage_status]
              )}
            >
              {item.triage_status.replace(/_/g, ' ')}
            </Badge>
            {item.status && (
              <span className="text-slate-400">
                • {item.status.replace(/_/g, ' ')}
              </span>
            )}
            <span>•</span>
            <time
              title={format(new Date(item.received_at), 'PPpp')}
            >
              {formatDistanceToNow(new Date(item.received_at), {
                addSuffix: true,
              })}
            </time>
          </div>
        </div>
        <div className="ml-2 shrink-0 self-center text-slate-400">
          {expanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </div>
      </button>

      {expanded && (
        <div
          className="border-t border-slate-100 p-3 space-y-3"
          data-testid={`inbox-row-detail-${item.id}`}
        >
          <p className="text-sm text-slate-700 whitespace-pre-wrap">
            {item.body}
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            {onOpenAppointment && (
              <Button
                size="sm"
                variant="outline"
                onClick={onOpenAppointment}
                data-testid={`open-appointment-btn-${item.id}`}
              >
                <ArrowRight className="h-3 w-3 mr-1" />
                Open appointment
              </Button>
            )}
            {onOpenCustomer && (
              <Button
                size="sm"
                variant="outline"
                onClick={onOpenCustomer}
                data-testid={`open-customer-btn-${item.id}`}
              >
                <User className="h-3 w-3 mr-1" />
                Open customer
              </Button>
            )}
            <Button
              size="sm"
              variant="ghost"
              disabled
              title="Archive available in v1"
              data-testid={`archive-inbox-btn-${item.id}`}
            >
              <AlertCircle className="h-3 w-3 mr-1" />
              Archive
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

