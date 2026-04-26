/**
 * CustomerMessages — paired inbound/outbound conversation view (gap-13).
 *
 * Backed by ``GET /api/v1/customers/{id}/conversation`` which UNIONs
 * sent_messages, job_confirmation_responses, campaign_responses, and
 * communications into a single chronological stream.
 *
 * Outbound rows render right-aligned (chat-app convention); inbound
 * rows render left-aligned. Each row exposes a channel icon, parsed
 * keyword (inbound), delivery status (outbound), and timestamp.
 *
 * Validates: scheduling-gaps gap-13.
 */

import { useMemo, useState } from 'react';
import { ArrowDownLeft, ArrowUpRight, Mail, MessageSquare, Phone, RefreshCw } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { OptOutBadge } from '@/shared/components';
import { cn } from '@/lib/utils';
import { customerKeys, useCustomerConversation } from '../hooks';
import type {
  ConversationChannel,
  ConversationItem,
} from '../types';

type ChannelFilter = 'all' | 'sms' | 'email';

const channelIcons: Record<ConversationChannel, React.ReactNode> = {
  sms: <MessageSquare className="h-3.5 w-3.5 text-teal-500" />,
  email: <Mail className="h-3.5 w-3.5 text-blue-500" />,
  phone: <Phone className="h-3.5 w-3.5 text-violet-500" />,
  other: <MessageSquare className="h-3.5 w-3.5 text-slate-400" />,
};

const outboundStatusColors: Record<string, string> = {
  sent: 'bg-emerald-100 text-emerald-700',
  delivered: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
  pending: 'bg-amber-100 text-amber-700',
  queued: 'bg-blue-100 text-blue-700',
  scheduled: 'bg-blue-100 text-blue-700',
  cancelled: 'bg-slate-100 text-slate-600',
};

const inboundStatusColors: Record<string, string> = {
  parsed: 'bg-emerald-100 text-emerald-700',
  needs_review: 'bg-amber-100 text-amber-700',
  orphan: 'bg-purple-100 text-purple-700',
  opted_out: 'bg-red-100 text-red-700',
  pending: 'bg-slate-100 text-slate-600',
};

interface CustomerMessagesProps {
  customerId: string;
}

export function CustomerMessages({ customerId }: CustomerMessagesProps) {
  const {
    data,
    isLoading,
    error,
    dataUpdatedAt,
    isFetching,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useCustomerConversation(customerId);
  const queryClient = useQueryClient();
  const [channelFilter, setChannelFilter] = useState<ChannelFilter>('all');

  const allItems = useMemo<ConversationItem[]>(() => {
    if (!data?.pages) return [];
    return data.pages.flatMap((p) => p.items);
  }, [data]);

  const filteredItems = useMemo(() => {
    if (channelFilter === 'all') return allItems;
    return allItems.filter((item) => item.channel === channelFilter);
  }, [allItems, channelFilter]);

  const header = (
    <div className="mb-3 flex items-center justify-between">
      <OptOutBadge customerId={customerId} />
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <ChannelFilterPills value={channelFilter} onChange={setChannelFilter} />
        <span data-testid="queue-last-updated">
          {dataUpdatedAt > 0
            ? `Updated ${formatDistanceToNow(new Date(dataUpdatedAt), { addSuffix: true })}`
            : 'Updating…'}
        </span>
        <Button
          size="sm"
          variant="ghost"
          className="h-7 w-7 p-0"
          disabled={isFetching}
          onClick={() =>
            queryClient.invalidateQueries({
              queryKey: customerKeys.conversation(customerId),
            })
          }
          data-testid="refresh-messages-btn"
          aria-label="Refresh messages"
        >
          <RefreshCw className={cn('h-3 w-3', isFetching && 'animate-spin')} />
        </Button>
      </div>
    </div>
  );

  if (isLoading) {
    return (
      <div className="space-y-3" data-testid="messages-loading">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return <p className="text-red-600 text-sm" data-testid="messages-error">Failed to load messages.</p>;
  }

  if (filteredItems.length === 0) {
    return (
      <div data-testid="customer-messages" className="space-y-3">
        {header}
        <div className="text-center py-8" data-testid="messages-empty">
          <MessageSquare className="h-10 w-10 text-slate-300 mx-auto mb-2" />
          <p className="text-sm text-slate-500">
            {channelFilter === 'all'
              ? 'No messages yet for this customer'
              : `No ${channelFilter} messages match`}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="customer-messages" className="space-y-3">
      {header}
      <div className="space-y-2">
        {filteredItems.map((item) => (
          <ConversationRow key={`${item.source_table}-${item.id}`} item={item} />
        ))}
      </div>
      {hasNextPage && (
        <div className="flex justify-center pt-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
            data-testid="load-more-conversation-btn"
          >
            {isFetchingNextPage ? 'Loading…' : 'Load more'}
          </Button>
        </div>
      )}
    </div>
  );
}

interface ConversationRowProps {
  item: ConversationItem;
}

function ConversationRow({ item }: ConversationRowProps) {
  const isOutbound = item.direction === 'outbound';
  const statusColors = isOutbound ? outboundStatusColors : inboundStatusColors;
  const containerAlign = isOutbound ? 'items-end' : 'items-start';
  const bubbleStyles = isOutbound
    ? 'bg-teal-50 border-teal-100'
    : 'bg-white border-slate-100';
  const directionIcon = isOutbound ? (
    <ArrowUpRight className="h-3 w-3 text-teal-500" />
  ) : (
    <ArrowDownLeft className="h-3 w-3 text-indigo-500" />
  );
  const directionLabel = isOutbound ? 'Outbound' : 'Inbound';

  return (
    <div
      className={cn('flex flex-col gap-1', containerAlign)}
      data-testid={`message-${item.id}`}
      data-source={item.source_table}
      data-direction={item.direction}
    >
      <div
        className={cn(
          'max-w-[85%] rounded-lg border px-3 py-2 space-y-1.5',
          bubbleStyles
        )}
      >
        <div className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-wide text-slate-500">
          {directionIcon}
          <span>{directionLabel}</span>
          {channelIcons[item.channel]}
          {item.message_type && (
            <span className="text-slate-400">
              {item.message_type.replace(/_/g, ' ')}
            </span>
          )}
          {item.parsed_keyword && (
            <Badge
              className="bg-indigo-100 text-indigo-700 text-[10px]"
              data-testid={`message-keyword-${item.id}`}
            >
              {item.parsed_keyword}
            </Badge>
          )}
        </div>
        <p className="text-sm text-slate-700 whitespace-pre-wrap">{item.body}</p>
        <div className="flex items-center justify-between gap-2 text-[11px] text-slate-400">
          <span>
            {item.from_phone
              ? `From ${item.from_phone}`
              : item.to_phone
              ? `To ${item.to_phone}`
              : null}
          </span>
          <div className="flex items-center gap-2">
            {item.status && (
              <Badge
                className={cn(
                  'text-[10px] capitalize',
                  statusColors[item.status] ?? 'bg-slate-100 text-slate-600'
                )}
                data-testid={`message-status-${item.status}`}
              >
                {item.status.replace(/_/g, ' ')}
              </Badge>
            )}
            <time>{new Date(item.timestamp).toLocaleString()}</time>
          </div>
        </div>
      </div>
    </div>
  );
}

interface ChannelFilterPillsProps {
  value: ChannelFilter;
  onChange: (next: ChannelFilter) => void;
}

function ChannelFilterPills({ value, onChange }: ChannelFilterPillsProps) {
  const options: { key: ChannelFilter; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'sms', label: 'SMS' },
    { key: 'email', label: 'Email' },
  ];
  return (
    <div className="flex items-center gap-1" data-testid="conversation-channel-filter">
      {options.map((opt) => (
        <button
          key={opt.key}
          type="button"
          onClick={() => onChange(opt.key)}
          className={cn(
            'rounded-full px-2 py-0.5 text-[11px] font-medium transition-colors',
            value === opt.key
              ? 'bg-teal-100 text-teal-700'
              : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
          )}
          data-testid={`conversation-channel-${opt.key}`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
